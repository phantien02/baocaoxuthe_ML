import pytest
from unittest.mock import MagicMock, patch
from agent.bot.commands import handle_post
from agent.storage.database import init_db

BOT_ID = "bot_user_id_26chars_xxxxxx"
BOT_USERNAME = "bot_test_tienpc1"


def make_rest(channel_id="chan123"):
    rest = MagicMock()
    rest.get_channel_id.return_value = channel_id
    rest.get_my_user_id.return_value = BOT_ID
    rest.get_my_username.return_value = BOT_USERNAME
    return rest


def make_post(message="!report", channel_id="chan123", file_ids=None, post_type="", user_id="user1"):
    return {
        "channel_id": channel_id,
        "message": message,
        "user_id": user_id,
        "file_ids": file_ids or [],
        "type": post_type,
    }


def dm_event(sender="@tienpc1"):
    return {"channel_type": "D", "sender_name": sender}


def group_event(mentions=None, sender="@tienpc1"):
    ev = {"channel_type": "P", "sender_name": sender}
    if mentions is not None:
        import json
        ev["mentions"] = json.dumps(mentions)
    return ev


def test_report_command_posts_message():
    init_db()
    rest = make_rest()
    post = make_post("!report")
    with patch("agent.bot.commands.get_recent_items", return_value=[{"title": "T", "source": "3gpp", "url": "https://x.com", "content": "c"}]):
        with patch("agent.bot.commands.generate_report", return_value="📡 Report"):
            with patch("agent.bot.commands.save_report", return_value=1):
                handle_post(post, rest, group_event())
    rest.post_message.assert_called_once()
    assert "📡 Report" in rest.post_message.call_args[0][0]


def test_ignores_non_command_in_configured_channel():
    init_db()
    rest = make_rest()
    post = make_post("just a normal message")
    handle_post(post, rest, group_event())
    rest.post_message.assert_not_called()


def test_dm_natural_message_gets_llm_reply():
    init_db()
    rest = make_rest()
    post = make_post("tôi không biết sử dụng, hãy hướng dẫn tôi", channel_id="dm_chan")
    with patch("agent.bot.commands.chat_reply", return_value="Chào bạn! Tôi có thể...") as chat:
        handle_post(post, rest, dm_event())
    chat.assert_called_once()
    rest.post_message.assert_called_once()
    assert "Chào bạn" in rest.post_message.call_args[0][0]
    assert rest.post_message.call_args[0][1] == "dm_chan"


def test_group_mention_gets_llm_reply():
    init_db()
    rest = make_rest(channel_id="chan123")
    # nhóm bất kỳ (không phải channel cấu hình), bot được @mention
    post = make_post(f"@{BOT_USERNAME} bạn làm được gì?", channel_id="random_group")
    with patch("agent.bot.commands.chat_reply", return_value="Tôi làm được...") as chat:
        handle_post(post, rest, group_event(mentions=[BOT_ID]))
    chat.assert_called_once()
    # phần @bot phải được bỏ khỏi tin nhắn gửi cho LLM
    assert "@" + BOT_USERNAME not in chat.call_args[0][0]
    rest.post_message.assert_called_once()
    assert rest.post_message.call_args[0][1] == "random_group"


def test_group_mention_by_text_without_mentions_field():
    init_db()
    rest = make_rest(channel_id="chan123")
    post = make_post(f"@{BOT_USERNAME} xin chào", channel_id="random_group")
    with patch("agent.bot.commands.chat_reply", return_value="Chào!") as chat:
        handle_post(post, rest, group_event())  # không có field mentions
    chat.assert_called_once()
    rest.post_message.assert_called_once()


def test_group_message_without_mention_ignored():
    init_db()
    rest = make_rest(channel_id="chan123")
    post = make_post("nói chuyện bình thường", channel_id="random_group")
    handle_post(post, rest, group_event())
    rest.post_message.assert_not_called()


def test_mention_with_command_runs_command():
    init_db()
    rest = make_rest(channel_id="chan123")
    post = make_post(f"@{BOT_USERNAME} !sources", channel_id="random_group")
    handle_post(post, rest, group_event(mentions=[BOT_ID]))
    rest.post_message.assert_called_once()
    assert "3GPP" in rest.post_message.call_args[0][0]


def test_ignores_own_posts():
    init_db()
    rest = make_rest()
    post = make_post("tin nhắn của chính bot", channel_id="dm_chan", user_id=BOT_ID)
    handle_post(post, rest, dm_event())
    rest.post_message.assert_not_called()


def test_ignores_system_posts():
    init_db()
    rest = make_rest()
    post = make_post("user đã tham gia", channel_id="chan123", post_type="system_join_channel")
    handle_post(post, rest, group_event())
    rest.post_message.assert_not_called()


def test_status_command():
    init_db()
    rest = make_rest()
    post = make_post("!status")
    with patch("agent.bot.commands.get_last_crawl_time", return_value="2026-06-30 08:00"):
        with patch("agent.bot.commands.get_next_run", return_value="2026-07-07 08:00"):
            handle_post(post, rest, group_event())
    rest.post_message.assert_called_once()
    msg = rest.post_message.call_args[0][0]
    assert "2026-06-30" in msg


def test_sources_command():
    init_db()
    rest = make_rest()
    post = make_post("!sources")
    handle_post(post, rest, group_event())
    rest.post_message.assert_called_once()
    msg = rest.post_message.call_args[0][0]
    assert "3GPP" in msg


def test_help_command():
    init_db()
    rest = make_rest()
    post = make_post("!help")
    handle_post(post, rest, group_event())
    rest.post_message.assert_called_once()
    msg = rest.post_message.call_args[0][0]
    assert "!report" in msg


def test_file_attachment_triggers_summary():
    init_db()
    rest = make_rest()
    post = make_post("", file_ids=["file123"])
    rest.get_file_info.return_value = {"name": "spec.pdf", "extension": "pdf"}
    rest.download_file.return_value = b"%PDF-1.4 content"
    with patch("agent.bot.commands.extract_text_from_bytes", return_value="extracted text"):
        with patch("agent.bot.commands.summarize_document", return_value="Summary here"):
            with patch("agent.bot.commands.save_uploaded_doc", return_value=1):
                handle_post(post, rest, group_event())
    rest.post_message.assert_called_once()
    assert "Summary here" in rest.post_message.call_args[0][0]


def test_ignores_posts_from_other_channels():
    init_db()
    rest = make_rest(channel_id="chan123")
    post = make_post("!report", channel_id="other_chan")
    handle_post(post, rest, group_event())
    rest.post_message.assert_not_called()


def test_is_admin_true_when_listed(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1,sep_a")
    from agent.bot.commands import is_admin
    assert is_admin("tienpc1") is True


def test_is_admin_case_insensitive(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAMES", "TienPC1")
    from agent.bot.commands import is_admin
    assert is_admin("tienpc1") is True


def test_is_admin_false_when_not_listed(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAMES", "sep_a")
    from agent.bot.commands import is_admin
    assert is_admin("tienpc1") is False


def test_is_admin_false_when_unset(monkeypatch):
    monkeypatch.delenv("ADMIN_USERNAMES", raising=False)
    from agent.bot.commands import is_admin
    assert is_admin("tienpc1") is False


def test_schedule_view_shows_current(monkeypatch):
    init_db()
    from agent.storage.database import set_setting
    set_setting("schedule_days", "mon,fri")
    set_setting("schedule_time", "08:30")
    rest = make_rest()
    post = make_post("!schedule")
    with patch("agent.bot.commands.get_next_run", return_value="2026-07-17 08:30"):
        handle_post(post, rest, group_event(sender="@ai_ai"))
    msg = rest.post_message.call_args[0][0]
    assert "Thứ 2, Thứ 6" in msg
    assert "08:30" in msg


def test_schedule_set_success_for_admin(monkeypatch):
    init_db()
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1")
    rest = make_rest()
    post = make_post("!schedule mon,fri 08:30")
    with patch("agent.bot.commands.reschedule", return_value="2026-07-17 08:30") as resched:
        handle_post(post, rest, group_event(sender="@tienpc1"))
    resched.assert_called_once_with("mon,fri", "08:30")
    from agent.storage.database import get_setting
    assert get_setting("schedule_days") == "mon,fri"
    assert get_setting("schedule_time") == "08:30"
    assert "✅" in rest.post_message.call_args[0][0]


def test_schedule_set_denied_for_non_admin(monkeypatch):
    init_db()
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1")
    rest = make_rest()
    post = make_post("!schedule mon,fri 08:30")
    with patch("agent.bot.commands.reschedule") as resched:
        handle_post(post, rest, group_event(sender="@nguoi_la"))
    resched.assert_not_called()
    from agent.storage.database import get_setting
    assert get_setting("schedule_days") is None
    assert "⛔" in rest.post_message.call_args[0][0]


def test_schedule_no_admin_configured_message(monkeypatch):
    init_db()
    monkeypatch.delenv("ADMIN_USERNAMES", raising=False)
    rest = make_rest()
    post = make_post("!schedule mon,fri 08:30")
    with patch("agent.bot.commands.reschedule") as resched:
        handle_post(post, rest, group_event(sender="@ai_do_cung_duoc"))
    resched.assert_not_called()
    from agent.storage.database import get_setting
    assert get_setting("schedule_days") is None
    msg = rest.post_message.call_args[0][0]
    assert "ADMIN_USERNAMES" in msg or "Chưa cấu hình admin" in msg
    assert "⛔" not in msg


def test_schedule_bad_syntax_shows_hint(monkeypatch):
    init_db()
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1")
    rest = make_rest()
    post = make_post("!schedule funday 99:99")
    with patch("agent.bot.commands.reschedule") as resched:
        handle_post(post, rest, group_event(sender="@tienpc1"))
    resched.assert_not_called()
    assert "!schedule" in rest.post_message.call_args[0][0]


def test_help_lists_schedule():
    init_db()
    rest = make_rest()
    handle_post(make_post("!help"), rest, group_event())
    assert "!schedule" in rest.post_message.call_args[0][0]


def test_schedule_missing_time_shows_hint(monkeypatch):
    init_db()
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1")
    rest = make_rest()
    post = make_post("!schedule mon,fri")
    with patch("agent.bot.commands.reschedule") as resched:
        handle_post(post, rest, group_event(sender="@tienpc1"))
    resched.assert_not_called()
    from agent.storage.database import get_setting
    assert get_setting("schedule_days") is None
    msg = rest.post_message.call_args[0][0]
    assert "Lịch hiện tại" not in msg
    assert "08:30" in msg or "!schedule" in msg


def test_schedule_reschedule_failure_does_not_persist(monkeypatch):
    init_db()
    monkeypatch.setenv("ADMIN_USERNAMES", "tienpc1")
    rest = make_rest()
    post = make_post("!schedule tue 09:00")
    with patch("agent.bot.commands.reschedule", side_effect=RuntimeError("boom")):
        handle_post(post, rest, group_event(sender="@tienpc1"))
    msg = rest.post_message.call_args[0][0]
    assert "Lỗi" in msg
    from agent.storage.database import get_setting
    assert get_setting("schedule_days") is None
    assert get_setting("schedule_time") is None

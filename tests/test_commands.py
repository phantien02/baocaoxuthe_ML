import pytest
from unittest.mock import MagicMock, patch
from agent.bot.commands import handle_post
from agent.storage.database import init_db


def make_rest(channel_id="chan123"):
    rest = MagicMock()
    rest.get_channel_id.return_value = channel_id
    return rest


def make_post(message="!report", channel_id="chan123", file_ids=None, post_type=""):
    return {
        "channel_id": channel_id,
        "message": message,
        "user_id": "user1",
        "file_ids": file_ids or [],
        "type": post_type,
    }


def test_report_command_posts_message():
    init_db()
    rest = make_rest()
    post = make_post("!report")
    with patch("agent.bot.commands.get_recent_items", return_value=[{"title": "T", "source": "3gpp", "url": "https://x.com", "content": "c"}]):
        with patch("agent.bot.commands.generate_report", return_value="📡 Report"):
            with patch("agent.bot.commands.save_report", return_value=1):
                handle_post(post, rest)
    rest.post_message.assert_called_once()
    assert "📡 Report" in rest.post_message.call_args[0][0]


def test_ignores_non_command_in_channel():
    init_db()
    rest = make_rest()
    post = make_post("just a normal message")
    handle_post(post, rest)
    rest.post_message.assert_not_called()


def test_responds_to_anything_in_dm():
    init_db()
    rest = make_rest()
    post = make_post("hello bot", channel_id="dm_chan", post_type="D")
    with patch("agent.bot.commands.get_recent_items", return_value=[]):
        handle_post(post, rest)
    rest.post_message.assert_called_once()


def test_status_command():
    init_db()
    rest = make_rest()
    post = make_post("!status")
    with patch("agent.bot.commands.get_last_crawl_time", return_value="2026-06-30 08:00"):
        with patch("agent.bot.commands.get_next_run", return_value="2026-07-07 08:00"):
            handle_post(post, rest)
    rest.post_message.assert_called_once()
    msg = rest.post_message.call_args[0][0]
    assert "2026-06-30" in msg


def test_sources_command():
    init_db()
    rest = make_rest()
    post = make_post("!sources")
    handle_post(post, rest)
    rest.post_message.assert_called_once()
    msg = rest.post_message.call_args[0][0]
    assert "3GPP" in msg


def test_help_command():
    init_db()
    rest = make_rest()
    post = make_post("!help")
    handle_post(post, rest)
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
                handle_post(post, rest)
    rest.post_message.assert_called_once()
    assert "Summary here" in rest.post_message.call_args[0][0]


def test_ignores_posts_from_other_channels():
    init_db()
    rest = make_rest(channel_id="chan123")
    post = make_post("!report", channel_id="other_chan")
    handle_post(post, rest)
    rest.post_message.assert_not_called()

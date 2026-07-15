import io
import json
import os
from datetime import datetime

from agent.llm.claude_client import chat_reply, generate_report, summarize_document
from agent.storage.database import (
    get_recent_items, save_report, save_uploaded_doc, get_last_crawl_time,
)
from agent.scheduler import get_next_run

SOURCES = ["3GPP", "GSMA", "ETSI", "Ericsson", "Nokia", "Huawei"]


def is_admin(sender_name: str) -> bool:
    raw = os.getenv("ADMIN_USERNAMES", "")
    admins = {u.strip().lower() for u in raw.split(",") if u.strip()}
    return sender_name.strip().lstrip("@").lower() in admins if admins else False


def handle_post(post: dict, rest_client, event_data: dict | None = None) -> None:
    event_data = event_data or {}
    channel_id = post.get("channel_id", "")
    message = post.get("message", "").strip()
    user_id = post.get("user_id", "")
    file_ids = post.get("file_ids", [])
    sender_name = (event_data.get("sender_name") or "").lstrip("@")

    # Bỏ qua tin hệ thống (join/leave...) và tin do chính bot gửi (tránh vòng lặp)
    if post.get("type", "").startswith("system_"):
        return
    if user_id == rest_client.get_my_user_id():
        return

    # channel_type nằm trong event data của WebSocket, không nằm trong post
    is_dm = event_data.get("channel_type", "") == "D"
    mentioned, clean_message = _detect_mention(message, event_data, rest_client)
    is_configured_channel = channel_id == rest_client.get_channel_id()

    # Bot phản hồi khi: chat riêng, được @mention ở bất kỳ nhóm nào,
    # hoặc tin trong channel báo cáo đã cấu hình
    if not (is_dm or mentioned or is_configured_channel):
        return

    if file_ids:
        _handle_file_upload(file_ids[0], channel_id, user_id, rest_client)
        return

    text = clean_message if mentioned else message
    if not text:
        return

    if text.startswith("!"):
        _handle_command(text, channel_id, rest_client, allow_chat_fallback=is_dm or mentioned)
        return

    # Trong channel báo cáo, tin thường (không lệnh, không mention) thì bỏ qua
    if not (is_dm or mentioned):
        return

    # Giao tiếp tự nhiên qua LLM
    reply = chat_reply(text, sender_name, rest_client.get_my_username())
    rest_client.post_message(reply, channel_id)


def _detect_mention(message: str, event_data: dict, rest_client) -> tuple[bool, str]:
    """Nhận diện bot được @mention; trả về (mentioned, message đã bỏ phần @bot)."""
    try:
        raw = event_data.get("mentions", "[]")
        mentioned_ids = json.loads(raw) if isinstance(raw, str) else list(raw)
    except Exception:
        mentioned_ids = []
    username = rest_client.get_my_username()
    tag = f"@{username}"
    mentioned = rest_client.get_my_user_id() in mentioned_ids or tag in message
    clean = message.replace(tag, " ").strip() if mentioned else message
    return mentioned, clean


def _handle_command(text: str, channel_id: str, rest_client, allow_chat_fallback: bool = False) -> None:
    cmd = text.lower().split()[0]
    if cmd in ("!report", "!báo_cáo"):
        _handle_report(channel_id, rest_client)
    elif cmd == "!status":
        _handle_status(channel_id, rest_client)
    elif cmd == "!sources":
        rest_client.post_message(_sources_text(), channel_id)
    elif cmd == "!help":
        rest_client.post_message(_help_text(), channel_id)
    elif allow_chat_fallback:
        # Lệnh lạ trong ngữ cảnh trò chuyện — để LLM trả lời tự nhiên
        reply = chat_reply(text, "", rest_client.get_my_username())
        rest_client.post_message(reply, channel_id)
    else:
        rest_client.post_message(_help_text(), channel_id)


def _handle_report(channel_id: str, rest_client) -> None:
    items = get_recent_items(days=7)
    week_label = datetime.now().strftime("Tuần %W/%Y")
    if not items:
        rest_client.post_message("ℹ️ Không có bài mới trong 7 ngày qua.", channel_id)
        return
    report = generate_report(items, week_label)
    save_report("manual", report, channel_id)
    rest_client.post_message(report, channel_id)


def _handle_status(channel_id: str, rest_client) -> None:
    last_crawl = get_last_crawl_time() or "Chưa có"
    next_run = get_next_run()
    msg = f"📊 **Trạng thái Agent**\n- Lần crawl cuối: {last_crawl}\n- Báo cáo tiếp theo: {next_run}"
    rest_client.post_message(msg, channel_id)


def _sources_text() -> str:
    lines = "\n".join(f"  • {s}" for s in SOURCES)
    return f"🌐 **Nguồn đang theo dõi:**\n{lines}"


def _help_text() -> str:
    return (
        "**Lệnh bot:**\n"
        "  `!report` — Tạo báo cáo từ 7 ngày qua\n"
        "  `!status` — Thời gian crawl cuối + lịch tiếp theo\n"
        "  `!sources` — Danh sách nguồn\n"
        "  `!help` — Trợ giúp\n"
        "  _(attach file PDF/DOCX)_ — Tóm tắt tài liệu\n\n"
        "💬 Ngoài lệnh, bạn có thể chat tự nhiên với tôi: nhắn riêng (DM) "
        "hoặc nhắc tên tôi trong nhóm (`@bot...`) rồi đặt câu hỏi."
    )


def _handle_file_upload(file_id: str, channel_id: str, user_id: str, rest_client) -> None:
    try:
        info = rest_client.get_file_info(file_id)
        filename = info.get("name", "unknown")
        extension = info.get("extension", "").lower()
        raw_bytes = rest_client.download_file(file_id)
        text = extract_text_from_bytes(raw_bytes, extension)
        if not text:
            rest_client.post_message(f"⚠️ Không đọc được nội dung file `{filename}`.", channel_id)
            return
        summary = summarize_document(text, filename)
        save_uploaded_doc(filename, extension, text[:10000], summary, user_id)
        rest_client.post_message(f"📄 **Tóm tắt `{filename}`:**\n\n{summary}", channel_id)
    except Exception as e:
        rest_client.post_message(f"⚠️ Lỗi xử lý file: {e}", channel_id)


def extract_text_from_bytes(data: bytes, extension: str) -> str:
    if extension == "pdf":
        return _extract_pdf(data)
    if extension in ("docx", "doc"):
        return _extract_docx(data)
    try:
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        print(f"[pdf] extract error: {e}")
        return ""


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        print(f"[docx] extract error: {e}")
        return ""

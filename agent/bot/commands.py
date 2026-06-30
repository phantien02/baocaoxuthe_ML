import io
from datetime import datetime

from agent.llm.claude_client import generate_report, summarize_document
from agent.storage.database import (
    get_recent_items, save_report, save_uploaded_doc, get_last_crawl_time,
)
from agent.scheduler import get_next_run

SOURCES = ["3GPP", "GSMA", "ETSI", "Ericsson", "Nokia", "Huawei"]


def handle_post(post: dict, rest_client) -> None:
    channel_id = post.get("channel_id", "")
    message = post.get("message", "").strip()
    user_id = post.get("user_id", "")
    file_ids = post.get("file_ids", [])
    post_type = post.get("type", "")

    configured_channel = rest_client.get_channel_id()
    is_dm = post_type == "D"
    is_configured_channel = channel_id == configured_channel

    if not is_dm and not is_configured_channel:
        return

    if file_ids:
        _handle_file_upload(file_ids[0], channel_id, user_id, rest_client)
        return

    if is_configured_channel and not message.startswith("!"):
        return

    cmd = message.lower().split()[0] if message else "!report"

    if cmd in ("!report", "!báo_cáo"):
        _handle_report(channel_id, rest_client)
    elif cmd == "!status":
        _handle_status(channel_id, rest_client)
    elif cmd == "!sources":
        rest_client.post_message(_sources_text(), channel_id)
    elif cmd == "!help":
        rest_client.post_message(_help_text(), channel_id)
    elif is_dm:
        _handle_report(channel_id, rest_client)


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
        "  _(attach file PDF/DOCX)_ — Tóm tắt tài liệu"
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

import os
import time
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from agent.llm.prompts import CHAT_PROMPT, REPORT_PROMPT, SUMMARIZE_PROMPT

_client: genai.Client | None = None

# Mã lỗi tạm thời của Gemini nên thử lại (quá tải / hết hạn mức tạm thời / lỗi server)
_RETRY_CODES = {429, 500, 503}
_MAX_ATTEMPTS = 4  # 1 lần đầu + 3 lần thử lại, backoff 2s/4s/8s


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def _generate(prompt: str, max_output_tokens: int) -> str:
    """Gọi Gemini có retry cho lỗi tạm thời (503/429/500) với backoff lũy thừa.
    Lỗi tạm thời kéo dài quá số lần thử -> ném lại để lớp trên xử lý/log."""
    client = get_client()
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=_model(),
                contents=prompt,
                config=types.GenerateContentConfig(max_output_tokens=max_output_tokens),
            )
            return response.text
        except genai_errors.APIError as e:
            code = getattr(e, "code", None)
            if code not in _RETRY_CODES or attempt == _MAX_ATTEMPTS - 1:
                raise
            wait = 2 ** (attempt + 1)  # 2s, 4s, 8s
            print(f"[llm] Gemini lỗi tạm thời {code}, thử lại sau {wait}s "
                  f"(lần {attempt + 1}/{_MAX_ATTEMPTS - 1})")
            time.sleep(wait)
    raise RuntimeError("unreachable")  # vòng lặp luôn return hoặc raise


def generate_report(items: list[dict], week_label: str) -> str:
    prompt = REPORT_PROMPT.format(
        week_label=week_label,
        items="\n\n".join(
            f"Source: {i['source']}\nTitle: {i['title']}\nURL: {i['url']}\nContent: {i['content'][:500]}"
            for i in items
        ),
    )
    return _generate(prompt, max_output_tokens=4096)


def chat_reply(message: str, sender_name: str = "", bot_name: str = "bot") -> str:
    prompt = CHAT_PROMPT.format(
        bot_name=bot_name,
        sender_name=sender_name or "người dùng",
        message=message[:4000],
    )
    return _generate(prompt, max_output_tokens=1024)


def summarize_document(content: str, filename: str) -> str:
    prompt = SUMMARIZE_PROMPT.format(filename=filename, content=content[:8000])
    return _generate(prompt, max_output_tokens=2048)

import os
import anthropic

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["CLAUDE_API_KEY"])
    return _client


def generate_report(items: list[dict], week_label: str) -> str:
    from .prompts import REPORT_PROMPT
    items_text = "\n\n".join(
        f"[{item['source'].upper()}] {item['title']}\nURL: {item['url']}\n{item['content']}"
        for item in items
    )
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    message = get_client().messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": REPORT_PROMPT.format(
            week_label=week_label, items=items_text
        )}],
    )
    return message.content[0].text


def summarize_document(content: str, filename: str) -> str:
    from .prompts import SUMMARIZE_PROMPT
    model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    message = get_client().messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": SUMMARIZE_PROMPT.format(
            filename=filename, content=content[:8000]
        )}],
    )
    return message.content[0].text

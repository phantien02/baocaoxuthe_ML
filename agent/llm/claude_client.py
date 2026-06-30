import os
from google import genai
from google.genai import types

from agent.llm.prompts import REPORT_PROMPT, SUMMARIZE_PROMPT

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


def _model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def generate_report(items: list[dict], week_label: str) -> str:
    prompt = REPORT_PROMPT.format(
        week_label=week_label,
        items="\n\n".join(
            f"Source: {i['source']}\nTitle: {i['title']}\nURL: {i['url']}\nContent: {i['content'][:500]}"
            for i in items
        ),
    )
    client = get_client()
    response = client.models.generate_content(
        model=_model(),
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=4096),
    )
    return response.text


def summarize_document(content: str, filename: str) -> str:
    prompt = SUMMARIZE_PROMPT.format(filename=filename, content=content[:8000])
    client = get_client()
    response = client.models.generate_content(
        model=_model(),
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=2048),
    )
    return response.text

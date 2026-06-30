import pytest
from unittest.mock import MagicMock, patch
from agent.llm.claude_client import generate_report, summarize_document


SAMPLE_ITEMS = [
    {"source": "3gpp", "title": "NWDAF Release 19", "url": "https://3gpp.org/1",
     "content": "Network automation features.", "topic": "5GC"},
    {"source": "ericsson", "title": "5GC Cloud Native", "url": "https://ericsson.com/1",
     "content": "Cloud native deployment strategies.", "topic": "5GC"},
]


def _mock_response(text: str):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=text)]
    return mock_msg


def test_generate_report_returns_string():
    with patch("agent.llm.claude_client.get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response("📡 BÁO CÁO...")
        result = generate_report(SAMPLE_ITEMS, "Tuần 27/2026")
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_report_calls_correct_model():
    with patch("agent.llm.claude_client.get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response("report")
        generate_report(SAMPLE_ITEMS, "Tuần 27/2026")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 4096


def test_summarize_document_returns_string():
    with patch("agent.llm.claude_client.get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response("Tóm tắt: ...")
        result = summarize_document("Document content here", "spec.pdf")
    assert isinstance(result, str)
    assert len(result) > 0


def test_summarize_truncates_long_content():
    long_content = "x" * 20000
    with patch("agent.llm.claude_client.get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.messages.create.return_value = _mock_response("summary")
        summarize_document(long_content, "big.pdf")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    prompt_sent = call_kwargs["messages"][0]["content"]
    assert len(prompt_sent) < len(long_content)

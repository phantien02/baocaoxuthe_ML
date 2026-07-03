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
    mock_resp = MagicMock()
    mock_resp.text = text
    return mock_resp


def test_generate_report_returns_string():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response("📡 BÁO CÁO...")
    with patch("agent.llm.claude_client.get_client", return_value=mock_client):
        result = generate_report(SAMPLE_ITEMS, "Tuần 27/2026")
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_report_calls_correct_model():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response("report")
    with patch("agent.llm.claude_client.get_client", return_value=mock_client):
        generate_report(SAMPLE_ITEMS, "Tuần 27/2026")
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    assert call_kwargs["model"] == "gemini-test"  # lấy từ env GEMINI_MODEL (conftest)
    assert call_kwargs["config"].max_output_tokens == 4096


def test_summarize_document_returns_string():
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response("Tóm tắt: ...")
    with patch("agent.llm.claude_client.get_client", return_value=mock_client):
        result = summarize_document("Document content here", "spec.pdf")
    assert isinstance(result, str)
    assert len(result) > 0


def test_summarize_truncates_long_content():
    long_content = "x" * 20000
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _mock_response("summary")
    with patch("agent.llm.claude_client.get_client", return_value=mock_client):
        summarize_document(long_content, "big.pdf")
    call_kwargs = mock_client.models.generate_content.call_args.kwargs
    prompt_sent = call_kwargs["contents"]
    assert len(prompt_sent) < len(long_content)

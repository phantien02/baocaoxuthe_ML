import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from agent.main import crawl_and_report
from agent.storage.database import init_db


def test_crawl_and_report_sends_report_when_items_exist():
    init_db()
    rest = MagicMock()
    rest.get_channel_id.return_value = "chan1"
    items = [{"title": "5GC Update", "source": "3gpp", "url": "https://x.com", "content": "c"}]
    with patch("agent.main.run_all_crawlers", return_value=3):
        with patch("agent.main.get_recent_items", return_value=items):
            with patch("agent.main.generate_report", return_value="## Report") as mock_gen:
                with patch("agent.main.save_report", return_value=1):
                    crawl_and_report(rest)
    rest.post_message.assert_called_once()
    assert "## Report" in rest.post_message.call_args[0][0]
    mock_gen.assert_called_once()


def test_crawl_and_report_skips_when_no_items():
    init_db()
    rest = MagicMock()
    with patch("agent.main.run_all_crawlers", return_value=0):
        with patch("agent.main.get_recent_items", return_value=[]):
            with patch("agent.main.generate_report") as mock_gen:
                crawl_and_report(rest)
    mock_gen.assert_not_called()
    rest.post_message.assert_not_called()


def test_crawl_and_report_uses_current_week_label():
    init_db()
    rest = MagicMock()
    rest.get_channel_id.return_value = "chan1"
    items = [{"title": "T", "source": "s", "url": "u", "content": "c"}]
    captured = {}
    def capture_gen(items, week_label):
        captured["week_label"] = week_label
        return "report"
    with patch("agent.main.run_all_crawlers", return_value=1):
        with patch("agent.main.get_recent_items", return_value=items):
            with patch("agent.main.generate_report", side_effect=capture_gen):
                with patch("agent.main.save_report", return_value=1):
                    crawl_and_report(rest)
    assert "Tuần" in captured["week_label"]


def test_crawl_and_report_saves_report_as_scheduled():
    init_db()
    rest = MagicMock()
    rest.get_channel_id.return_value = "chan99"
    items = [{"title": "T", "source": "s", "url": "u", "content": "c"}]
    with patch("agent.main.run_all_crawlers", return_value=1):
        with patch("agent.main.get_recent_items", return_value=items):
            with patch("agent.main.generate_report", return_value="R"):
                with patch("agent.main.save_report") as mock_save:
                    crawl_and_report(rest)
    mock_save.assert_called_once_with("scheduled", "R", "chan99")

import pytest
import os


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_agent.db")
    monkeypatch.setenv("DB_PATH", db_file)
    yield db_file


@pytest.fixture(autouse=True)
def env_vars(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
    monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("NETCHAT_URL", "https://netchat.test.vn")
    monkeypatch.setenv("NETCHAT_TOKEN", "mm_testtoken")
    monkeypatch.setenv("NETCHAT_TEAM_NAME", "test-team")
    monkeypatch.setenv("NETCHAT_CHANNEL_NAME", "test-channel")
    monkeypatch.setenv("REPORT_SCHEDULE_DAY", "mon")
    monkeypatch.setenv("REPORT_SCHEDULE_TIME", "08:00")
    monkeypatch.setenv("REPORT_TIMEZONE", "Asia/Ho_Chi_Minh")

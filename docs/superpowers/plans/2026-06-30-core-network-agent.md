# Core Network Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python chatbot agent that auto-crawls Core Network tech news, generates bilingual weekly reports via Claude API, and communicates through Viettel Netchat.

**Architecture:** Modular monolith — one Docker container, five Python packages (`bot`, `crawler`, `llm`, `scheduler`, `storage`) communicating via direct function calls. WebSocket listens for Netchat commands; REST API sends reports. APScheduler drives weekly cron.

**Tech Stack:** Python 3.11, anthropic SDK, requests, BeautifulSoup4, websocket-client, APScheduler, SQLite, python-dotenv, pytest, Docker, GCP VM.

## Global Constraints

- Python ≥ 3.11 (uses `match`, `X | Y` type unions)
- All Netchat calls use `Bearer <NETCHAT_TOKEN>` header
- LLM model default: `claude-sonnet-4-6` (override via `CLAUDE_MODEL` env var)
- SQLite file at path from `DB_PATH` env var, default `/data/agent.db`
- Report language: Vietnamese titles/summaries + English technical content
- Crawlers must tolerate HTTP errors silently (return `[]` on any exception)
- Bot responds to `!commands` only in configured channel; responds to anything in DM
- Dedup crawled items by URL (SQLite UNIQUE constraint, catch IntegrityError)

---

## File Map

```
core-network-agent/
├── agent/
│   ├── __init__.py
│   ├── main.py                        # entrypoint, wires all modules
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── rest_client.py             # NetchatRestClient: post_message, download_file
│   │   ├── websocket_client.py        # NetchatWebSocketClient: start/stop
│   │   └── commands.py                # handle_post: routes ! commands + file uploads
│   ├── crawler/
│   │   ├── __init__.py                # run_all_crawlers() -> int
│   │   ├── base.py                    # CrawledItem dataclass + BaseCrawler
│   │   ├── source_3gpp.py             # Crawler3GPP
│   │   ├── source_gsma.py             # CrawlerGSMA
│   │   ├── source_etsi.py             # CrawlerETSI
│   │   ├── source_ericsson.py         # CrawlerEricsson
│   │   ├── source_nokia.py            # CrawlerNokia
│   │   └── source_huawei.py           # CrawlerHuawei
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── claude_client.py           # generate_report, summarize_document
│   │   └── prompts.py                 # REPORT_PROMPT, SUMMARIZE_PROMPT
│   ├── scheduler/
│   │   └── __init__.py                # init_scheduler, get_next_run, stop
│   └── storage/
│       ├── __init__.py
│       └── database.py                # init_db, save_crawled_item, get_recent_items, ...
├── tests/
│   ├── conftest.py                    # isolated_db + env_vars fixtures
│   ├── test_storage.py
│   ├── test_crawler_base.py
│   ├── test_crawlers.py
│   ├── test_llm.py
│   ├── test_rest_client.py
│   └── test_commands.py
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── requirements.txt
└── README.md
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `agent/__init__.py` (empty)
- Create: `agent/bot/__init__.py` (empty)
- Create: `agent/crawler/__init__.py` (stub)
- Create: `agent/llm/__init__.py` (empty)
- Create: `agent/scheduler/__init__.py` (stub)
- Create: `agent/storage/__init__.py` (empty)
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: project can be installed with `pip install -r requirements.txt`; `pytest tests/` runs with zero test failures

- [ ] **Step 1: Create requirements.txt**

```
anthropic>=0.40.0
requests>=2.31.0
beautifulsoup4>=4.12.0
websocket-client>=1.7.0
APScheduler>=3.10.0
python-dotenv>=1.0.0
pypdf>=4.0.0
python-docx>=1.1.0
pytest>=8.0.0
pytest-mock>=3.12.0
responses>=0.25.0
```

- [ ] **Step 2: Create .env.example**

```env
# LLM
CLAUDE_API_KEY=sk-ant-your-key-here
CLAUDE_MODEL=claude-sonnet-4-6

# Netchat (Mattermost-compatible)
NETCHAT_URL=https://netchat.viettel.vn
NETCHAT_TOKEN=mm_your_token_here
NETCHAT_TEAM_NAME=your-team-name
NETCHAT_CHANNEL_NAME=core-network-tech

# Scheduler (Asia/Ho_Chi_Minh timezone)
REPORT_SCHEDULE_DAY=mon
REPORT_SCHEDULE_TIME=08:00
REPORT_TIMEZONE=Asia/Ho_Chi_Minh

# Storage
DB_PATH=/data/agent.db
```

- [ ] **Step 3: Create Dockerfile**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY agent/ ./agent/
VOLUME ["/data"]
CMD ["python", "-m", "agent.main"]
```

- [ ] **Step 4: Create docker-compose.yml**

```yaml
services:
  agent:
    build: .
    env_file: .env
    volumes:
      - agent_data:/data
    restart: unless-stopped

volumes:
  agent_data:
```

- [ ] **Step 5: Create tests/conftest.py**

```python
import pytest
import os


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_agent.db")
    monkeypatch.setenv("DB_PATH", db_file)
    # init_db called per-test by tests that need it
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
```

- [ ] **Step 6: Create empty __init__.py files**

Create empty files at: `agent/__init__.py`, `agent/bot/__init__.py`, `agent/llm/__init__.py`, `agent/storage/__init__.py`

- [ ] **Step 7: Install dependencies**

```bash
cd C:\Users\tienpc1\core-network-agent
pip install -r requirements.txt
```

Expected: no errors. Verify with `python -c "import anthropic, requests, bs4, websocket, apscheduler"` → no ImportError.

- [ ] **Step 8: Run pytest to confirm zero tests (not failure)**

```bash
pytest tests/ -v
```

Expected: `no tests ran` or `0 passed` — NOT error.

- [ ] **Step 9: Init git repo and commit scaffold**

```bash
git init
echo "__pycache__/" > .gitignore
echo "*.pyc" >> .gitignore
echo ".env" >> .gitignore
echo "*.db" >> .gitignore
git add .
git commit -m "feat: project scaffold"
```

---

## Task 2: Storage Module

**Files:**
- Create: `agent/storage/database.py`
- Create: `tests/test_storage.py`

**Interfaces:**
- Produces:
  - `init_db() -> None`
  - `save_crawled_item(source: str, title: str, url: str, content: str, topic: str) -> bool` (True=new, False=duplicate)
  - `get_recent_items(days: int = 7) -> list[dict]`
  - `save_report(trigger_type: str, content: str, sent_to_channel: str | None = None) -> int`
  - `get_last_crawl_time() -> str | None`
  - `save_uploaded_doc(filename: str, file_type: str, content: str, summary: str, uploaded_by: str) -> int`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_storage.py
import pytest
from agent.storage.database import (
    init_db, save_crawled_item, get_recent_items,
    save_report, get_last_crawl_time, save_uploaded_doc,
)


def test_init_db_creates_tables():
    init_db()
    import sqlite3, os
    conn = sqlite3.connect(os.environ["DB_PATH"])
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    table_names = {t[0] for t in tables}
    assert {"crawled_items", "reports", "uploaded_docs"}.issubset(table_names)
    conn.close()


def test_save_crawled_item_new():
    init_db()
    result = save_crawled_item("3gpp", "Test Title", "https://example.com/1", "content", "5GC")
    assert result is True


def test_save_crawled_item_duplicate():
    init_db()
    save_crawled_item("3gpp", "Title", "https://example.com/dup", "content", "5GC")
    result = save_crawled_item("3gpp", "Title", "https://example.com/dup", "content", "5GC")
    assert result is False


def test_get_recent_items_returns_saved():
    init_db()
    save_crawled_item("gsma", "GSMA Post", "https://gsma.com/1", "body", "Autonomous")
    items = get_recent_items(days=7)
    assert len(items) >= 1
    assert items[0]["title"] == "GSMA Post"


def test_save_report_returns_id():
    init_db()
    rid = save_report("manual", "Report content", "channel123")
    assert isinstance(rid, int)
    assert rid > 0


def test_get_last_crawl_time_none_on_empty():
    init_db()
    result = get_last_crawl_time()
    assert result is None


def test_get_last_crawl_time_after_insert():
    init_db()
    save_crawled_item("3gpp", "T", "https://x.com/t", "c", "5GC")
    result = get_last_crawl_time()
    assert result is not None


def test_save_uploaded_doc_returns_id():
    init_db()
    doc_id = save_uploaded_doc("spec.pdf", "pdf", "full content", "summary text", "user123")
    assert isinstance(doc_id, int)
    assert doc_id > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_storage.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.storage.database'`

- [ ] **Step 3: Implement agent/storage/database.py**

```python
import sqlite3
import os
from pathlib import Path


def _db_path() -> str:
    return os.getenv("DB_PATH", "/data/agent.db")


def get_connection() -> sqlite3.Connection:
    path = _db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS crawled_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content TEXT,
                topic TEXT,
                crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_in_report BOOLEAN DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trigger_type TEXT NOT NULL,
                content TEXT NOT NULL,
                sent_to_channel TEXT
            );
            CREATE TABLE IF NOT EXISTS uploaded_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_type TEXT,
                content TEXT,
                summary TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                uploaded_by TEXT
            );
        """)


def save_crawled_item(source: str, title: str, url: str, content: str, topic: str) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO crawled_items (source, title, url, content, topic) VALUES (?, ?, ?, ?, ?)",
                (source, title, url, content, topic),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_recent_items(days: int = 7) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM crawled_items WHERE crawled_at >= datetime('now', ?)"
            " ORDER BY crawled_at DESC",
            (f"-{days} days",),
        ).fetchall()
        return [dict(row) for row in rows]


def save_report(trigger_type: str, content: str, sent_to_channel: str | None = None) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO reports (trigger_type, content, sent_to_channel) VALUES (?, ?, ?)",
            (trigger_type, content, sent_to_channel),
        )
        return cursor.lastrowid


def get_last_crawl_time() -> str | None:
    with get_connection() as conn:
        row = conn.execute("SELECT MAX(crawled_at) AS last FROM crawled_items").fetchone()
        return row["last"] if row else None


def save_uploaded_doc(filename: str, file_type: str, content: str, summary: str, uploaded_by: str) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO uploaded_docs (filename, file_type, content, summary, uploaded_by)"
            " VALUES (?, ?, ?, ?, ?)",
            (filename, file_type, content, summary, uploaded_by),
        )
        return cursor.lastrowid
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_storage.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/storage/database.py tests/test_storage.py
git commit -m "feat: storage module with SQLite"
```

---

## Task 3: Crawler Base + 3GPP Crawler

**Files:**
- Create: `agent/crawler/base.py`
- Create: `agent/crawler/source_3gpp.py`
- Modify: `agent/crawler/__init__.py`
- Create: `tests/test_crawler_base.py`

**Interfaces:**
- Consumes: nothing (no deps on other tasks)
- Produces:
  - `CrawledItem(source, title, url, content, topic, date)` dataclass
  - `BaseCrawler` with `crawl() -> list[CrawledItem]` abstract method and `_get_html(url) -> str`
  - `Crawler3GPP().crawl() -> list[CrawledItem]`
  - `run_all_crawlers() -> int` (in `__init__.py`) — counts new items saved to DB

- [ ] **Step 1: Write failing tests**

```python
# tests/test_crawler_base.py
import pytest
import responses as resp_lib
from agent.crawler.base import CrawledItem, BaseCrawler
from agent.crawler.source_3gpp import Crawler3GPP


def test_crawled_item_fields():
    item = CrawledItem(
        source="3gpp", title="Test", url="https://3gpp.org/1",
        content="content", topic="5GC",
    )
    assert item.source == "3gpp"
    assert item.topic == "5GC"
    assert item.date is None  # optional field


def test_base_crawler_requires_crawl():
    class NoCrawl(BaseCrawler):
        source_name = "test"

    with pytest.raises(NotImplementedError):
        NoCrawl().crawl()


@resp_lib.activate
def test_3gpp_crawler_returns_list_on_valid_html():
    resp_lib.add(
        resp_lib.GET,
        "https://www.3gpp.org/news-events/3gpp-news",
        body="""
        <html><body>
          <article class="news-item">
            <h3><a href="/news/5gc-update">5GC NWDAF Release 19 Update</a></h3>
            <p class="summary">New features for network automation in Release 19.</p>
          </article>
        </body></html>
        """,
        status=200,
    )
    crawler = Crawler3GPP()
    items = crawler.crawl()
    assert isinstance(items, list)
    assert len(items) == 1
    assert items[0].source == "3gpp"
    assert items[0].topic in ("5GC", "IMS", "EPC", "Autonomous", "General")


@resp_lib.activate
def test_3gpp_crawler_returns_empty_on_http_error():
    resp_lib.add(
        resp_lib.GET,
        "https://www.3gpp.org/news-events/3gpp-news",
        status=500,
    )
    items = Crawler3GPP().crawl()
    assert items == []


def test_detect_topic_5gc():
    c = Crawler3GPP()
    assert c._detect_topic("AMF SMF UPF 5G core architecture") == "5GC"


def test_detect_topic_ims():
    c = Crawler3GPP()
    assert c._detect_topic("VoLTE VoNR IMS enhancement") == "IMS"


def test_detect_topic_autonomous():
    c = Crawler3GPP()
    assert c._detect_topic("autonomous network ZSM AI/ML operations") == "Autonomous"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_crawler_base.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.crawler.base'`

- [ ] **Step 3: Create agent/crawler/base.py**

```python
from dataclasses import dataclass, field
from typing import Optional
import requests


@dataclass
class CrawledItem:
    source: str
    title: str
    url: str
    content: str
    topic: str
    date: Optional[str] = None


class BaseCrawler:
    source_name: str = ""
    topics: list[str] = field(default_factory=list)

    def crawl(self) -> list[CrawledItem]:
        raise NotImplementedError

    def _get_html(self, url: str, timeout: int = 15) -> str:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; CoreNetworkAgent/1.0; +viettel.com.vn)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
```

- [ ] **Step 4: Create agent/crawler/source_3gpp.py**

```python
from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem


class Crawler3GPP(BaseCrawler):
    source_name = "3gpp"
    BASE_URL = "https://www.3gpp.org/news-events/3gpp-news"

    def crawl(self) -> list[CrawledItem]:
        try:
            html = self._get_html(self.BASE_URL)
            soup = BeautifulSoup(html, "html.parser")
            items = []
            for article in soup.select("article")[:15]:
                title_tag = article.select_one("h3 a, h2 a, h3, h2")
                link_tag = article.select_one("a[href]")
                summary_tag = article.select_one("p.summary, p.description, p")
                if not title_tag or not link_tag:
                    continue
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else f"https://www.3gpp.org{href}"
                title = title_tag.get_text(strip=True)
                content = summary_tag.get_text(strip=True) if summary_tag else title
                items.append(CrawledItem(
                    source=self.source_name,
                    title=title,
                    url=url,
                    content=content,
                    topic=self._detect_topic(title + " " + content),
                ))
            return items
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []

    def _detect_topic(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in ("5gc", "amf", "smf", "upf", "nrf", "nwdaf", "5g core", "pcf")):
            return "5GC"
        if any(k in t for k in ("ims", "volte", "vonr", "rcs", "rich communication")):
            return "IMS"
        if any(k in t for k in ("epc", "pgw", "sgw", "mme", "pcrf", "4g core")):
            return "EPC"
        if any(k in t for k in ("autonomous", "self-managing", "zsm", "zero-touch", "ai/ml", "closed loop")):
            return "Autonomous"
        return "General"
```

- [ ] **Step 5: Update agent/crawler/__init__.py**

```python
from .source_3gpp import Crawler3GPP
from .source_gsma import CrawlerGSMA
from .source_etsi import CrawlerETSI
from .source_ericsson import CrawlerEricsson
from .source_nokia import CrawlerNokia
from .source_huawei import CrawlerHuawei
from agent.storage.database import save_crawled_item

CRAWLERS = [
    Crawler3GPP(),
    CrawlerGSMA(),
    CrawlerETSI(),
    CrawlerEricsson(),
    CrawlerNokia(),
    CrawlerHuawei(),
]


def run_all_crawlers() -> int:
    total_new = 0
    for crawler in CRAWLERS:
        items = crawler.crawl()
        for item in items:
            if save_crawled_item(item.source, item.title, item.url, item.content, item.topic):
                total_new += 1
    return total_new
```

*Note: remaining crawler classes (CrawlerGSMA etc.) are stubs until Task 4.*

- [ ] **Step 6: Create stub files so imports don't fail (Task 4 will fill them)**

Create `agent/crawler/source_gsma.py`, `source_etsi.py`, `source_ericsson.py`, `source_nokia.py`, `source_huawei.py` each with:

```python
from .base import BaseCrawler, CrawledItem


class CrawlerGSMA(BaseCrawler):   # replace classname per file
    source_name = "gsma"          # replace per file

    def crawl(self) -> list[CrawledItem]:
        return []
```

Classnames and source_names for each file:
- `source_gsma.py`: `CrawlerGSMA`, `"gsma"`
- `source_etsi.py`: `CrawlerETSI`, `"etsi"`
- `source_ericsson.py`: `CrawlerEricsson`, `"ericsson"`
- `source_nokia.py`: `CrawlerNokia`, `"nokia"`
- `source_huawei.py`: `CrawlerHuawei`, `"huawei"`

- [ ] **Step 7: Run tests**

```bash
pytest tests/test_crawler_base.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add agent/crawler/ tests/test_crawler_base.py
git commit -m "feat: crawler base + 3GPP crawler"
```

---

## Task 4: Remaining Crawlers (GSMA, ETSI, Ericsson, Nokia, Huawei)

**Files:**
- Modify: `agent/crawler/source_gsma.py`
- Modify: `agent/crawler/source_etsi.py`
- Modify: `agent/crawler/source_ericsson.py`
- Modify: `agent/crawler/source_nokia.py`
- Modify: `agent/crawler/source_huawei.py`
- Create: `tests/test_crawlers.py`

**Interfaces:**
- Consumes: `BaseCrawler`, `CrawledItem` from Task 3; `_detect_topic` pattern from `Crawler3GPP`
- Produces: all 5 crawler classes with working `crawl() -> list[CrawledItem]`, each tolerating HTTP errors

- [ ] **Step 1: Write tests**

```python
# tests/test_crawlers.py
import pytest
import responses as resp_lib
from agent.crawler.source_gsma import CrawlerGSMA
from agent.crawler.source_etsi import CrawlerETSI
from agent.crawler.source_ericsson import CrawlerEricsson
from agent.crawler.source_nokia import CrawlerNokia
from agent.crawler.source_huawei import CrawlerHuawei


CRAWLERS_UNDER_TEST = [
    (CrawlerGSMA, "https://www.gsma.com/solutions-and-impact/technologies/networks/"),
    (CrawlerETSI, "https://www.etsi.org/news-events/news"),
    (CrawlerEricsson, "https://www.ericsson.com/en/blog/tags/core-network"),
    (CrawlerNokia, "https://www.nokia.com/about-us/news/"),
    (CrawlerHuawei, "https://carrier.huawei.com/en/insights"),
]


@pytest.mark.parametrize("cls,url", CRAWLERS_UNDER_TEST)
@resp_lib.activate
def test_crawler_returns_list_on_200(cls, url):
    resp_lib.add(resp_lib.GET, url, body="<html><body></body></html>", status=200)
    items = cls().crawl()
    assert isinstance(items, list)


@pytest.mark.parametrize("cls,url", CRAWLERS_UNDER_TEST)
@resp_lib.activate
def test_crawler_returns_empty_on_500(cls, url):
    resp_lib.add(resp_lib.GET, url, status=500)
    items = cls().crawl()
    assert items == []


@resp_lib.activate
def test_ericsson_parses_article():
    resp_lib.add(
        resp_lib.GET,
        "https://www.ericsson.com/en/blog/tags/core-network",
        body="""
        <html><body>
          <div class="card">
            <h3><a href="/en/blog/2026/5gc-evolution">5GC Evolution with NWDAF</a></h3>
            <p>Network automation via AI/ML in 5G Core.</p>
          </div>
        </body></html>
        """,
        status=200,
    )
    items = CrawlerEricsson().crawl()
    assert len(items) == 1
    assert items[0].source == "ericsson"
    assert items[0].topic in ("5GC", "Autonomous", "IMS", "EPC", "General")
```

- [ ] **Step 2: Run tests — expect failures for unimplemented crawlers**

```bash
pytest tests/test_crawlers.py -v
```

Expected: tests for 500-error pass (stubs return `[]`), but 200-parse tests may fail.

- [ ] **Step 3: Implement source_gsma.py**

```python
from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem
from .source_3gpp import Crawler3GPP


class CrawlerGSMA(BaseCrawler):
    source_name = "gsma"
    BASE_URL = "https://www.gsma.com/solutions-and-impact/technologies/networks/"

    def crawl(self) -> list[CrawledItem]:
        try:
            html = self._get_html(self.BASE_URL)
            soup = BeautifulSoup(html, "html.parser")
            items = []
            detector = Crawler3GPP()
            for card in soup.select("article, .card, .news-item")[:15]:
                title_tag = card.select_one("h3 a, h2 a, h3, h2")
                link_tag = card.select_one("a[href]")
                summary_tag = card.select_one("p")
                if not title_tag or not link_tag:
                    continue
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else f"https://www.gsma.com{href}"
                title = title_tag.get_text(strip=True)
                content = summary_tag.get_text(strip=True) if summary_tag else title
                items.append(CrawledItem(
                    source=self.source_name, title=title, url=url,
                    content=content, topic=detector._detect_topic(title + " " + content),
                ))
            return items
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []
```

- [ ] **Step 4: Implement source_etsi.py**

```python
from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem
from .source_3gpp import Crawler3GPP


class CrawlerETSI(BaseCrawler):
    source_name = "etsi"
    BASE_URL = "https://www.etsi.org/news-events/news"

    def crawl(self) -> list[CrawledItem]:
        try:
            html = self._get_html(self.BASE_URL)
            soup = BeautifulSoup(html, "html.parser")
            items = []
            detector = Crawler3GPP()
            for item in soup.select(".news-list-item, article, .item")[:15]:
                title_tag = item.select_one("h3 a, h2 a, h4 a, h3, h2")
                link_tag = item.select_one("a[href]")
                summary_tag = item.select_one("p")
                if not title_tag or not link_tag:
                    continue
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else f"https://www.etsi.org{href}"
                title = title_tag.get_text(strip=True)
                content = summary_tag.get_text(strip=True) if summary_tag else title
                items.append(CrawledItem(
                    source=self.source_name, title=title, url=url,
                    content=content, topic=detector._detect_topic(title + " " + content),
                ))
            return items
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []
```

- [ ] **Step 5: Implement source_ericsson.py**

```python
from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem
from .source_3gpp import Crawler3GPP


class CrawlerEricsson(BaseCrawler):
    source_name = "ericsson"
    BASE_URL = "https://www.ericsson.com/en/blog/tags/core-network"

    def crawl(self) -> list[CrawledItem]:
        try:
            html = self._get_html(self.BASE_URL)
            soup = BeautifulSoup(html, "html.parser")
            items = []
            detector = Crawler3GPP()
            for card in soup.select(".card, article, .blog-post")[:15]:
                title_tag = card.select_one("h3 a, h2 a, h3, h2")
                link_tag = card.select_one("a[href]")
                summary_tag = card.select_one("p")
                if not title_tag or not link_tag:
                    continue
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else f"https://www.ericsson.com{href}"
                title = title_tag.get_text(strip=True)
                content = summary_tag.get_text(strip=True) if summary_tag else title
                items.append(CrawledItem(
                    source=self.source_name, title=title, url=url,
                    content=content, topic=detector._detect_topic(title + " " + content),
                ))
            return items
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []
```

- [ ] **Step 6: Implement source_nokia.py**

```python
from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem
from .source_3gpp import Crawler3GPP


class CrawlerNokia(BaseCrawler):
    source_name = "nokia"
    BASE_URL = "https://www.nokia.com/about-us/news/"

    def crawl(self) -> list[CrawledItem]:
        try:
            html = self._get_html(self.BASE_URL)
            soup = BeautifulSoup(html, "html.parser")
            items = []
            detector = Crawler3GPP()
            for item in soup.select("article, .news-item, .card")[:15]:
                title_tag = item.select_one("h3 a, h2 a, h3, h2")
                link_tag = item.select_one("a[href]")
                summary_tag = item.select_one("p")
                if not title_tag or not link_tag:
                    continue
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else f"https://www.nokia.com{href}"
                title = title_tag.get_text(strip=True)
                content = summary_tag.get_text(strip=True) if summary_tag else title
                items.append(CrawledItem(
                    source=self.source_name, title=title, url=url,
                    content=content, topic=detector._detect_topic(title + " " + content),
                ))
            return items
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []
```

- [ ] **Step 7: Implement source_huawei.py**

```python
from bs4 import BeautifulSoup
from .base import BaseCrawler, CrawledItem
from .source_3gpp import Crawler3GPP


class CrawlerHuawei(BaseCrawler):
    source_name = "huawei"
    BASE_URL = "https://carrier.huawei.com/en/insights"

    def crawl(self) -> list[CrawledItem]:
        try:
            html = self._get_html(self.BASE_URL)
            soup = BeautifulSoup(html, "html.parser")
            items = []
            detector = Crawler3GPP()
            for item in soup.select(".insight-item, article, .card")[:15]:
                title_tag = item.select_one("h3 a, h2 a, h3, h2")
                link_tag = item.select_one("a[href]")
                summary_tag = item.select_one("p")
                if not title_tag or not link_tag:
                    continue
                href = link_tag.get("href", "")
                url = href if href.startswith("http") else f"https://carrier.huawei.com{href}"
                title = title_tag.get_text(strip=True)
                content = summary_tag.get_text(strip=True) if summary_tag else title
                items.append(CrawledItem(
                    source=self.source_name, title=title, url=url,
                    content=content, topic=detector._detect_topic(title + " " + content),
                ))
            return items
        except Exception as e:
            print(f"[{self.source_name}] crawl error: {e}")
            return []
```

- [ ] **Step 8: Run all crawler tests**

```bash
pytest tests/test_crawlers.py tests/test_crawler_base.py -v
```

Expected: all tests PASS.

- [ ] **Step 9: Commit**

```bash
git add agent/crawler/ tests/test_crawlers.py
git commit -m "feat: all 6 crawlers (GSMA, ETSI, Ericsson, Nokia, Huawei)"
```

---

## Task 5: LLM Module

**Files:**
- Create: `agent/llm/prompts.py`
- Create: `agent/llm/claude_client.py`
- Create: `tests/test_llm.py`

**Interfaces:**
- Consumes: `CLAUDE_API_KEY`, `CLAUDE_MODEL` env vars
- Produces:
  - `generate_report(items: list[dict], week_label: str) -> str`
  - `summarize_document(content: str, filename: str) -> str`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_llm.py
import pytest
from unittest.mock import MagicMock, patch
from agent.llm.claude_client import generate_report, summarize_document


SAMPLE_ITEMS = [
    {"source": "3gpp", "title": "NWDAF Release 19", "url": "https://3gpp.org/1",
     "content": "Network automation features.", "topic": "5GC"},
    {"source": "ericsson", "title": "5GC Cloud Native", "url": "https://ericsson.com/1",
     "content": "Cloud native deployment strategies.", "topic": "5GC"},
]


def _mock_anthropic_response(text: str):
    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=text)]
    return mock_msg


def test_generate_report_returns_string():
    with patch("agent.llm.claude_client.get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("📡 BÁO CÁO...")
        result = generate_report(SAMPLE_ITEMS, "Tuần 27/2026")
    assert isinstance(result, str)
    assert len(result) > 0


def test_generate_report_calls_correct_model():
    with patch("agent.llm.claude_client.get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("report")
        generate_report(SAMPLE_ITEMS, "Tuần 27/2026")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 4096


def test_summarize_document_returns_string():
    with patch("agent.llm.claude_client.get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("Tóm tắt: ...")
        result = summarize_document("Document content here", "spec.pdf")
    assert isinstance(result, str)
    assert len(result) > 0


def test_summarize_truncates_long_content():
    long_content = "x" * 20000
    with patch("agent.llm.claude_client.get_client") as mock_get:
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.messages.create.return_value = _mock_anthropic_response("summary")
        summarize_document(long_content, "big.pdf")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    # content sent to Claude must be truncated
    prompt_sent = call_kwargs["messages"][0]["content"]
    assert len(prompt_sent) < len(long_content)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_llm.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.llm.claude_client'`

- [ ] **Step 3: Create agent/llm/prompts.py**

```python
REPORT_PROMPT = """\
Bạn là chuyên gia mạng lõi viễn thông (Core Network Engineer). \
Hãy viết báo cáo công nghệ mới cho {week_label} từ các bài viết được thu thập dưới đây.

DỮ LIỆU ĐẦU VÀO:
{items}

YÊU CẦU ĐỊNH DẠNG:
1. Dòng đầu: tiêu đề "📡 BÁO CÁO CÔNG NGHỆ MẠNG LÕI — {week_label}"
2. Phần TỔNG QUAN (tiếng Việt, 2-3 câu)
3. Các mục theo domain (chỉ ghi mục nếu có nội dung):
   - ## 5G Core (5GC)
   - ## IMS / VoNR
   - ## Autonomous Networks
   - ## EPC / 4G Evolution
   Mỗi bài: tiêu đề tiếng Anh, nguồn, tóm tắt kỹ thuật 3-5 câu tiếng Anh
4. Mục "## 🔗 Tài liệu đáng chú ý" — danh sách links

Viết báo cáo:"""

SUMMARIZE_PROMPT = """\
Bạn là chuyên gia mạng lõi viễn thông. \
Hãy tóm tắt tài liệu kỹ thuật sau phục vụ nghiên cứu công nghệ mạng lõi 4G/5G.

TÊN FILE: {filename}
NỘI DUNG:
{content}

YÊU CẦU:
1. Tổng quan (tiếng Việt, 3-5 câu)
2. Điểm kỹ thuật chính (tiếng Anh, bullet points)
3. Mức độ liên quan: 5GC / IMS / EPC / Autonomous / Không liên quan trực tiếp

Tóm tắt:"""
```

- [ ] **Step 4: Create agent/llm/claude_client.py**

```python
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
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_llm.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/llm/ tests/test_llm.py
git commit -m "feat: LLM module with Claude API"
```

---

## Task 6: Bot REST Client

**Files:**
- Create: `agent/bot/rest_client.py`
- Create: `tests/test_rest_client.py`

**Interfaces:**
- Consumes: `NETCHAT_URL`, `NETCHAT_TOKEN`, `NETCHAT_TEAM_NAME`, `NETCHAT_CHANNEL_NAME` env vars
- Produces: `NetchatRestClient` with:
  - `get_channel_id() -> str`
  - `post_message(message: str, channel_id: str | None = None) -> dict`
  - `download_file(file_id: str) -> bytes`
  - `get_file_info(file_id: str) -> dict`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rest_client.py
import pytest
import responses as resp_lib
from agent.bot.rest_client import NetchatRestClient


@resp_lib.activate
def test_get_channel_id():
    resp_lib.add(
        resp_lib.GET,
        "https://netchat.test.vn/api/v4/channels/name/test-team/test-channel",
        json={"id": "chan123", "name": "test-channel"},
        status=200,
    )
    client = NetchatRestClient()
    cid = client.get_channel_id()
    assert cid == "chan123"


@resp_lib.activate
def test_get_channel_id_cached():
    resp_lib.add(
        resp_lib.GET,
        "https://netchat.test.vn/api/v4/channels/name/test-team/test-channel",
        json={"id": "chan123"},
        status=200,
    )
    client = NetchatRestClient()
    client.get_channel_id()
    client.get_channel_id()  # second call must not re-hit the API
    assert len(resp_lib.calls) == 1


@resp_lib.activate
def test_post_message():
    resp_lib.add(
        resp_lib.GET,
        "https://netchat.test.vn/api/v4/channels/name/test-team/test-channel",
        json={"id": "chan123"},
        status=200,
    )
    resp_lib.add(
        resp_lib.POST,
        "https://netchat.test.vn/api/v4/posts",
        json={"id": "post456", "message": "Hello"},
        status=201,
    )
    client = NetchatRestClient()
    result = client.post_message("Hello")
    assert result["id"] == "post456"


@resp_lib.activate
def test_post_message_with_explicit_channel():
    resp_lib.add(
        resp_lib.POST,
        "https://netchat.test.vn/api/v4/posts",
        json={"id": "post789"},
        status=201,
    )
    client = NetchatRestClient()
    result = client.post_message("Hello", channel_id="explicit_chan")
    body = resp_lib.calls[0].request.body
    assert "explicit_chan" in body


@resp_lib.activate
def test_download_file():
    resp_lib.add(
        resp_lib.GET,
        "https://netchat.test.vn/api/v4/files/file123",
        body=b"PDF content bytes",
        status=200,
    )
    client = NetchatRestClient()
    data = client.download_file("file123")
    assert data == b"PDF content bytes"


@resp_lib.activate
def test_get_file_info():
    resp_lib.add(
        resp_lib.GET,
        "https://netchat.test.vn/api/v4/files/file123/info",
        json={"id": "file123", "name": "spec.pdf", "extension": "pdf"},
        status=200,
    )
    client = NetchatRestClient()
    info = client.get_file_info("file123")
    assert info["name"] == "spec.pdf"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_rest_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.bot.rest_client'`

- [ ] **Step 3: Implement agent/bot/rest_client.py**

```python
import json
import os
import requests


class NetchatRestClient:
    def __init__(self):
        self._base_url = os.environ["NETCHAT_URL"].rstrip("/")
        self._token = os.environ["NETCHAT_TOKEN"]
        self._team_name = os.environ["NETCHAT_TEAM_NAME"]
        self._channel_name = os.environ["NETCHAT_CHANNEL_NAME"]
        self._channel_id: str | None = None
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {self._token}"})

    def _api(self, method: str, path: str, **kwargs):
        url = f"{self._base_url}/api/v4{path}"
        resp = self._session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def get_channel_id(self) -> str:
        if self._channel_id:
            return self._channel_id
        data = self._api("GET", f"/channels/name/{self._team_name}/{self._channel_name}")
        self._channel_id = data["id"]
        return self._channel_id

    def post_message(self, message: str, channel_id: str | None = None) -> dict:
        cid = channel_id or self.get_channel_id()
        return self._api("POST", "/posts", json={"channel_id": cid, "message": message})

    def download_file(self, file_id: str) -> bytes:
        url = f"{self._base_url}/api/v4/files/{file_id}"
        resp = self._session.get(url)
        resp.raise_for_status()
        return resp.content

    def get_file_info(self, file_id: str) -> dict:
        return self._api("GET", f"/files/{file_id}/info")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_rest_client.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent/bot/rest_client.py tests/test_rest_client.py
git commit -m "feat: Netchat REST client"
```

---

## Task 7: Scheduler

**Files:**
- Modify: `agent/scheduler/__init__.py`

**Interfaces:**
- Produces:
  - `init_scheduler(crawl_and_report_fn: callable) -> BackgroundScheduler`
  - `get_next_run() -> str`
  - `stop() -> None`

- [ ] **Step 1: Implement agent/scheduler/__init__.py**

No separate tests — scheduler behavior is verified in the integration test (Task 9). The scheduler must start in background and not block.

```python
import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: BackgroundScheduler | None = None


def init_scheduler(crawl_and_report_fn) -> BackgroundScheduler:
    global _scheduler
    day = os.getenv("REPORT_SCHEDULE_DAY", "mon")
    time_str = os.getenv("REPORT_SCHEDULE_TIME", "08:00")
    timezone = os.getenv("REPORT_TIMEZONE", "Asia/Ho_Chi_Minh")
    hour, minute = time_str.split(":")

    _scheduler = BackgroundScheduler(timezone=timezone)
    _scheduler.add_job(
        crawl_and_report_fn,
        CronTrigger(
            day_of_week=day,
            hour=int(hour),
            minute=int(minute),
            timezone=timezone,
        ),
        id="weekly_report",
        name="Weekly Core Network Report",
        replace_existing=True,
    )
    _scheduler.start()
    return _scheduler


def get_next_run() -> str:
    if not _scheduler:
        return "Scheduler not started"
    job = _scheduler.get_job("weekly_report")
    if job and job.next_run_time:
        return job.next_run_time.strftime("%Y-%m-%d %H:%M %Z")
    return "Unknown"


def stop() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
```

- [ ] **Step 2: Smoke test scheduler starts without error**

```bash
python -c "
import os; os.environ.update({
  'REPORT_SCHEDULE_DAY':'mon','REPORT_SCHEDULE_TIME':'08:00',
  'REPORT_TIMEZONE':'Asia/Ho_Chi_Minh'
})
from agent.scheduler import init_scheduler, get_next_run, stop
s = init_scheduler(lambda: None)
print('Next run:', get_next_run())
stop()
print('OK')
"
```

Expected: prints `Next run: <date>` and `OK`.

- [ ] **Step 3: Commit**

```bash
git add agent/scheduler/__init__.py
git commit -m "feat: APScheduler weekly cron"
```

---

## Task 8: Bot WebSocket + Command Routing + File Handling

**Files:**
- Create: `agent/bot/websocket_client.py`
- Create: `agent/bot/commands.py`
- Create: `tests/test_commands.py`

**Interfaces:**
- Consumes:
  - `NetchatRestClient` from Task 6 (methods: `get_channel_id`, `post_message`, `download_file`, `get_file_info`)
  - `generate_report(items, week_label)` from Task 5
  - `summarize_document(content, filename)` from Task 5
  - `get_recent_items(days)` from Task 2
  - `save_report(trigger_type, content, channel_id)` from Task 2
  - `save_uploaded_doc(filename, file_type, content, summary, uploaded_by)` from Task 2
  - `get_last_crawl_time()` from Task 2
  - `get_next_run()` from Task 7
- Produces:
  - `NetchatWebSocketClient(on_message_callback)` with `start()` and `stop()`
  - `handle_post(post, rest_client, llm_generate, llm_summarize, storage, scheduler_next_run) -> None`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_commands.py
import pytest
from unittest.mock import MagicMock, patch, call
from agent.bot.commands import handle_post


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
    rest = make_rest()
    post = make_post("!report")
    with patch("agent.bot.commands.get_recent_items", return_value=[{"title": "T"}]):
        with patch("agent.bot.commands.generate_report", return_value="📡 Report"):
            with patch("agent.bot.commands.save_report", return_value=1):
                handle_post(post, rest)
    rest.post_message.assert_called_once()
    assert "📡 Report" in rest.post_message.call_args[0][0]


def test_ignores_non_command_in_channel():
    rest = make_rest()
    post = make_post("just a normal message")
    handle_post(post, rest)
    rest.post_message.assert_not_called()


def test_responds_to_non_command_in_dm():
    rest = make_rest()
    post = make_post("what is 5GC?", channel_id="dm_chan", post_type="D")
    with patch("agent.bot.commands.generate_report", return_value="answer"):
        with patch("agent.bot.commands.get_recent_items", return_value=[]):
            with patch("agent.bot.commands.save_report", return_value=1):
                handle_post(post, rest)
    # DM with non-! still gets a response (treated as !report)
    rest.post_message.assert_called_once()


def test_status_command():
    rest = make_rest()
    post = make_post("!status")
    with patch("agent.bot.commands.get_last_crawl_time", return_value="2026-06-30 08:00"):
        with patch("agent.bot.commands.get_next_run", return_value="2026-07-07 08:00"):
            handle_post(post, rest)
    rest.post_message.assert_called_once()
    msg = rest.post_message.call_args[0][0]
    assert "2026-06-30" in msg


def test_sources_command():
    rest = make_rest()
    post = make_post("!sources")
    handle_post(post, rest)
    rest.post_message.assert_called_once()
    msg = rest.post_message.call_args[0][0]
    assert "3gpp" in msg.lower() or "3GPP" in msg


def test_help_command():
    rest = make_rest()
    post = make_post("!help")
    handle_post(post, rest)
    rest.post_message.assert_called_once()
    msg = rest.post_message.call_args[0][0]
    assert "!report" in msg


def test_file_attachment_triggers_summary():
    rest = make_rest()
    post = make_post("", file_ids=["file123"])
    rest.get_file_info.return_value = {"name": "spec.pdf", "extension": "pdf"}
    rest.download_file.return_value = b"%PDF-1.4 content"
    with patch("agent.bot.commands.extract_text_from_bytes", return_value="extracted text"):
        with patch("agent.bot.commands.summarize_document", return_value="Summary"):
            with patch("agent.bot.commands.save_uploaded_doc", return_value=1):
                handle_post(post, rest)
    rest.post_message.assert_called_once()
    assert "Summary" in rest.post_message.call_args[0][0]


def test_ignores_posts_from_other_channels():
    rest = make_rest(channel_id="chan123")
    post = make_post("!report", channel_id="other_chan")
    handle_post(post, rest)
    rest.post_message.assert_not_called()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_commands.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.bot.commands'`

- [ ] **Step 3: Create agent/bot/commands.py**

```python
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
```

- [ ] **Step 4: Create agent/bot/websocket_client.py**

```python
import json
import os
import threading
import websocket


class NetchatWebSocketClient:
    def __init__(self, on_post_callback):
        self._base_url = os.environ["NETCHAT_URL"].rstrip("/")
        self._token = os.environ["NETCHAT_TOKEN"]
        self._on_post_callback = on_post_callback
        self._ws: websocket.WebSocketApp | None = None
        self._thread: threading.Thread | None = None

    def _ws_url(self) -> str:
        return (
            self._base_url
            .replace("https://", "wss://")
            .replace("http://", "ws://")
            + "/api/v4/websocket"
        )

    def _on_open(self, ws):
        auth = {"seq": 1, "action": "authentication_challenge", "data": {"token": self._token}}
        ws.send(json.dumps(auth))
        print("[ws] connected")

    def _on_message(self, ws, raw):
        try:
            event = json.loads(raw)
            if event.get("event") == "posted":
                post = json.loads(event["data"]["post"])
                self._on_post_callback(post)
        except Exception as e:
            print(f"[ws] message error: {e}")

    def _on_error(self, ws, error):
        print(f"[ws] error: {error}")

    def _on_close(self, ws, code, msg):
        print(f"[ws] closed: {code}")

    def start(self):
        self._ws = websocket.WebSocketApp(
            self._ws_url(),
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._thread = threading.Thread(target=self._ws.run_forever, daemon=True)
        self._thread.start()
        print("[ws] listener started")

    def stop(self):
        if self._ws:
            self._ws.close()
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_commands.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/bot/ tests/test_commands.py
git commit -m "feat: WebSocket client + command routing + file handler"
```

---

## Task 9: main.py Integration

**Files:**
- Create: `agent/main.py`

**Interfaces:**
- Consumes: all modules above
- Produces: runnable `python -m agent.main` that starts bot, scheduler, and WebSocket listener

- [ ] **Step 1: Create agent/main.py**

```python
import os
import signal
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from agent.storage.database import init_db, get_recent_items, save_report
from agent.bot.rest_client import NetchatRestClient
from agent.bot.websocket_client import NetchatWebSocketClient
from agent.bot.commands import handle_post
from agent.crawler import run_all_crawlers
from agent.llm.claude_client import generate_report
import agent.scheduler as scheduler_module


_rest: NetchatRestClient | None = None


def crawl_and_report() -> None:
    print(f"[scheduler] Running at {datetime.now().isoformat()}")
    new_count = run_all_crawlers()
    print(f"[scheduler] {new_count} new items crawled")
    items = get_recent_items(days=7)
    if not items:
        print("[scheduler] No items to report")
        return
    week_label = datetime.now().strftime("Tuần %W/%Y")
    report = generate_report(items, week_label)
    channel_id = _rest.get_channel_id()
    save_report("scheduled", report, channel_id)
    _rest.post_message(report)
    print(f"[scheduler] Report sent to {channel_id}")


def main() -> None:
    global _rest
    init_db()
    print("[main] DB initialized")

    _rest = NetchatRestClient()

    def on_post(post: dict) -> None:
        handle_post(post, _rest)

    scheduler_module.init_scheduler(crawl_and_report)
    print(f"[main] Scheduler started. Next run: {scheduler_module.get_next_run()}")

    ws = NetchatWebSocketClient(on_post)
    ws.start()

    def shutdown(sig, frame):
        print("\n[main] Shutting down...")
        scheduler_module.stop()
        ws.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print("[main] Agent ready. Listening on Netchat...")
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify import chain works**

```bash
python -c "from agent.main import main; print('import OK')"
```

Expected: `import OK` with no errors.

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add agent/main.py
git commit -m "feat: main entrypoint, wires all modules"
```

---

## Task 10: Docker Build + Deployment

**Files:**
- Create: `README.md` (deployment guide)

**Interfaces:**
- Produces: `docker-compose up -d --build` runs without error; agent starts and logs `Agent ready`

- [ ] **Step 1: Build Docker image locally**

```bash
docker build -t core-network-agent:latest .
```

Expected: `Successfully built ...`

- [ ] **Step 2: Test container starts**

```bash
docker run --rm \
  -e CLAUDE_API_KEY=test \
  -e NETCHAT_URL=https://netchat.viettel.vn \
  -e NETCHAT_TOKEN=mm_test \
  -e NETCHAT_TEAM_NAME=team \
  -e NETCHAT_CHANNEL_NAME=channel \
  core-network-agent:latest \
  python -c "from agent.main import main; print('container OK')"
```

Expected: `container OK`

- [ ] **Step 3: Create README.md**

```markdown
# Core Network Agent

Agent tự động báo cáo công nghệ mới mạng lõi (5GC, IMS, EPC, Autonomous Networks).

## Cài đặt (GCP VM)

```bash
git clone https://github.com/<you>/core-network-agent.git
cd core-network-agent
cp .env.example .env
# Điền CLAUDE_API_KEY, NETCHAT_TOKEN, NETCHAT_TEAM_NAME, NETCHAT_CHANNEL_NAME vào .env
docker-compose up -d --build
```

## Lệnh bot (trên Netchat)

| Lệnh | Mô tả |
|------|-------|
| `!report` | Tạo báo cáo ngay |
| `!status` | Trạng thái agent |
| `!sources` | Nguồn đang theo dõi |
| `!help` | Trợ giúp |
| _(attach PDF/DOCX)_ | Tóm tắt tài liệu |

## Update

```bash
git pull && docker-compose up -d --build
```
```

- [ ] **Step 4: Push to GitHub**

```bash
git add README.md
git commit -m "docs: deployment guide"
git remote add origin https://github.com/<your-username>/core-network-agent.git
git push -u origin main
```

- [ ] **Step 5: Deploy on GCP VM**

SSH vào VM rồi chạy:

```bash
git clone https://github.com/<your-username>/core-network-agent.git
cd core-network-agent
cp .env.example .env
# nano .env — điền các giá trị thực
docker-compose up -d --build
docker-compose logs -f   # xem log
```

Expected log:
```
[main] DB initialized
[main] Scheduler started. Next run: 2026-07-06 08:00 ICT
[ws] connected
[main] Agent ready. Listening on Netchat...
```

---

## Self-Review Checklist

- [x] **Storage**: `init_db`, `save_crawled_item`, `get_recent_items`, `save_report`, `get_last_crawl_time`, `save_uploaded_doc` — all in Task 2 ✓
- [x] **Crawlers**: 6 sources (3GPP, GSMA, ETSI, Ericsson, Nokia, Huawei) — Tasks 3 & 4 ✓
- [x] **LLM**: `generate_report` + `summarize_document` — Task 5 ✓
- [x] **REST client**: `post_message`, `download_file`, `get_file_info` — Task 6 ✓
- [x] **Scheduler**: weekly cron via APScheduler — Task 7 ✓
- [x] **WebSocket**: event listener, auth handshake — Task 8 ✓
- [x] **Commands**: `!report`, `!status`, `!sources`, `!help`, file attachment — Task 8 ✓
- [x] **File handling**: PDF (pypdf) + DOCX (python-docx) extraction — Task 8 ✓
- [x] **main.py**: wires all modules — Task 9 ✓
- [x] **Docker + deploy**: Dockerfile, docker-compose, GCP instructions — Task 10 ✓
- [x] **Bilingual report**: enforced in REPORT_PROMPT template — Task 5 ✓
- [x] **Bot only responds in configured channel (! prefix) or DM**: enforced in `handle_post` — Task 8 ✓
- [x] **Dedup by URL**: SQLite UNIQUE + IntegrityError catch — Task 2 ✓

import pytest
from agent.storage.database import (
    init_db, save_crawled_item, get_recent_items, get_items_between,
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


def test_get_items_between_filters_by_published_date():
    init_db()
    save_crawled_item("3gpp", "June wk1", "https://x.com/w1", "c", "5GC",
                      published_at="2026-06-03 10:00:00")
    save_crawled_item("3gpp", "June wk3", "https://x.com/w3", "c", "5GC",
                      published_at="2026-06-17 10:00:00")
    save_crawled_item("3gpp", "No date", "https://x.com/nd", "c", "5GC")  # rơi về crawled_at (hôm nay)
    wk1 = get_items_between("2026-06-01", "2026-06-08")
    assert [i["title"] for i in wk1] == ["June wk1"]
    wk3 = get_items_between("2026-06-15", "2026-06-22")
    assert [i["title"] for i in wk3] == ["June wk3"]


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

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
                published_at TIMESTAMP,
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
            CREATE TABLE IF NOT EXISTS settings (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Migration cho DB tạo trước khi có cột published_at
        try:
            conn.execute("ALTER TABLE crawled_items ADD COLUMN published_at TIMESTAMP")
        except sqlite3.OperationalError:
            pass  # cột đã tồn tại


def save_crawled_item(source: str, title: str, url: str, content: str, topic: str,
                      published_at: str | None = None) -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO crawled_items (source, title, url, content, topic, published_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (source, title, url, content, topic, published_at),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_recent_items(days: int = 7) -> list[dict]:
    # Ưu tiên ngày xuất bản; bài không có ngày thì dùng thời điểm crawl
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM crawled_items"
            " WHERE COALESCE(published_at, crawled_at) >= datetime('now', ?)"
            " ORDER BY COALESCE(published_at, crawled_at) DESC",
            (f"-{days} days",),
        ).fetchall()
        return [dict(row) for row in rows]


def get_items_between(start: str, end: str) -> list[dict]:
    """Lấy bài có ngày (xuất bản, hoặc crawl nếu thiếu) trong [start, end) — định dạng 'YYYY-MM-DD'."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM crawled_items"
            " WHERE COALESCE(published_at, crawled_at) >= ?"
            " AND COALESCE(published_at, crawled_at) < ?"
            " ORDER BY COALESCE(published_at, crawled_at) ASC",
            (start, end),
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


def get_setting(key: str, default: str | None = None) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET"
            " value = excluded.value, updated_at = CURRENT_TIMESTAMP",
            (key, value),
        )

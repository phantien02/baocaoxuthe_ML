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

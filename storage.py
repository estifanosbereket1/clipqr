import contextlib
import os
import sqlite3
from pathlib import Path

from content_detector import detect_type, contains_secret

from rapidfuzz import fuzz

import re
import uuid


FUZZY_MATCH_THRESHOLD = 60


def get_db_path():
    base_path = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    db_path = base_path + "/clipvault/history.db"
    os.makedirs(f"{base_path}/clipvault", exist_ok=True)
    return Path(db_path)

def get_images_dir() -> Path:
    base_path = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    images_dir = Path(base_path) / "clipvault" / "images"
    os.makedirs(images_dir, exist_ok=True)
    return images_dir


@contextlib.contextmanager
def get_connection():
    # setup
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        # teardown
        conn.commit()
        conn.close()

def init_db():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY,content TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, pinned BOOLEAN DEFAULT 0)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS tags (entry_id INTEGER NOT NULL, tag TEXT NOT NULL, PRIMARY KEY (entry_id, tag))"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS snippets (id INTEGER PRIMARY KEY, name TEXT NOT NULL, content TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP)"
        )
        cur.execute("PRAGMA table_info(history)")
        columns = [row["name"] for row in cur.fetchall()]
        if "pinned_at" not in columns:
            cur.execute("ALTER TABLE history ADD COLUMN pinned_at DATETIME DEFAULT NULL")
        if "content_type" not in columns:
            cur.execute("ALTER TABLE history ADD COLUMN content_type TEXT DEFAULT NULL")
        if "self_destruct" not in columns:
            cur.execute("ALTER TABLE history ADD COLUMN self_destruct BOOLEAN DEFAULT 0")
        if "origin" not in columns:
            cur.execute("ALTER TABLE history ADD COLUMN origin TEXT DEFAULT 'local'")
        if "contains_secret" not in columns:
            cur.execute("ALTER TABLE history ADD COLUMN contains_secret TEXT DEFAULT NULL")


def get_local_entries_since(since_timestamp: str, exclude_origin: str = None):
    """
    Returns entries that:
      - originated locally on this machine (never re-broadcasts synced-in entries)
      - were created after since_timestamp
      - are not pinned or self-destruct (those never sync)
    """
    with get_connection() as conn:
        cur = conn.cursor()
        return cur.execute(
            """
            SELECT * FROM history
            WHERE origin = 'local'
              AND created_at > ?
              AND pinned = 0
              AND self_destruct = 0
            ORDER BY created_at ASC
            """,
            (since_timestamp,),
        ).fetchall()

def toggle_self_destruct(entry_id):
    with get_connection() as conn:
        cur = conn.cursor()
        current = cur.execute(
            "SELECT self_destruct FROM history WHERE id = ?", (entry_id,)
        ).fetchone()
        if current is None:
            return
        new_value = 0 if current["self_destruct"] else 1
        cur.execute(
            "UPDATE history SET self_destruct = ? WHERE id = ?", (new_value, entry_id)
        )


MAX_PINNED = 5


def get_pinned_entries():
    with get_connection() as conn:
        cur = conn.cursor()
        return cur.execute(
            "SELECT * FROM history WHERE pinned = 1 ORDER BY pinned_at DESC"
        ).fetchall()



def get_oldest_pinned_entry():
    with get_connection() as conn:
        cur = conn.cursor()
        return cur.execute(
            "SELECT * FROM history WHERE pinned = 1 ORDER BY pinned_at ASC LIMIT 1"
        ).fetchone()


def pin_entry(entry_id):
    """
    Attempts to pin an entry. Returns None on success.
    If already at MAX_PINNED, returns the oldest pinned entry instead of pinning,
    so the caller can ask the user to confirm swapping it out.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        count = cur.execute(
            "SELECT COUNT(*) as c FROM history WHERE pinned = 1"
        ).fetchone()["c"]
        if count >= MAX_PINNED:
            return get_oldest_pinned_entry()
        cur.execute(
            "UPDATE history SET pinned = 1, pinned_at = CURRENT_TIMESTAMP WHERE id = ?",
            (entry_id,),
        )
        return None


def unpin_entry(entry_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE history SET pinned = 0, pinned_at = NULL WHERE id = ?", (entry_id,)
        )


def get_recent_unpinned(limit=20):
    with get_connection() as conn:
        cur = conn.cursor()
        return cur.execute(
            "SELECT * FROM history WHERE pinned = 0 ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()


def add_entry(content: str, origin: str = "local"):
    inserted = False
    content = content.strip()
    if content:
        with get_connection() as conn:
            cur = conn.cursor()
            latest_content = cur.execute(
                "SELECT content FROM history ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            if latest_content is None or content != latest_content[0]:
                content_type = detect_type(content)
                secret_type = contains_secret(content)
                cur.execute(
                    "INSERT INTO history (content, content_type, origin, contains_secret) VALUES (?, ?, ?, ?)",
                    (content, content_type, origin, secret_type),
                )
                inserted = True
    return inserted


def add_image_entry(image_bytes: bytes, origin: str = "local"):
    """
    Saves image bytes to a file and inserts a history row pointing at it.
    Skips insertion if the bytes are identical to the most recently added
    image (same duplicate-prevention spirit as add_entry, but comparing
    raw bytes of the last IMAGE specifically, not the last entry overall).
    """
    with get_connection() as conn:
        cur = conn.cursor()
        latest_image_row = cur.execute(
            "SELECT content FROM history WHERE content_type = 'image' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()

        if latest_image_row is not None:
            latest_path = latest_image_row["content"]
            if os.path.exists(latest_path):
                with open(latest_path, "rb") as f:
                    latest_bytes = f.read()
                if latest_bytes == image_bytes:
                    return False  # identical to the last image, skip

        images_dir = get_images_dir()
        filename = f"{uuid.uuid4().hex}.png"
        file_path = str(images_dir / filename)
        with open(file_path, "wb") as f:
            f.write(image_bytes)

        cur.execute(
            "INSERT INTO history (content, content_type, origin) VALUES (?, ?, ?)",
            (file_path, "image", origin),
        )
        return True


def get_history(limit=20):
    with get_connection() as conn:
        cur = conn.cursor()
        latest_contents = cur.execute(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT (?)", (limit,)
        ).fetchall()
        return latest_contents


def get_entry_by_id(entry_id):
    with get_connection() as conn:
        cur = conn.cursor()
        entry = cur.execute(
            "SELECT * FROM history WHERE id = (?)", (entry_id,)
        ).fetchone()
        return entry


def delete_entry(entry_id):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM history where id = (?)", (entry_id,))
        rows_deleted = cur.rowcount
        return rows_deleted


def clear_history():
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM history")

def _register_regex_function(conn):
    def regexp(pattern, value):
        if value is None:
            return False
        try:
            return re.search(pattern, value) is not None
        except re.error:
            return False
    conn.create_function("REGEXP", 2, regexp)



def search_entries(query: str, limit: int = 50, use_regex: bool = False, content_type_filter: str = None, tag_filter: str = None):
    # Only run regex if there is actually a query
    if use_regex and query:
        with get_connection() as conn:
            _register_regex_function(conn)
            cur = conn.cursor()
            sql = "SELECT DISTINCT history.* FROM history"
            if tag_filter:
                sql += " JOIN tags ON tags.entry_id = history.id"
            sql += " WHERE history.content REGEXP ? AND history.pinned = 0"
            params = [query]
            if content_type_filter:
                if content_type_filter == "code":
                    sql += " AND history.content_type LIKE 'code:%'"
                else:
                    sql += " AND history.content_type = ?"
                    params.append(content_type_filter)
            if tag_filter:
                sql += " AND tags.tag = ?"
                params.append(tag_filter)
            sql += " ORDER BY history.created_at DESC LIMIT ?"
            params.append(limit)
            try:
                return cur.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                return []

    with get_connection() as conn:
        cur = conn.cursor()
        candidates_sql = "SELECT DISTINCT history.* FROM history"
        if tag_filter:
            candidates_sql += " JOIN tags ON tags.entry_id = history.id"
        candidates_sql += " WHERE history.pinned = 0"
        params = []
        if content_type_filter:
            if content_type_filter == "code":
                candidates_sql += " AND history.content_type LIKE 'code:%'"
            else:
                candidates_sql += " AND history.content_type = ?"
                params.append(content_type_filter)
        if tag_filter:
            candidates_sql += " AND tags.tag = ?"
            params.append(tag_filter)
        candidates_sql += " ORDER BY history.created_at DESC LIMIT 500"
        candidates = cur.execute(candidates_sql, params).fetchall()

    # If the user is just filtering by tag/type with no text, skip fuzzy matching
    if not query:
        return candidates[:limit]

    scored = []
    for row in candidates:
        score = fuzz.partial_ratio(query.lower(), row["content"].lower())
        if score >= FUZZY_MATCH_THRESHOLD:
            scored.append((score, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [row for score, row in scored[:limit]]


def add_tag(entry_id: int, tag: str):
    tag = tag.strip().lower()
    if not tag:
        return
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO tags (entry_id, tag) VALUES (?, ?)",
            (entry_id, tag),
        )


def remove_tag(entry_id: int, tag: str):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM tags WHERE entry_id = ? AND tag = ?",
            (entry_id, tag),
        )


def get_tags_for_entry(entry_id: int) -> list[str]:
    with get_connection() as conn:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT tag FROM tags WHERE entry_id = ? ORDER BY tag",
            (entry_id,),
        ).fetchall()
        return [row["tag"] for row in rows]


def get_all_tags() -> list[str]:
    with get_connection() as conn:
        cur = conn.cursor()
        rows = cur.execute("SELECT DISTINCT tag FROM tags ORDER BY tag").fetchall()
        return [row["tag"] for row in rows]

def add_snippet(name: str, content: str):
    name = name.strip()
    content = content.strip()
    if not name or not content:
        return None
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO snippets (name, content) VALUES (?, ?)",
            (name, content),
        )
        return cur.lastrowid


def update_snippet(snippet_id: int, name: str, content: str):
    name = name.strip()
    content = content.strip()
    if not name or not content:
        return False
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE snippets SET name = ?, content = ? WHERE id = ?",
            (name, content, snippet_id),
        )
        return cur.rowcount > 0


def delete_snippet(snippet_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM snippets WHERE id = ?", (snippet_id,))
        return cur.rowcount > 0


def get_all_snippets():
    with get_connection() as conn:
        cur = conn.cursor()
        return cur.execute(
            "SELECT * FROM snippets ORDER BY name COLLATE NOCASE"
        ).fetchall()


def get_snippet_by_id(snippet_id: int):
    with get_connection() as conn:
        cur = conn.cursor()
        return cur.execute(
            "SELECT * FROM snippets WHERE id = ?", (snippet_id,)
        ).fetchone()

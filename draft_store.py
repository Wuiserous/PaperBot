import json
import os
import shutil
import sqlite3
import tempfile
import time
import uuid
from typing import Optional


DB_PATH = os.getenv(
    "WEB_DRAFT_DB",
    os.path.join(tempfile.gettempdir(), "paperbot_web_drafts.sqlite3") if os.getenv("VERCEL")
    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "paperbot_web_drafts.sqlite3"),
)
TTL_SECONDS = 60 * 60 * 12
STORE_DIR = os.path.join(
    tempfile.gettempdir(), "paperbot_web_drafts" if os.getenv("VERCEL") else "paperbot_web_drafts_local"
)
FILES_DIR = os.path.join(STORE_DIR, "files")


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    os.makedirs(FILES_DIR, exist_ok=True)
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drafts (
                id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _cleanup_expired(conn) -> None:
    cutoff = int(time.time()) - TTL_SECONDS
    rows = conn.execute("SELECT id, payload_json FROM drafts WHERE updated_at < ?", (cutoff,)).fetchall()
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
            _cleanup_files(payload)
        except Exception:
            pass
    conn.execute("DELETE FROM drafts WHERE updated_at < ?", (cutoff,))


def _cleanup_files(payload: Optional[dict]) -> None:
    if not payload:
        return
    for key in ("pdf_path", "preview_path"):
        path = payload.get(key)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


def _copy_asset(path: str, draft_id: str, suffix: str) -> str:
    if not path or not os.path.exists(path):
        return ""

    _, ext = os.path.splitext(path)
    copied_path = os.path.join(FILES_DIR, f"{draft_id}-{suffix}{ext or ''}")
    shutil.copyfile(path, copied_path)
    return copied_path


def _prepare_payload(payload: dict, draft_id: str, previous_payload: Optional[dict] = None) -> dict:
    prepared = dict(payload)
    if previous_payload:
        _cleanup_files(previous_payload)
    prepared["pdf_path"] = _copy_asset(str(payload.get("pdf_path") or ""), draft_id, "document")
    prepared["preview_path"] = _copy_asset(str(payload.get("preview_path") or ""), draft_id, "preview")
    return prepared


def save_draft(payload: dict, draft_id: Optional[str] = None) -> str:
    _init_db()
    now = int(time.time())
    draft_id = draft_id or uuid.uuid4().hex
    conn = _connect()
    try:
        _cleanup_expired(conn)
        previous_payload = None
        existing_row = conn.execute("SELECT payload_json FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if existing_row:
            previous_payload = json.loads(existing_row["payload_json"])
        stored_payload = _prepare_payload(payload, draft_id, previous_payload=previous_payload)
        conn.execute(
            """
            INSERT INTO drafts (id, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (draft_id, json.dumps(stored_payload), now, now),
        )
        conn.commit()
        return draft_id
    finally:
        conn.close()


def load_draft(draft_id: Optional[str]) -> Optional[dict]:
    if not draft_id:
        return None
    _init_db()
    conn = _connect()
    try:
        _cleanup_expired(conn)
        row = conn.execute("SELECT payload_json FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if not row:
            return None
        conn.execute("UPDATE drafts SET updated_at = ? WHERE id = ?", (int(time.time()), draft_id))
        conn.commit()
        return json.loads(row["payload_json"])
    finally:
        conn.close()


def delete_draft(draft_id: Optional[str]) -> None:
    if not draft_id:
        return
    _init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT payload_json FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if row:
            try:
                _cleanup_files(json.loads(row["payload_json"]))
            except Exception:
                pass
        conn.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
        conn.commit()
    finally:
        conn.close()

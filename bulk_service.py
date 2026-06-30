import csv
import io
import json
import os
import re
import sqlite3
import tempfile
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import database_handler
import letter_service


RATE_LIMIT_INTERVAL_SECONDS = 0.35
MAX_BULK_ROWS = 500
DEFAULT_DB_DIR = tempfile.gettempdir() if os.getenv("VERCEL") else os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("BULK_JOB_DB", os.path.join(DEFAULT_DB_DIR, "bulk_jobs.sqlite3"))

_db_lock = threading.Lock()


def get_required_headers(letter_type: str) -> List[str]:
    schema = letter_service.get_letter_schema().get(letter_type)
    if not schema:
        return []
    return [field["name"] for field in schema["fields"] if field.get("required")]


def get_header_formats() -> Dict[str, str]:
    return {
        letter_type: ",".join(get_required_headers(letter_type))
        for letter_type, _label in letter_service.LETTER_TYPE_OPTIONS
    }


def _normalize_header(header: str) -> str:
    normalized = (header or "").strip().lstrip("\ufeff").lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized)
    return normalized.strip("_")


def _build_header_aliases(letter_type: str) -> Dict[str, str]:
    schema = letter_service.get_letter_schema().get(letter_type) or {}
    aliases = {}
    for field in schema.get("fields", []):
        field_name = field["name"]
        aliases[_normalize_header(field_name)] = field_name
        aliases[_normalize_header(field.get("label", ""))] = field_name
    return aliases


def parse_csv_upload(letter_type: str, file_storage) -> List[dict]:
    required_headers = get_required_headers(letter_type)
    if not required_headers:
        raise ValueError("Select a valid letter type.")

    raw = file_storage.read()
    if not raw:
        raise ValueError("Upload a CSV file.")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Upload a UTF-8 CSV file. Export the sheet as CSV and try again.") from exc

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    header_aliases = _build_header_aliases(letter_type)
    canonical_headers = {}
    for header in headers:
        canonical = header_aliases.get(_normalize_header(header))
        if canonical:
            canonical_headers[header] = canonical

    missing = [header for header in required_headers if header not in canonical_headers.values()]
    if missing:
        expected = ", ".join(required_headers)
        found = ", ".join(headers) if headers else "none"
        raise ValueError(f"CSV missing headers: {', '.join(missing)}. Expected: {expected}. Found: {found}.")

    rows = []
    for index, row in enumerate(reader, start=2):
        clean_row = {}
        for original_header, value in row.items():
            canonical = canonical_headers.get(original_header)
            if canonical:
                clean_row[canonical] = (value or "").strip()

        if not any(clean_row.values()):
            continue

        missing_values = [header for header in required_headers if not clean_row.get(header)]
        if missing_values:
            raise ValueError(f"Row {index} missing values: {', '.join(missing_values)}")

        clean_row["_row_number"] = index
        rows.append(clean_row)

        if len(rows) > MAX_BULK_ROWS:
            raise ValueError(f"Maximum {MAX_BULK_ROWS} rows allowed per upload.")

    if not rows:
        raise ValueError("CSV has no rows to process.")

    return rows


def create_bulk_job(letter_type: str, rows: List[dict]) -> str:
    _init_db()

    if _has_running_job():
        raise ValueError("A bulk job is already running. Wait for it to finish.")

    job_id = uuid.uuid4().hex
    now = _now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO bulk_jobs
            (id, letter_type, status, total, processed, sent, failed, current, errors_json, started_at, finished_at, updated_at)
            VALUES (?, ?, ?, ?, 0, 0, 0, '', '[]', NULL, NULL, ?)
            """,
            (job_id, letter_type, "queued", len(rows), now),
        )

    worker = threading.Thread(target=_run_bulk_job, args=(job_id, letter_type, rows), daemon=True)
    worker.start()
    return job_id


def get_bulk_job(job_id: str) -> Optional[dict]:
    _init_db()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM bulk_jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_job(row) if row else None


def export_failed_rows(job_id: str) -> str:
    job = get_bulk_job(job_id)
    if not job:
        raise ValueError("Bulk job not found.")

    fieldnames = ["row", "name", "email", "domain", "training_from", "date", "cert_id", "error"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for error in job.get("errors", []):
        writer.writerow(error)
    return output.getvalue()


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _db_lock:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with _connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bulk_jobs (
                    id TEXT PRIMARY KEY,
                    letter_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total INTEGER NOT NULL,
                    processed INTEGER NOT NULL,
                    sent INTEGER NOT NULL,
                    failed INTEGER NOT NULL,
                    current TEXT NOT NULL,
                    errors_json TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )


def _has_running_job() -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id FROM bulk_jobs WHERE status IN ('queued', 'running') LIMIT 1"
        ).fetchone()
    return row is not None


def _row_to_job(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "letter_type": row["letter_type"],
        "status": row["status"],
        "total": row["total"],
        "processed": row["processed"],
        "sent": row["sent"],
        "failed": row["failed"],
        "current": row["current"],
        "errors": json.loads(row["errors_json"] or "[]"),
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "updated_at": row["updated_at"],
    }


def _update_job(job_id: str, **updates) -> None:
    if not updates:
        return

    updates["updated_at"] = _now()
    columns = ", ".join(f"{key} = ?" for key in updates)
    values = list(updates.values())
    values.append(job_id)

    with _connect() as conn:
        conn.execute(f"UPDATE bulk_jobs SET {columns} WHERE id = ?", values)


def _increment_job(job_id: str, **increments) -> None:
    if not increments:
        return

    clauses = [f"{key} = {key} + ?" for key in increments]
    clauses.append("updated_at = ?")
    values = list(increments.values())
    values.extend([_now(), job_id])

    with _connect() as conn:
        conn.execute(f"UPDATE bulk_jobs SET {', '.join(clauses)} WHERE id = ?", values)


def _append_error(job_id: str, error_row: dict) -> None:
    job = get_bulk_job(job_id)
    if not job:
        return

    errors = job.get("errors", [])
    errors.append(error_row)
    _update_job(job_id, errors_json=json.dumps(errors))


def _run_bulk_job(job_id: str, letter_type: str, rows: List[dict]) -> None:
    _update_job(job_id, status="running", started_at=_now())

    for row in rows:
        row_number = row.get("_row_number", "")
        name = row.get("name", "")
        _update_job(job_id, current=name or f"Row {row_number}")

        preview_payload = None
        try:
            form_data = {key: value for key, value in row.items() if not key.startswith("_")}
            preview_payload = letter_service.build_letter_preview(letter_type, form_data, create_preview=False)
            sent, recipient_data = letter_service.send_letter_from_preview(preview_payload)

            if not sent:
                raise RuntimeError("Email provider did not confirm send.")

            database_handler.log_activity(
                recipient_data["letter_type"],
                recipient_data["name"],
                recipient_data["email"],
                "Web App Bulk",
                "Sent",
            )
            _increment_job(job_id, sent=1)

        except Exception as exc:
            error_row = {
                "row": row_number,
                "name": row.get("name", ""),
                "email": row.get("email", ""),
                "domain": row.get("domain", ""),
                "training_from": row.get("training_from", ""),
                "date": row.get("date", ""),
                "cert_id": row.get("cert_id", ""),
                "error": str(exc),
            }
            _append_error(job_id, error_row)
            _increment_job(job_id, failed=1)
        finally:
            if preview_payload:
                letter_service.cleanup_files(preview_payload.get("pdf_path"), preview_payload.get("preview_path"))

            _increment_job(job_id, processed=1)
            time.sleep(RATE_LIMIT_INTERVAL_SECONDS)

    job = get_bulk_job(job_id) or {}
    final_status = "failed" if job.get("failed") else "completed"
    _update_job(job_id, status=final_status, current="", finished_at=_now())


def _now() -> str:
    return datetime.utcnow().isoformat()

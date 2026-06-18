import csv
import io
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import database_handler
import letter_service


RATE_LIMIT_INTERVAL_SECONDS = 0.35
MAX_BULK_ROWS = 500

_jobs: Dict[str, dict] = {}
_jobs_lock = threading.Lock()


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


def parse_csv_upload(letter_type: str, file_storage) -> List[dict]:
    required_headers = get_required_headers(letter_type)
    if not required_headers:
        raise ValueError("Select a valid letter type.")

    raw = file_storage.read()
    if not raw:
        raise ValueError("Upload a CSV file.")

    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    missing = [header for header in required_headers if header not in headers]
    if missing:
        raise ValueError(f"CSV missing headers: {', '.join(missing)}")

    rows = []
    for index, row in enumerate(reader, start=2):
        clean_row = {key: (value or "").strip() for key, value in row.items()}
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
    job_id = uuid.uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "id": job_id,
            "letter_type": letter_type,
            "status": "queued",
            "total": len(rows),
            "processed": 0,
            "sent": 0,
            "failed": 0,
            "current": "",
            "errors": [],
            "started_at": None,
            "finished_at": None,
        }

    worker = threading.Thread(target=_run_bulk_job, args=(job_id, letter_type, rows), daemon=True)
    worker.start()
    return job_id


def get_bulk_job(job_id: str) -> Optional[dict]:
    with _jobs_lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


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


def _update_job(job_id: str, **updates) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(updates)


def _append_error(job_id: str, error_row: dict) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id]["errors"].append(error_row)


def _run_bulk_job(job_id: str, letter_type: str, rows: List[dict]) -> None:
    _update_job(job_id, status="running", started_at=datetime.utcnow().isoformat())

    for row in rows:
        row_number = row.get("_row_number", "")
        name = row.get("name", "")
        _update_job(job_id, current=name or f"Row {row_number}")

        preview_payload = None
        try:
            form_data = {key: value for key, value in row.items() if not key.startswith("_")}
            preview_payload = letter_service.build_letter_preview(letter_type, form_data)
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
            with _jobs_lock:
                _jobs[job_id]["sent"] += 1

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
            with _jobs_lock:
                _jobs[job_id]["failed"] += 1
        finally:
            if preview_payload:
                letter_service.cleanup_files(preview_payload.get("pdf_path"), preview_payload.get("preview_path"))

            with _jobs_lock:
                _jobs[job_id]["processed"] += 1

            time.sleep(RATE_LIMIT_INTERVAL_SECONDS)

    final_status = "failed" if get_bulk_job(job_id)["failed"] else "completed"
    _update_job(job_id, status=final_status, current="", finished_at=datetime.utcnow().isoformat())

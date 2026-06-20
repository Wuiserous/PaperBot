import base64
import json
import os
import shutil
import sqlite3
import tempfile
import time
import uuid
from typing import Any

import fitz

import pdf_generator


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RUNTIME_DIR = tempfile.gettempdir() if os.getenv("VERCEL") else BASE_DIR
STORE_DIR = os.path.join(RUNTIME_DIR, "custom_templates")
ASSET_DIR = os.path.join(STORE_DIR, "assets")
PREVIEW_DIR = os.path.join(STORE_DIR, "previews")
DB_PATH = os.path.join(STORE_DIR, "custom_templates.sqlite3")
ALLOWED_FONTS = {"helv", "times-roman", "cour"}


def _ensure_store() -> None:
    os.makedirs(ASSET_DIR, exist_ok=True)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS custom_templates (
                id TEXT PRIMARY KEY,
                owner_user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                source_pdf_path TEXT NOT NULL,
                preview_path TEXT NOT NULL,
                page_width REAL NOT NULL,
                page_height REAL NOT NULL,
                fields_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _connect() -> sqlite3.Connection:
    _ensure_store()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_template(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if not row:
        return None
    template = dict(row)
    try:
        template["fields"] = json.loads(template.pop("fields_json"))
    except json.JSONDecodeError:
        template["fields"] = []
    return template


def _slugify(name: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in name.strip())
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return cleaned or "template"


def _normalize_text(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _sanitize_field(field: dict[str, Any], index: int, page_width: float, page_height: float) -> dict[str, Any]:
    field_type = field.get("type")
    if field_type not in {"simple_text", "textbox"}:
        field_type = "simple_text"

    fontname = _normalize_text(field.get("fontname"), "helv").lower()
    if fontname not in ALLOWED_FONTS:
        fontname = "helv"

    fontsize = int(_clamp(float(field.get("fontsize", 12) or 12), 6, 144))
    width_default = 220 if field_type == "textbox" else 140
    height_default = 70 if field_type == "textbox" else max(18, fontsize + 8)
    width = _clamp(float(field.get("w", width_default) or width_default), 16, page_width)
    height = _clamp(float(field.get("h", height_default) or height_default), 16, page_height)
    x = _clamp(float(field.get("x", 48) or 48), 0, max(0, page_width - width))
    y = _clamp(float(field.get("y", 48) or 48), 0, max(0, page_height - height))
    align = int(field.get("align", 0) or 0)
    if align not in {0, 1, 2}:
        align = 0

    return {
        "type": field_type,
        "key": _normalize_text(field.get("key"), f"field_{index}"),
        "label": _normalize_text(field.get("label"), f"Field {index}"),
        "text": _normalize_text(field.get("text"), "Sample text"),
        "x": round(x, 1),
        "y": round(y, 1),
        "w": round(width, 1),
        "h": round(height, 1),
        "fontsize": fontsize,
        "fontname": fontname,
        "align": align,
    }


def _sanitize_fields(fields: list[dict[str, Any]], page_width: float, page_height: float) -> list[dict[str, Any]]:
    cleaned = []
    for index, field in enumerate(fields, start=1):
        if isinstance(field, dict):
            cleaned.append(_sanitize_field(field, index, page_width, page_height))
    return cleaned


def _template_data_url(path: str) -> str | None:
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        return "data:image/png;base64," + base64.b64encode(handle.read()).decode("ascii")


def list_templates(owner_user_id: int) -> list[dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT id, name, source_pdf_path, preview_path, page_width, page_height, fields_json, created_at, updated_at
            FROM custom_templates
            WHERE owner_user_id = ?
            ORDER BY updated_at DESC, created_at DESC
            """,
            (owner_user_id,),
        ).fetchall()
        return [_row_to_template(row) for row in rows]
    finally:
        conn.close()


def load_template(owner_user_id: int, template_id: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT id, name, source_pdf_path, preview_path, page_width, page_height, fields_json, created_at, updated_at
            FROM custom_templates
            WHERE owner_user_id = ? AND id = ?
            """,
            (owner_user_id, template_id),
        ).fetchone()
        template = _row_to_template(row)
        if template:
            template["preview_data_url"] = _template_data_url(template["preview_path"])
        return template
    finally:
        conn.close()


def create_template(owner_user_id: int, name: str, upload) -> str:
    _ensure_store()
    display_name = _normalize_text(name, "Untitled Template")
    filename = _normalize_text(getattr(upload, "filename", ""), "")
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Upload a PDF template.")

    template_id = uuid.uuid4().hex
    asset_name = f"{_slugify(display_name)}-{template_id[:8]}.pdf"
    asset_path = os.path.join(ASSET_DIR, asset_name)
    upload.save(asset_path)

    doc = fitz.open(asset_path)
    try:
        page = doc[0]
        page_width = float(page.rect.width)
        page_height = float(page.rect.height)
    finally:
        doc.close()

    preview_path = os.path.join(PREVIEW_DIR, f"{template_id}.png")
    generated_preview_path = pdf_generator._create_preview_from_pdf(asset_path)
    if not generated_preview_path or not os.path.exists(generated_preview_path):
        raise ValueError("Could not render a preview from that PDF.")
    shutil.copyfile(generated_preview_path, preview_path)
    if generated_preview_path != preview_path and os.path.exists(generated_preview_path):
        try:
            os.remove(generated_preview_path)
        except OSError:
            pass

    now = int(time.time())
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO custom_templates (
                id, owner_user_id, name, source_pdf_path, preview_path, page_width, page_height, fields_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                template_id,
                owner_user_id,
                display_name,
                asset_path,
                preview_path,
                page_width,
                page_height,
                "[]",
                now,
                now,
            ),
        )
        conn.commit()
        return template_id
    finally:
        conn.close()


def save_template(owner_user_id: int, template_id: str, name: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    template = load_template(owner_user_id, template_id)
    if not template:
        raise ValueError("Template not found.")

    cleaned_fields = _sanitize_fields(fields, float(template["page_width"]), float(template["page_height"]))
    conn = _connect()
    try:
        conn.execute(
            """
            UPDATE custom_templates
            SET name = ?, fields_json = ?, updated_at = ?
            WHERE owner_user_id = ? AND id = ?
            """,
            (
                _normalize_text(name, template["name"]),
                json.dumps(cleaned_fields),
                int(time.time()),
                owner_user_id,
                template_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return load_template(owner_user_id, template_id)


def render_check(owner_user_id: int, template_id: str, fields: list[dict[str, Any]] | None = None) -> str:
    template = load_template(owner_user_id, template_id)
    if not template:
        raise ValueError("Template not found.")

    render_fields = fields if fields is not None else template["fields"]
    render_fields = _sanitize_fields(render_fields, float(template["page_width"]), float(template["page_height"]))

    render_pdf_path = os.path.join(tempfile.gettempdir(), f"paperbot-template-render-{uuid.uuid4().hex}.pdf")
    render_png_path = render_pdf_path.replace(".pdf", ".png")

    doc = fitz.open(template["source_pdf_path"])
    try:
        page = doc[0]
        for field in render_fields:
            text = field["text"]
            if field["type"] == "textbox":
                page.insert_textbox(
                    fitz.Rect(field["x"], field["y"], field["x"] + field["w"], field["y"] + field["h"]),
                    text,
                    fontsize=field["fontsize"],
                    fontname=field["fontname"],
                    align=field["align"],
                    color=(0, 0, 0),
                )
            else:
                page.insert_text(
                    (field["x"], field["y"]),
                    text,
                    fontsize=field["fontsize"],
                    fontname=field["fontname"],
                    color=(0, 0, 0),
                )
        doc.save(render_pdf_path, garbage=4, deflate=True)
    finally:
        doc.close()

    try:
        generated_preview_path = pdf_generator._create_preview_from_pdf(render_pdf_path)
        if generated_preview_path and generated_preview_path != render_png_path:
            shutil.copyfile(generated_preview_path, render_png_path)
        with open(render_png_path, "rb") as handle:
            return "data:image/png;base64," + base64.b64encode(handle.read()).decode("ascii")
    finally:
        for path in (render_pdf_path, render_png_path):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass

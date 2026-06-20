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


def _int_color_to_rgb(color_value: int | None) -> tuple[float, float, float]:
    if color_value is None:
        return 0.0, 0.0, 0.0
    red = ((color_value >> 16) & 255) / 255
    green = ((color_value >> 8) & 255) / 255
    blue = (color_value & 255) / 255
    return red, green, blue


def _safe_slug(value: str, default: str = "field") -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    cleaned = "_".join(part for part in cleaned.split("_") if part)
    return cleaned or default


def _normalize_source(source: dict[str, Any] | None, page_width: float, page_height: float) -> dict[str, Any] | None:
    if not isinstance(source, dict):
        return None

    bbox = source.get("bbox") or [source.get("x"), source.get("y"), source.get("x2"), source.get("y2")]
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        return None

    x0 = _clamp(float(bbox[0] or 0), 0, page_width)
    y0 = _clamp(float(bbox[1] or 0), 0, page_height)
    x1 = _clamp(float(bbox[2] or x0), x0, page_width)
    y1 = _clamp(float(bbox[3] or y0), y0, page_height)
    font_label = _normalize_text(source.get("font_label"), "")
    return {
        "span_id": _normalize_text(source.get("span_id"), ""),
        "text": _normalize_text(source.get("text"), ""),
        "replace_text": _normalize_text(source.get("replace_text"), _normalize_text(source.get("text"), "")),
        "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
        "font_key": _normalize_text(source.get("font_key"), ""),
        "font_label": font_label,
        "font_alias": _normalize_text(source.get("font_alias"), _safe_slug(font_label, "font")),
        "font_size": round(float(source.get("font_size", 12) or 12), 2),
        "color": int(source.get("color", 0) or 0),
        "chars": source.get("chars") if isinstance(source.get("chars"), list) else [],
        "token_ids": source.get("token_ids") if isinstance(source.get("token_ids"), list) else [],
        "line_id": _normalize_text(source.get("line_id"), ""),
        "use_bbox_only": bool(source.get("use_bbox_only")),
    }


def _merge_char_boxes(chars: list[dict[str, Any]]) -> list[float]:
    boxes = [char.get("bbox") for char in chars if isinstance(char.get("bbox"), list) and len(char.get("bbox")) == 4]
    if not boxes:
        return [0.0, 0.0, 0.0, 0.0]
    return [
        round(min(box[0] for box in boxes), 1),
        round(min(box[1] for box in boxes), 1),
        round(max(box[2] for box in boxes), 1),
        round(max(box[3] for box in boxes), 1),
    ]


def _extract_text_spans(pdf_path: str) -> list[dict[str, Any]]:
    doc = fitz.open(pdf_path)
    try:
        page = doc[0]
        fonts = page.get_fonts()
        font_map: dict[str, tuple[int, str]] = {}
        for xref, _ext, _type, base_name, resource_name, _encoding in fonts:
            normalized_name = str(base_name).split("+", 1)[-1]
            font_map[normalized_name] = (int(xref), str(resource_name))
            font_map[str(base_name)] = (int(xref), str(resource_name))

        spans: list[dict[str, Any]] = []
        raw = page.get_text("rawdict")
        counter = 0
        for block_index, block in enumerate(raw.get("blocks", [])):
            for line_index, line in enumerate(block.get("lines", [])):
                line_id = f"line-{block_index}-{line_index}"
                for span_index, span in enumerate(line.get("spans", [])):
                    chars = [
                        {
                            "c": str(char.get("c") or ""),
                            "bbox": [round(float(value), 1) for value in char.get("bbox", [])] if len(char.get("bbox", [])) == 4 else None,
                        }
                        for char in (span.get("chars") or [])
                        if str(char.get("c") or "") and len(char.get("bbox", [])) == 4
                    ]
                    if not chars:
                        continue
                    font_label = str(span.get("font") or "")
                    font_xref, font_key = font_map.get(font_label, font_map.get(font_label.split("+", 1)[-1], (0, "")))
                    word_chars: list[dict[str, Any]] = []
                    for char in chars:
                        if char["c"].isspace():
                            if word_chars:
                                word_text = "".join(item["c"] for item in word_chars)
                                spans.append(
                                    {
                                        "id": f"span-{counter}",
                                        "page": 0,
                                        "text": word_text,
                                        "bbox": _merge_char_boxes(word_chars),
                                        "font_label": font_label,
                                        "font_key": font_key,
                                        "font_xref": int(font_xref or 0),
                                        "font_size": round(float(span.get("size", 12) or 12), 2),
                                        "color": int(span.get("color", 0) or 0),
                                        "flags": int(span.get("flags", 0) or 0),
                                        "chars": word_chars[:],
                                        "line_id": line_id,
                                        "block_index": block_index,
                                        "line_index": line_index,
                                        "span_index": span_index,
                                    }
                                )
                                counter += 1
                                word_chars = []
                            continue
                        word_chars.append(char)

                    if word_chars:
                        word_text = "".join(item["c"] for item in word_chars)
                        spans.append(
                            {
                                "id": f"span-{counter}",
                                "page": 0,
                                "text": word_text,
                                "bbox": _merge_char_boxes(word_chars),
                                "font_label": font_label,
                                "font_key": font_key,
                                "font_xref": int(font_xref or 0),
                                "font_size": round(float(span.get("size", 12) or 12), 2),
                                "color": int(span.get("color", 0) or 0),
                                "flags": int(span.get("flags", 0) or 0),
                                "chars": word_chars[:],
                                "line_id": line_id,
                                "block_index": block_index,
                                "line_index": line_index,
                                "span_index": span_index,
                            }
                        )
                        counter += 1
        return spans
    finally:
        doc.close()


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

    source = _normalize_source(field.get("source"), page_width, page_height)

    detected_font = _normalize_text(field.get("fontname"), source.get("font_alias") if source else "helv").lower()
    fontname = detected_font
    if fontname not in ALLOWED_FONTS:
        fontname = source.get("font_alias") if source and source.get("font_alias") else "helv"

    default_font_size = source.get("font_size", 12) if source else 12
    fontsize = int(_clamp(float(field.get("fontsize", default_font_size) or default_font_size), 6, 144))
    source_bbox = source.get("bbox") if source else None
    width_default = (source_bbox[2] - source_bbox[0]) if source_bbox else (220 if field_type == "textbox" else 140)
    height_default = (source_bbox[3] - source_bbox[1]) if source_bbox else (70 if field_type == "textbox" else max(18, fontsize + 8))
    width = _clamp(float(field.get("w", width_default) or width_default), 16, page_width)
    height = _clamp(float(field.get("h", height_default) or height_default), 16, page_height)
    x_default = source_bbox[0] if source_bbox else 48
    y_default = source_bbox[1] if source_bbox else 48
    x = _clamp(float(field.get("x", x_default) or x_default), 0, max(0, page_width - width))
    y = _clamp(float(field.get("y", y_default) or y_default), 0, max(0, page_height - height))
    align = int(field.get("align", 0) or 0)
    if align not in {0, 1, 2}:
        align = 0

    cleaned = {
        "type": field_type,
        "key": _safe_slug(_normalize_text(field.get("key"), f"field_{index}"), f"field_{index}"),
        "label": _normalize_text(field.get("label"), f"Field {index}"),
        "text": _normalize_text(field.get("text"), source.get("text", "Sample text") if source else "Sample text"),
        "x": round(x, 1),
        "y": round(y, 1),
        "w": round(width, 1),
        "h": round(height, 1),
        "fontsize": fontsize,
        "fontname": fontname,
        "align": align,
        "origin": "extracted" if source else _normalize_text(field.get("origin"), "manual"),
    }
    if source:
        cleaned["source"] = source
    return cleaned


def _sanitize_fields(fields: list[dict[str, Any]], page_width: float, page_height: float) -> list[dict[str, Any]]:
    cleaned = []
    for index, field in enumerate(fields, start=1):
        if isinstance(field, dict):
            cleaned.append(_sanitize_field(field, index, page_width, page_height))
    return cleaned


def _resolve_source_rect(source: dict[str, Any]) -> fitz.Rect:
    if source.get("use_bbox_only"):
        bbox = source.get("bbox") or [0, 0, 0, 0]
        return fitz.Rect(bbox)

    replace_text = _normalize_text(source.get("replace_text"), source.get("text", ""))
    source_text = _normalize_text(source.get("text"), "")
    chars = source.get("chars") or []

    if replace_text and source_text and chars:
        start_index = source_text.find(replace_text)
        if start_index != -1:
            end_index = start_index + len(replace_text)
            selected = chars[start_index:end_index]
            selected_boxes = [char.get("bbox") for char in selected if isinstance(char.get("bbox"), list) and len(char.get("bbox")) == 4]
            if selected_boxes:
                x0 = min(box[0] for box in selected_boxes)
                y0 = min(box[1] for box in selected_boxes)
                x1 = max(box[2] for box in selected_boxes)
                y1 = max(box[3] for box in selected_boxes)
                return fitz.Rect(x0, y0, x1, y1)

    bbox = source.get("bbox") or [0, 0, 0, 0]
    return fitz.Rect(bbox)


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
            template["extracted_spans"] = _extract_text_spans(template["source_pdf_path"])
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
        embedded_fonts: dict[str, bytes] = {}
        for xref, _ext, _type, base_name, resource_name, _encoding in page.get_fonts():
            font_bytes = doc.extract_font(xref)[3]
            if font_bytes:
                embedded_fonts[str(resource_name)] = font_bytes
                embedded_fonts[str(base_name).split("+", 1)[-1]] = font_bytes

        for field in render_fields:
            text = field["text"]
            source = _normalize_source(field.get("source"), float(template["page_width"]), float(template["page_height"]))
            render_rect = fitz.Rect(field["x"], field["y"], field["x"] + field["w"], field["h"] + field["y"])
            font_name = field["fontname"]
            color = (0, 0, 0)
            if source:
                render_rect = _resolve_source_rect(source)
                page.draw_rect(render_rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
                color = _int_color_to_rgb(source.get("color"))
                font_bytes = embedded_fonts.get(source.get("font_key")) or embedded_fonts.get(source.get("font_label"))
                if font_bytes:
                    page.insert_font(fontname=source["font_alias"], fontbuffer=font_bytes)
                    font_name = source["font_alias"]
                else:
                    fallback_name = _normalize_text(font_name, "helv").lower()
                    font_name = fallback_name if fallback_name in ALLOWED_FONTS else "helv"
            elif font_name not in ALLOWED_FONTS:
                font_name = "helv"

            page.insert_textbox(
                render_rect,
                text,
                fontsize=field["fontsize"],
                fontname=font_name,
                align=field["align"],
                color=color,
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

import logging
import os
import base64
from datetime import timedelta

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from config_loader import load_project_env
import draft_store
import web_auth


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_project_env(BASE_DIR)

SECRET = os.getenv("FLASK_SECRET_KEY", "paperbot")

app = Flask(__name__, template_folder="web_templates")
app.secret_key = SECRET
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=45)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.getenv("VERCEL"))
web_auth.register_auth_routes(app)


def _get_form_values_by_type():
    values = session.get("web_form_values_by_type", {})
    return values if isinstance(values, dict) else {}


def _remember_form_values(letter_type: str, form_data: dict) -> None:
    values = _get_form_values_by_type()
    values[letter_type] = dict(form_data)
    session["web_form_values_by_type"] = values


def _clear_form_values(letter_type: str | None = None) -> None:
    if letter_type is None:
        session.pop("web_form_values_by_type", None)
        session.pop("web_form_values", None)
        return

    values = _get_form_values_by_type()
    values.pop(letter_type, None)
    if values:
        session["web_form_values_by_type"] = values
    else:
        session.pop("web_form_values_by_type", None)
    session.pop("web_form_values", None)


def clear_session_draft():
    draft_store.delete_draft(session.pop("web_draft_id", None))


def build_dashboard_context():
    import bulk_service
    import letter_service

    schema = letter_service.get_letter_schema()
    letter_types = letter_service.LETTER_TYPE_OPTIONS
    selected_type = session.get("selected_letter_type", letter_types[0][0])
    user = web_auth.current_web_user() or {}
    draft = draft_store.load_draft(session.get("web_draft_id"))
    if draft:
        draft["id"] = session.get("web_draft_id")
    draft_label = letter_service.get_letter_type_map().get(draft["letter_type"], "") if draft else ""
    form_values_by_type = _get_form_values_by_type()
    preview_token = os.path.getmtime(draft["preview_path"]) if draft and os.path.exists(draft["preview_path"]) else "0"
    just_previewed = bool(session.pop("just_previewed", False))
    preview_data_url = None
    if draft and draft.get("preview_path") and os.path.exists(draft["preview_path"]):
        with open(draft["preview_path"], "rb") as preview_file:
            preview_data_url = "data:image/png;base64," + base64.b64encode(preview_file.read()).decode("ascii")

    return {
        "schema": schema,
        "letter_types": letter_types,
        "selected_type": selected_type,
        "user": user,
        "draft": draft,
        "draft_label": draft_label,
        "draft_matches_selected": bool(draft and draft["letter_type"] == selected_type),
        "form_values_by_type": form_values_by_type,
        "preview_token": preview_token,
        "preview_data_url": preview_data_url,
        "just_previewed": just_previewed,
        "bulk_header_formats": bulk_service.get_header_formats(),
    }


@app.route("/app", methods=["GET"])
@web_auth.require_active_subscription
def web_dashboard():
    return render_template("dashboard.html", **build_dashboard_context())


@app.route("/app/preview", methods=["POST"])
@web_auth.require_active_subscription
def web_preview():
    import letter_service

    letter_type = request.form.get("letter_type", "")
    form_data = request.form.to_dict(flat=True)
    session["selected_letter_type"] = letter_type
    _remember_form_values(letter_type, form_data)

    try:
        preview_payload = letter_service.build_letter_preview(letter_type, form_data)
        previous_draft_id = session.get("web_draft_id")
        new_draft_id = draft_store.save_draft(preview_payload)
        session["web_draft_id"] = new_draft_id
        if previous_draft_id and previous_draft_id != new_draft_id:
            draft_store.delete_draft(previous_draft_id)
        if letter_type == "internship_letter":
            _remember_form_values(letter_type, preview_payload["form_data"])
        session["just_previewed"] = True
        flash("Preview ready.", "success")
    except Exception as exc:
        logging.exception("Web preview generation failed")
        flash(str(exc))

    return redirect(url_for("web_dashboard"))


@app.route("/app/send", methods=["POST"])
@web_auth.require_active_subscription
def web_send():
    import database_handler
    import letter_service

    requested_draft_id = request.form.get("draft_id")
    active_draft_id = session.get("web_draft_id")
    if requested_draft_id and requested_draft_id != active_draft_id:
        flash("The staged preview changed. Please review the latest preview before sending.")
        return redirect(url_for("web_dashboard"))

    draft = draft_store.load_draft(active_draft_id)
    if not draft:
        flash("Generate a preview first.")
        return redirect(url_for("web_dashboard"))

    session["selected_letter_type"] = draft["letter_type"]

    try:
        sent, recipient_data = letter_service.send_letter_from_preview(draft)
        status_text = "Sent" if sent else "Failed"
        database_handler.log_activity(
            recipient_data["letter_type"],
            recipient_data["name"],
            recipient_data["email"],
            "Web App",
            status_text,
        )
        if sent:
            flash(f"Sent to {recipient_data['name']}.", "success")
            clear_session_draft()
        else:
            flash(f"Email could not be sent to {recipient_data['name']}.")
    except Exception as exc:
        logging.exception("Web send failed")
        flash(f"Send failed: {exc}")

    return redirect(url_for("web_dashboard"))


@app.route("/app/clear", methods=["POST"])
@web_auth.require_active_subscription
def web_clear_draft():
    selected_type = session.get("selected_letter_type")
    clear_scope = request.form.get("clear_scope", "all")
    clear_session_draft()
    if clear_scope != "preview_only":
        _clear_form_values(selected_type)
    flash("Cleared.")
    return redirect(url_for("web_dashboard"))


@app.route("/app/preview-image/<draft_id>", methods=["GET"])
def web_preview_image(draft_id):
    draft = draft_store.load_draft(draft_id)
    if not draft:
        return ("Preview not found", 404)

    preview_path = draft.get("preview_path")
    if not preview_path or not os.path.exists(preview_path):
        return ("Preview file missing", 404)

    return send_file(preview_path, mimetype="image/png")


@app.route("/app/bulk/start", methods=["POST"])
@web_auth.require_active_subscription
def web_bulk_start():
    import bulk_service

    letter_type = request.form.get("letter_type", "")
    upload = request.files.get("csv_file")

    if not upload:
        return jsonify({"ok": False, "error": "Upload a CSV file."}), 400

    try:
        rows = bulk_service.parse_csv_upload(letter_type, upload)
        job_id = bulk_service.create_bulk_job(letter_type, rows)
        return jsonify({"ok": True, "job_id": job_id})
    except Exception as exc:
        logging.exception("Bulk upload failed")
        return jsonify({"ok": False, "error": str(exc)}), 400


@app.route("/app/bulk/status/<job_id>", methods=["GET"])
@web_auth.require_active_subscription
def web_bulk_status(job_id):
    import bulk_service

    job = bulk_service.get_bulk_job(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Bulk job not found."}), 404
    return jsonify({"ok": True, "job": job})


@app.route("/app/bulk/failed/<job_id>", methods=["GET"])
@web_auth.require_active_subscription
def web_bulk_failed(job_id):
    import bulk_service

    try:
        csv_text = bulk_service.export_failed_rows(job_id)
    except Exception as exc:
        return Response(str(exc), status=404)

    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=failed-{job_id}.csv"},
    )

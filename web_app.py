import logging
import os
from functools import wraps

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, send_file, session, url_for

import bulk_service
import database_handler
import letter_service
from config_loader import load_project_env


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_project_env(BASE_DIR)

DEFAULT_WEB_PASSWORD = "MySuperSecretPassword123"
SECRET = os.getenv("FLASK_SECRET_KEY", os.getenv("WEB_APP_PASSWORD", DEFAULT_WEB_PASSWORD))
WEB_APP_PASSWORD = os.getenv("WEB_APP_PASSWORD", SECRET)

app = Flask(__name__, template_folder="web_templates")
app.secret_key = SECRET
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


def login_required(route_func):
    return route_func


def clear_session_draft():
    draft = session.pop("web_draft", None)
    if not draft:
        return
    letter_service.cleanup_files(draft.get("pdf_path"), draft.get("preview_path"))


def build_dashboard_context():
    schema = letter_service.get_letter_schema()
    letter_types = letter_service.LETTER_TYPE_OPTIONS
    selected_type = session.get("selected_letter_type", letter_types[0][0])
    draft = session.get("web_draft")
    draft_label = letter_service.get_letter_type_map().get(draft["letter_type"], "") if draft else ""
    form_values = session.get("web_form_values", {})
    preview_token = os.path.getmtime(draft["preview_path"]) if draft and os.path.exists(draft["preview_path"]) else "0"

    return {
        "schema": schema,
        "letter_types": letter_types,
        "selected_type": selected_type,
        "draft": draft,
        "draft_label": draft_label,
        "form_values": form_values,
        "preview_token": preview_token,
        "bulk_header_formats": bulk_service.get_header_formats(),
    }


@app.route("/", methods=["GET"])
def web_index():
    return redirect(url_for("web_dashboard"))


@app.route("/login", methods=["GET", "POST"])
def web_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == WEB_APP_PASSWORD:
            session["web_authenticated"] = True
            return redirect(url_for("web_dashboard"))
        flash("Incorrect password.")
    return render_template("login.html")


@app.route("/logout")
@login_required
def web_logout():
    clear_session_draft()
    session.clear()
    flash("Logged out.")
    return redirect(url_for("web_login"))


@app.route("/app", methods=["GET"])
@login_required
def web_dashboard():
    return render_template("dashboard.html", **build_dashboard_context())


@app.route("/app/preview", methods=["POST"])
@login_required
def web_preview():
    letter_type = request.form.get("letter_type", "")
    form_data = request.form.to_dict(flat=True)
    session["selected_letter_type"] = letter_type
    session["web_form_values"] = form_data

    clear_session_draft()

    try:
        preview_payload = letter_service.build_letter_preview(letter_type, form_data)
        session["web_draft"] = preview_payload
        if letter_type == "internship_letter":
            session["web_form_values"] = preview_payload["form_data"]
        flash("Preview ready.", "success")
    except Exception as exc:
        logging.exception("Web preview generation failed")
        flash(str(exc))

    return redirect(url_for("web_dashboard"))


@app.route("/app/send", methods=["POST"])
@login_required
def web_send():
    draft = session.get("web_draft")
    if not draft:
        flash("Generate a preview first.")
        return redirect(url_for("web_dashboard"))

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
            session.pop("web_form_values", None)
        else:
            flash(f"Email could not be sent to {recipient_data['name']}.")
    except Exception as exc:
        logging.exception("Web send failed")
        flash(f"Send failed: {exc}")

    return redirect(url_for("web_dashboard"))


@app.route("/app/clear", methods=["POST"])
@login_required
def web_clear_draft():
    clear_session_draft()
    session.pop("web_form_values", None)
    flash("Cleared.")
    return redirect(url_for("web_dashboard"))


@app.route("/app/preview-image", methods=["GET"])
@login_required
def web_preview_image():
    draft = session.get("web_draft")
    if not draft:
        return ("Preview not found", 404)

    preview_path = draft.get("preview_path")
    if not preview_path or not os.path.exists(preview_path):
        return ("Preview file missing", 404)

    return send_file(preview_path, mimetype="image/png")


@app.route("/app/bulk/start", methods=["POST"])
@login_required
def web_bulk_start():
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
@login_required
def web_bulk_status(job_id):
    job = bulk_service.get_bulk_job(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Bulk job not found."}), 404
    return jsonify({"ok": True, "job": job})


@app.route("/app/bulk/failed/<job_id>", methods=["GET"])
@login_required
def web_bulk_failed(job_id):
    try:
        csv_text = bulk_service.export_failed_rows(job_id)
    except Exception as exc:
        return Response(str(exc), status=404)

    return Response(
        csv_text,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=failed-{job_id}.csv"},
    )

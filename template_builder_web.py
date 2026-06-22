import json

from flask import flash, jsonify, redirect, render_template, request, url_for

import custom_template_service
import web_auth


def register_template_builder_routes(app):
    def _render_builder(user: dict, selected_template=None):
        templates = custom_template_service.list_templates(user["id"])
        if not selected_template and templates:
            selected_template = custom_template_service.load_template(user["id"], templates[0]["id"])
        return render_template(
            "template_builder.html",
            user=user,
            templates=templates,
            selected_template=selected_template,
        )

    @app.route("/app/templates", methods=["GET"])
    @web_auth.require_active_subscription
    def web_template_builder():
        user = web_auth.current_web_user() or {}
        requested_template_id = request.args.get("template")
        selected_template = None

        if requested_template_id:
            selected_template = custom_template_service.load_template(user["id"], requested_template_id)
        return _render_builder(user, selected_template=selected_template)

    @app.route("/app/templates/create", methods=["POST"])
    @web_auth.require_active_subscription
    def web_template_create():
        user = web_auth.current_web_user() or {}
        upload = request.files.get("template_file")
        if not upload or not upload.filename:
            flash("Upload a PDF template first.")
            return redirect(url_for("web_template_builder"))

        try:
            template_id = custom_template_service.create_template(
                user["id"],
                request.form.get("template_name", ""),
                upload,
            )
            flash("Template ready. Click detected PDF text to create placeholders, then save.", "success")
            return _render_builder(user, selected_template=custom_template_service.load_template(user["id"], template_id))
        except Exception as exc:
            flash(str(exc))
            return _render_builder(user)

    @app.route("/app/templates/<template_id>/save", methods=["POST"])
    @web_auth.require_active_subscription
    def web_template_save(template_id):
        user = web_auth.current_web_user() or {}
        requested_template_id = request.form.get("template_id", template_id) or template_id
        fields_raw = request.form.get("fields_json", "[]")
        selected_template = None
        try:
            fields = json.loads(fields_raw)
            selected_template = custom_template_service.save_template(
                user["id"],
                requested_template_id,
                request.form.get("template_name", ""),
                fields,
            )
            flash("Template saved.", "success")
        except Exception as exc:
            flash(f"Could not save template: {exc}")
        return _render_builder(user, selected_template=selected_template)

    @app.route("/app/templates/<template_id>/render-check", methods=["POST"])
    @web_auth.require_active_subscription
    def web_template_render_check(template_id):
        user = web_auth.current_web_user() or {}
        payload = request.get_json(silent=True) or {}
        try:
            fields = payload.get("fields") or []
            image_data_url = custom_template_service.render_check(user["id"], template_id, fields)
            return jsonify({"ok": True, "image_data_url": image_data_url})
        except Exception as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

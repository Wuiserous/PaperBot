import hashlib
import os
import random
import time
from functools import wraps

from typing import Optional

from flask import jsonify, redirect, render_template, request, session, url_for

import database_handler
from config_loader import load_project_env


load_project_env()

OTP_TTL_SECONDS = 10 * 60


def web_user_id_from_email(email: str) -> int:
    normalized = email.strip().lower()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return (int(digest[:12], 16) % 9000000000) + 1000000000


def send_login_otp(name: str, email: str) -> None:
    import resend

    resend.api_key = os.getenv("RESEND_API_KEY")

    otp = f"{random.randint(0, 999999):06d}"
    expires_at = int(time.time()) + OTP_TTL_SECONDS
    session["pending_login"] = {
        "name": name.strip(),
        "email": email.strip().lower(),
        "otp_hash": _hash_otp(otp),
        "expires_at": expires_at,
    }

    resend.Emails.send(
        {
            "from": f"PaperBot <{os.getenv('DEFAULT_EMAIL', 'support@persevex.com')}>",
            "to": [email],
            "subject": "Your PaperBot login code",
            "html": f"<p>Your PaperBot login code is <strong>{otp}</strong>.</p><p>This code expires in 10 minutes.</p>",
        }
    )


def complete_login(otp: str) -> dict:
    pending = session.get("pending_login")
    if not pending:
        return {"ok": False, "error": "Request a new code."}

    if int(time.time()) > int(pending.get("expires_at", 0)):
        session.pop("pending_login", None)
        return {"ok": False, "error": "Code expired."}

    if _hash_otp(otp.strip()) != pending.get("otp_hash"):
        return {"ok": False, "error": "Incorrect code."}

    user_id = web_user_id_from_email(pending["email"])
    status = database_handler.get_user_status(user_id)
    if status.get("status") == "not_found":
        database_handler.register_new_user(user_id, pending["name"] or pending["email"])
        database_handler.clear_user_cache(user_id)
        status = database_handler.get_user_status(user_id)

    session["web_user"] = {
        "id": user_id,
        "name": pending["name"],
        "email": pending["email"],
    }
    session.pop("pending_login", None)

    return {"ok": True, "active": status.get("status") == "active"}


def current_web_user() -> Optional[dict]:
    return session.get("web_user")


def current_subscription_status() -> dict:
    user = current_web_user()
    if not user:
        return {"status": "not_logged_in"}
    return database_handler.get_user_status(user["id"])


def require_login(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        if not current_web_user():
            return redirect(url_for("web_login"))
        return route_func(*args, **kwargs)

    return wrapper


def require_active_subscription(route_func):
    @wraps(route_func)
    def wrapper(*args, **kwargs):
        if not current_web_user():
            return redirect(url_for("web_login"))

        status = current_subscription_status()
        if status.get("status") != "active":
            return redirect(url_for("web_paywall"))

        return route_func(*args, **kwargs)

    return wrapper


def build_payment_context() -> dict:
    import razorpay_handler

    user = current_web_user()
    status = current_subscription_status()
    payment_url = razorpay_handler.create_payment_link(user["id"]) if user else None
    return {"user": user, "status": status, "payment_url": payment_url}


def register_auth_routes(app):
    @app.route("/", methods=["GET"])
    def web_index():
        if not current_web_user():
            return redirect(url_for("web_login"))
        if current_subscription_status().get("status") != "active":
            return redirect(url_for("web_paywall"))
        return redirect(url_for("web_dashboard"))

    @app.route("/login", methods=["GET"])
    def web_login():
        if current_web_user() and current_subscription_status().get("status") == "active":
            return redirect(url_for("web_dashboard"))
        return render_template("login.html")

    @app.route("/auth/request-otp", methods=["POST"])
    def web_request_otp():
        payload = request.get_json(silent=True) or request.form
        name = (payload.get("name") or "").strip()
        email = (payload.get("email") or "").strip().lower()
        if not name or not email or "@" not in email:
            return jsonify({"ok": False, "error": "Enter name and email."}), 400

        try:
            send_login_otp(name, email)
            return jsonify({"ok": True})
        except Exception:
            app.logger.exception("Failed to send OTP")
            return jsonify({"ok": False, "error": "Could not send code."}), 500

    @app.route("/auth/verify-otp", methods=["POST"])
    def web_verify_otp():
        payload = request.get_json(silent=True) or request.form
        otp = (payload.get("otp") or "").strip()
        if len(otp) != 6:
            return jsonify({"ok": False, "error": "Enter 6 digits."}), 400

        result = complete_login(otp)
        if not result.get("ok"):
            return jsonify(result), 400

        return jsonify({"ok": True, "redirect": url_for("web_dashboard") if result.get("active") else url_for("web_paywall")})

    @app.route("/logout")
    def web_logout():
        session.clear()
        return redirect(url_for("web_login"))

    @app.route("/pay", methods=["GET"])
    @require_login
    def web_paywall():
        return render_template("paywall.html", **build_payment_context())

    @app.route("/pay/check", methods=["POST"])
    @require_login
    def web_check_payment():
        user = current_web_user()
        database_handler.clear_user_cache(user["id"])
        status = database_handler.get_user_status(user["id"])
        if status.get("status") == "active":
            return jsonify({"ok": True, "redirect": url_for("web_dashboard")})
        return jsonify({"ok": False, "error": "Payment not active yet."}), 400


def _hash_otp(otp: str) -> str:
    secret = os.getenv("FLASK_SECRET_KEY", "paperbot")
    return hashlib.sha256(f"{secret}:{otp}".encode("utf-8")).hexdigest()

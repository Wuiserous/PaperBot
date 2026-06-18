import os
import time

from config_loader import load_project_env


load_project_env()

_last_error = None


def get_last_error() -> str | None:
    return _last_error


def create_payment_link(user_id: int):
    """
    Creates a one-time Razorpay payment link for Rs. 999.
    """
    global _last_error
    _last_error = None

    try:
        load_project_env()
        key_id = os.environ.get("RAZORPAY_KEY_ID", "").strip()
        key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "").strip()

        if not key_id or not key_secret:
            _last_error = "Razorpay credentials are missing on this deployment."
            print(_last_error)
            return None

        import razorpay

        client = razorpay.Client(auth=(key_id, key_secret))
        amount_in_paise = 999 * 100

        link_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": "30-Day Access to Telegram Bot",
            "notes": {
                "telegram_user_id": str(user_id),
            },
            "notify": {
                "sms": False,
                "email": False,
            },
            "reminder_enable": False,
            "expire_by": int(time.time()) + 86400,
        }
        payment_link = client.payment_link.create(link_data)
        short_url = payment_link.get("short_url")
        if not short_url:
            _last_error = "Razorpay did not return a payment URL."
            print(_last_error)
            return None

        return short_url

    except Exception as e:
        _last_error = f"Razorpay could not create the payment link: {e}"
        print(_last_error)
        return None

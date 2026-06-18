import os
import time

from config_loader import load_project_env


load_project_env()

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")


def create_payment_link(user_id: int):
    """
    Creates a one-time Razorpay payment link for Rs. 999.
    """
    try:
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
            print("Razorpay credentials are missing.")
            return None

        import razorpay

        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
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
        return payment_link.get("short_url")

    except Exception as e:
        print(f"Error creating Razorpay one-time payment link: {e}")
        return None

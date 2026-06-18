# razorpay_handler.py
import os
import time
from config_loader import load_project_env
import database_handler

load_project_env()

# --- RAZORPAY CONFIGURATION ---
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")
FALLBACK_PAYMENT_LINK = os.environ.get("RAZORPAY_PAYMENT_LINK_URL")


def create_payment_link(user_id: int):
    """
    Creates a ONE-TIME Razorpay Payment Link for ₹999 for 30 days of access.
    """
    try:
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
            print("Razorpay credentials are missing.")
            return FALLBACK_PAYMENT_LINK

        import razorpay

        client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

        # The amount is now hardcoded to ₹999
        amount_in_paise = 999 * 100

        expiry_date = database_handler.get_next_subscription_expiry()

        link_data = {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": f"PaperBot access until {expiry_date}",
            "notes": {
                # This is the most important part for tracking the user
                "telegram_user_id": str(user_id),
                "expiry_date": expiry_date,
                "billing_cycle_day": "8",
            },
            "notify": {
                "sms": False,
                "email": False
            },
            "reminder_enable": False,
            # Link expires after 1 day
            "expire_by": int(time.time()) + 86400
        }
        payment_link = client.payment_link.create(link_data)

        return payment_link.get('short_url')

    except Exception as e:
        print(f"Error creating Razorpay one-time payment link: {e}")
        return FALLBACK_PAYMENT_LINK

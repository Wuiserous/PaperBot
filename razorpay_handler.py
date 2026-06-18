import os

from config_loader import load_project_env


load_project_env()

FIXED_PAYMENT_LINK = os.environ.get("RAZORPAY_PAYMENT_LINK_URL", "").strip()


def create_payment_link(user_id: int):
    """Returns the fixed Razorpay payment link used by both bot and web app."""
    return FIXED_PAYMENT_LINK or None

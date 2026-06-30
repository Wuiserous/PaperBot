# database_handler.py

import os
import json
import requests
import tempfile
from datetime import date, datetime
from config_loader import load_project_env

load_project_env()

# Your Google Apps Script Web App URL
SCRIPT_URL = os.getenv('GOOGLE_SCRIPT_URL')
# The local JSON file for caching user statuses
CACHE_FILE = os.path.join(tempfile.gettempdir(), 'user_status_cache.json') if os.getenv("VERCEL") else 'user_status_cache.json'
SUBSCRIPTION_EXPIRY_DAY = 8


def _load_cache():
    """Loads the user status cache from the JSON file."""
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_cache(cache_data):
    """Saves the user status cache to the JSON file."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache_data, f, indent=4)


def _fetch_from_sheet(params: dict):
    """
    Generic function to make a request to the Google Apps Script.
    This version is corrected to properly handle Google's redirects.
    """
    # Define browser-like headers to ensure the request is not blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    if not SCRIPT_URL:
        return {"status": "error", "message": "GOOGLE_SCRIPT_URL is not configured."}

    try:
        # Make the request, explicitly allowing redirects (which is default but good to be clear)
        response = requests.get(
            SCRIPT_URL,
            params=params,
            headers=headers,
            allow_redirects=True, # This is crucial
            timeout=15
        )

        # Check if the final response is successful
        response.raise_for_status()

        # This is the most important part: a robust check for valid JSON.
        # If the response is not JSON, we will print the raw text to see the error.
        try:
            return response.json()
        except json.JSONDecodeError:
            print("--- FATAL ERROR: RESPONSE FROM GOOGLE WAS NOT JSON ---")
            print(f"Status Code: {response.status_code}")
            print("Response Headers:", response.headers)
            print("Final URL after redirects:", response.url)
            print("Response Text (first 500 chars):", response.text[:500])
            print("------------------------------------------------------")
            return {"status": "error", "message": "The server returned a non-JSON response."}

    except requests.RequestException as e:
        print(f"HTTP Request to Google Sheet failed: {e}")
        return {"status": "error", "message": str(e)}


def clear_user_cache(user_id: int):
    """Removes a single user from the local cache, forcing a refresh on next check."""
    cache = _load_cache()
    if str(user_id) in cache:
        del cache[str(user_id)]
        _save_cache(cache)
        print(f"Cache cleared for user_id: {user_id}")


def get_user_status(user_id: int):
    """
    Checks user status. First checks the local JSON cache, then falls back to the Google Sheet.
    """
    cache = _load_cache()
    user_id_str = str(user_id)

    if user_id_str in cache:
        cached_data = cache[user_id_str]
        # Perform local expiry check first - it's fast and saves an API call
        expiry_date_text = cached_data.get('expiry_date')
        if expiry_date_text:
            expiry_date = datetime.strptime(expiry_date_text, "%Y-%m-%d")
            if datetime.now() > expiry_date and cached_data['status'] != 'expired':
                cached_data['status'] = 'expired'
                cache[user_id_str] = cached_data
                _save_cache(cache)

        print(f"Cache hit for user {user_id_str}. Status: {cached_data['status']}")
        return cached_data

    # If not in cache, fetch from the source of truth (Google Sheet)
    print(f"Cache miss for user {user_id_str}. Fetching from Google Sheet...")
    params = {'action': 'getUserStatus', 'user_id': user_id_str}
    response = _fetch_from_sheet(params)

    if response.get("status") == "success":
        user_data = response["data"]
        # Update the cache with the fresh data
        cache[user_id_str] = user_data
        _save_cache(cache)
        return user_data
    elif response.get("status") == "not_found":
        return {"status": "not_found"}
    else:
        # Return the error but don't cache it
        return {"status": "error", "message": response.get("message", "Unknown error from script")}


def register_new_user(user_id: int, username: str):
    """Registers a new user via the web app. No caching needed here."""
    params = {'action': 'registerNewUser', 'user_id': user_id, 'username': username}
    return _fetch_from_sheet(params)


def get_next_subscription_expiry(today: date | None = None) -> str:
    """Returns the fixed monthly expiry date used by the payment flow."""
    today = today or date.today()
    year = today.year
    month = today.month + 1
    if month == 13:
        month = 1
        year += 1
    return date(year, month, SUBSCRIPTION_EXPIRY_DAY).strftime("%Y-%m-%d")


def log_activity(letter_type: str, recipient_name: str, recipient_email: str, sent_by: str, status: str):
    """Logs an activity via the web app. This is a 'fire-and-forget' action."""
    params = {
        'action': 'logActivity',
        'letter_type': letter_type,
        'recipient_name': recipient_name,
        'recipient_email': recipient_email,
        'sent_by': sent_by,
        'status': status
    }
    response = _fetch_from_sheet(params)
    return response.get("status") == "success"


def update_user_subscription(user_id: int):
    """
    Updates a user's subscription in the Google Sheet and clears the local cache for that user.
    This should be called by your Razorpay webhook handler.
    """
    params = {
        'action': 'updateSubscription',
        'user_id': user_id,
        'expiry_date': get_next_subscription_expiry(),
    }
    response = _fetch_from_sheet(params)
    if response.get("status") == "success":
        # Important: Clear the old cached data to force a refresh on the next check
        clear_user_cache(user_id)
        return True
    return False


def fetch_student_from_client_sheet(name: str):
    """
    Fetches student info from the client's Google Sheet via Apps Script.
    Returns the JSON object if found, otherwise None.
    """
    CLIENT_SCRIPT_URL = os.getenv("CLIENT_SCRIPT_URL")  # Make sure this env variable is set
    if not CLIENT_SCRIPT_URL:
        raise RuntimeError("CLIENT_SCRIPT_URL is not configured.")

    try:
        params = {'action': 'findStudent', 'name': name}
        response = requests.get(CLIENT_SCRIPT_URL, params=params, allow_redirects=True, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == "success":
            return data  # Return the full JSON object as is
        if data.get("status") in {"not_found", "missing"}:
            return None
        message = data.get("message") or "Unknown error from client's sheet."
        print(f"Client's Sheet API Error: {message}")
        raise RuntimeError(message)

    except requests.RequestException as e:
        print(f"HTTP Request to client's sheet failed: {e}")
        raise RuntimeError(f"Could not check the onboarding sheet: {e}") from e
    except ValueError as e:
        print(f"Client's Sheet API returned invalid JSON: {e}")
        raise RuntimeError("Could not check the onboarding sheet: invalid JSON response.") from e

# print(fetch_student_from_client_sheet('Wuis'))

# create_database.py
import sqlite3

# Connect to the database file (it will be created if it doesn't exist)
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()

# --- Create the Users table ---
# This is where we will store subscription and trial info
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    trial_start_date TEXT,
    subscription_status TEXT NOT NULL,
    subscription_expiry_date TEXT NOT NULL,
    razorpay_subscription_id TEXT
);
''')

# --- Create the Activity Log table ---
# This is the new home for our live dashboard log
cursor.execute('''
CREATE TABLE IF NOT EXISTS activity_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    letter_type TEXT,
    recipient_name TEXT,
    recipient_email TEXT,
    sent_by TEXT,
    status TEXT NOT NULL
);
''')

# --- Create the Client Students table (Optional but Recommended) ---
# This is for the "Internship Acceptance" flow. Instead of calling a slow
# external URL, you could periodically import your client's student data here for fast lookups.
# For now, we will keep the external API call, but this is the future path.
cursor.execute('''
CREATE TABLE IF NOT EXISTS client_students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    email TEXT,
    month TEXT,
    domain TEXT
);
''')


# Commit the changes and close the connection
conn.commit()
conn.close()

print("Database 'bot_database.db' and tables created successfully.")
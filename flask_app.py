import os
import asyncio
import logging
from datetime import timedelta
from collections import deque
from functools import wraps
from flask import Flask, Response, flash, jsonify, redirect, render_template, request, send_file, session, url_for

# Your Custom Modules (Must be in the same folder)
import bulk_service
import pdf_generator
import database_handler
import razorpay_handler
import draft_store
from email_sender import send_personalized_email
import letter_service
from config_loader import load_project_env
import web_auth

# Telegram Imports
from telegram import ReplyKeyboardMarkup, Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, ConversationHandler,
    MessageHandler, filters, ContextTypes, CallbackQueryHandler,
    PicklePersistence, ApplicationBuilder
)

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_project_env(BASE_DIR)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SECRET = "MySuperSecretPassword123"

app = Flask(__name__, template_folder="web_templates")
app.secret_key = os.getenv("FLASK_SECRET_KEY", SECRET)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=45)
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = bool(os.getenv("VERCEL"))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
web_auth.register_auth_routes(app)

(
    AWAITING_PAYMENT_CONFIRMATION,
    GET_CA_NAME, GET_CA_EMAIL, CONFIRM_CA,
    GET_INTERN_NAME, CONFIRM_INTERN,
    GET_OFFER_NAME, GET_OFFER_EMAIL, GET_OFFER_TRAINING_DATE, CONFIRM_OFFER,
    GET_CERT_NAME, GET_CERT_EMAIL, GET_CERT_DOMAIN, GET_CERT_DATE, GET_CERT_ID, CONFIRM_CERT,
    GET_CACERT_NAME, GET_CACERT_EMAIL, GET_CACERT_DATE, CONFIRM_CACERT
) = range(20)

# Tracker prevents Telegram from resending messages if email takes a few seconds
processed_updates = deque(maxlen=1000)

RESET_KEYBOARD = ReplyKeyboardMarkup(
    [["🏠 Main Menu / Reset"]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# ==========================================
# 2. LOGIC FUNCTIONS
# ==========================================

async def gatekeeper_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name

    try:
        status_data = await asyncio.to_thread(database_handler.get_user_status, user_id)
        status = status_data.get("status")

        if status == "not_found":
            await asyncio.to_thread(database_handler.register_new_user, user_id, username)
            await context.bot.send_message(chat_id=user_id, text="Welcome! To access all features, subscribe for ₹999/month.")
            await show_paywall(update, context)
            return False

        if status == "active": return True

        if status == "expired":
            await show_paywall(update, context)
            return False

        await context.bot.send_message(chat_id=user_id, text=f"Error checking status.")
        return False
    except Exception as e:
        logging.error(f"Gatekeeper error: {e}")
        await context.bot.send_message(chat_id=user_id, text="⚠️ Database timeout. Please try again.")
        return False

async def show_paywall(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    payment_url = await asyncio.to_thread(razorpay_handler.create_payment_link, user_id)
    text = "Your access has expired. Please click the button below to make a one-time payment for 30 days of full access."

    if payment_url:
        keyboard = [
            [InlineKeyboardButton("Pay ₹999 for 30 Days Access", url=payment_url)],
            [InlineKeyboardButton("✅ I've Paid, Check My Status", callback_data="check_payment_status")]
        ]
        if update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=InlineKeyboardMarkup(keyboard))
        return AWAITING_PAYMENT_CONFIRMATION
    else:
        await context.bot.send_message(chat_id=chat_id, text="Could not create a payment link right now.")
        return ConversationHandler.END

async def handle_payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text="🔄 Checking your status, please wait...")

    await asyncio.to_thread(database_handler.clear_user_cache, update.effective_user.id)
    status_data = await asyncio.to_thread(database_handler.get_user_status, update.effective_user.id)

    if status_data.get("status") == "active":
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Payment confirmed! Your subscription is active until {status_data.get('expiry_date')}.")
        await show_main_options(update, context)
        return ConversationHandler.END
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="⚠️ Your subscription is not active yet. It can take a minute to update.")
        return AWAITING_PAYMENT_CONFIRMATION

async def show_main_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [
        [InlineKeyboardButton("🎓 CA Letter", callback_data="opt_ca_letter")],
        [InlineKeyboardButton("💼 Internship Letter", callback_data="opt_intern_letter")],
        [InlineKeyboardButton("📜 Offer Letter", callback_data="opt_offer_letter")],
        [InlineKeyboardButton("🏆 Course Certificate", callback_data="opt_cert")],
        [InlineKeyboardButton("⭐ CA Certificate", callback_data="opt_ca_cert")]
    ]
    text = "🤖 **Main Menu**\nPlease choose an action below:\n\n_(Tip: Use the '🏠 Main Menu' button anytime to return here)_"

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    return ConversationHandler.END

async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query: await update.callback_query.answer()
    data = context.user_data
    if 'pdf_path' in data:
        full_pdf = os.path.join(BASE_DIR, data['pdf_path']) if not os.path.isabs(data['pdf_path']) else data['pdf_path']
        if os.path.exists(full_pdf): os.remove(full_pdf)
    if 'preview_path' in data:
        full_prev = os.path.join(BASE_DIR, data['preview_path']) if not os.path.isabs(data['preview_path']) else data['preview_path']
        if os.path.exists(full_prev): os.remove(full_prev)

    context.user_data.clear()
    msg = "🔄 Bot state has been reset."
    if update.message: await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    elif update.callback_query: await update.callback_query.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    await show_main_options(update, context)
    return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Welcome!", reply_markup=ReplyKeyboardRemove())
    if await gatekeeper_check(update, context):
        await show_main_options(update, context)
        return ConversationHandler.END
    return AWAITING_PAYMENT_CONFIRMATION

def get_user_display_name(update: Update) -> str:
    user = update.effective_user
    return user.full_name or user.username or f"ID:{user.id}"

async def process_and_send_letter(update: Update, context: ContextTypes.DEFAULT_TYPE, letter_type: str):
    """A single function to email the pre-generated PDF and log the activity."""
    query = update.callback_query
    await query.answer()

    if not await gatekeeper_check(update, context):
        await query.edit_message_text(text="Sorry, your subscription status changed.")
        context.user_data.clear()
        return AWAITING_PAYMENT_CONFIRMATION

    await query.edit_message_text(text="Processing and sending...")

    user_display_name = get_user_display_name(update)
    data = context.user_data
    pdf_path = data.get('pdf_path')

    # ENSURE ABSOLUTE PATH FOR PA
    if pdf_path and not os.path.isabs(pdf_path):
        pdf_path = os.path.join(BASE_DIR, pdf_path)

    email_sent = False
    recipient_data = {}

    try:
        if not pdf_path or not os.path.exists(pdf_path):
            raise FileNotFoundError("The generated PDF file could not be found.")

        if letter_type == "CA":
            recipient_data = {"name": data['name'], "email": data['email'], "domain": "Community", "letter_type": "Campus Ambassador"}
            email_sent = await asyncio.to_thread(send_personalized_email, pdf_path, recipient_data)
        elif letter_type == "Intern":
            recipient_data = {"name": data['name'], "email": data['email'], "domain": data['domain'], "letter_type": "Internship Acceptance"}
            email_sent = await asyncio.to_thread(send_personalized_email, pdf_path, recipient_data)
        elif letter_type == "Offer":
            recipient_data = {"name": data['name'], "email": data['email'], "domain": "General", "letter_type": "Offer Letter"}
            email_sent = await asyncio.to_thread(send_personalized_email, pdf_path, recipient_data)
        elif letter_type == "Certificate":
            recipient_data = {"name": data['name'], "email": data['email'], "domain": data['domain'], "letter_type": "Course Completion Certificate"}
            email_sent = await asyncio.to_thread(send_personalized_email, pdf_path, recipient_data)
        elif letter_type == "CA_Certificate":
            recipient_data = {"name": data['name'], "email": data['email'], "domain": "Community", "letter_type": "Campus Ambassador Certificate"}
            email_sent = await asyncio.to_thread(send_personalized_email, pdf_path, recipient_data)

        if email_sent:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"✅ Success! The letter has been sent to {data['name']}.")
            database_handler.log_activity(recipient_data['letter_type'], data['name'], data['email'], user_display_name, "✅ Sent")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"⚠️ Failure! The email to {data['name']} could not be sent.")
            database_handler.log_activity(recipient_data['letter_type'], data['name'], data['email'], user_display_name, "⚠️ Failed")

    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"An unexpected error occurred: {e}")
        database_handler.log_activity(data.get('letter_type', 'Unknown'), data.get('name', 'N/A'), data.get('email', 'N/A'), user_display_name, f"❌ Error: {e}")

    finally:
        # Cleanup files
        if 'pdf_path' in data:
            full_pdf = os.path.join(BASE_DIR, data['pdf_path']) if not os.path.isabs(data['pdf_path']) else data['pdf_path']
            if os.path.exists(full_pdf): os.remove(full_pdf)

        if 'preview_path' in data:
            full_prev = os.path.join(BASE_DIR, data['preview_path']) if not os.path.isabs(data['preview_path']) else data['preview_path']
            if os.path.exists(full_prev): os.remove(full_prev)

        context.user_data.clear()
        return await reset_command(update, context)

# ==========================================
# FLOW HANDLERS
# ==========================================
async def start_ca_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    if not await gatekeeper_check(update, context): return AWAITING_PAYMENT_CONFIRMATION
    context.user_data.clear()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Let's create a Campus Ambassador Letter.\nWhat is the candidate's full name?", reply_markup=RESET_KEYBOARD)
    return GET_CA_NAME

async def get_ca_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("Got it. What is their email address?", reply_markup=RESET_KEYBOARD)
    return GET_CA_EMAIL

async def get_ca_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['email'] = update.message.text.strip()
    msg = await update.message.reply_text("⚙️ Generating preview... please wait.")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='upload_photo')
    try:
        pdf_path, preview_path = await asyncio.to_thread(pdf_generator.generate_campus_ambassador_pdf_with_preview, context.user_data['name'])
        context.user_data['pdf_path'], context.user_data['preview_path'] = pdf_path, preview_path
        abs_preview = os.path.join(BASE_DIR, preview_path) if not os.path.isabs(preview_path) else preview_path
        await msg.delete()
        with open(abs_preview, 'rb') as photo_file: await update.message.reply_photo(photo=photo_file)
        keyboard = [[InlineKeyboardButton("✅ Yes, Send Now", callback_data="send_ca")], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_final")]]
        await update.message.reply_text(f"Send full letter to **{context.user_data['email']}**?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_CA
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
        return await reset_command(update, context)

async def start_intern_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    if not await gatekeeper_check(update, context): return AWAITING_PAYMENT_CONFIRMATION
    context.user_data.clear()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Let's create an Internship Acceptance Letter.\nWhat is the intern's full name?", reply_markup=RESET_KEYBOARD)
    return GET_INTERN_NAME

async def process_intern_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    msg = await update.message.reply_text(f"🔍 Searching for '{name}' in database... Please wait.")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
    try:
        student_data = await asyncio.to_thread(database_handler.fetch_student_from_client_sheet, name)
        if not student_data:
            await msg.edit_text(f"⚠️ Could not find '{name}' in the Onboarding sheet.")
            return GET_INTERN_NAME
        context.user_data.update(student_data)
        await msg.edit_text(f"✅ Found! Generating preview for {name}...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='upload_photo')
        pdf_path, preview_path = await asyncio.to_thread(pdf_generator.generate_internship_acceptance_pdf_with_preview, name=student_data['name'], month=student_data['month'], domain=student_data['domain'])
        context.user_data['pdf_path'], context.user_data['preview_path'] = pdf_path, preview_path
        abs_preview = os.path.join(BASE_DIR, preview_path) if not os.path.isabs(preview_path) else preview_path
        await msg.delete()
        with open(abs_preview, 'rb') as photo_file: await update.message.reply_photo(photo=photo_file)
        keyboard = [[InlineKeyboardButton("✅ Yes, Send Now", callback_data="send_intern")], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_final")]]
        await update.message.reply_text(f"Send full letter to **{student_data['email']}**?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_INTERN
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
        return await reset_command(update, context)

async def start_offer_letter_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    if not await gatekeeper_check(update, context): return AWAITING_PAYMENT_CONFIRMATION
    context.user_data.clear()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Offer Letter.\nWhat is the candidate's full name?", reply_markup=RESET_KEYBOARD)
    return GET_OFFER_NAME

async def get_offer_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("Got it. Email address?", reply_markup=RESET_KEYBOARD)
    return GET_OFFER_EMAIL

async def get_offer_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['email'] = update.message.text.strip()
    await update.message.reply_text("Training start date? (e.g., DD-MM-YYYY)", reply_markup=RESET_KEYBOARD)
    return GET_OFFER_TRAINING_DATE

async def get_offer_training_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['training_from'] = update.message.text.strip()
    msg = await update.message.reply_text("⚙️ Generating preview... please wait.")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='upload_photo')
    try:
        pdf_path, preview_path = await asyncio.to_thread(pdf_generator.generate_offer_letter_pdf_with_preview, name=context.user_data['name'], training_from=context.user_data['training_from'])
        context.user_data['pdf_path'], context.user_data['preview_path'] = pdf_path, preview_path
        abs_preview = os.path.join(BASE_DIR, preview_path) if not os.path.isabs(preview_path) else preview_path
        await msg.delete()
        with open(abs_preview, 'rb') as photo_file: await update.message.reply_photo(photo=photo_file)
        keyboard = [[InlineKeyboardButton("✅ Yes, Send Now", callback_data="send_offer")], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_final")]]
        await update.message.reply_text(f"Send to **{context.user_data['email']}**?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_OFFER
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
        return await reset_command(update, context)

async def start_certificate_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    if not await gatekeeper_check(update, context): return AWAITING_PAYMENT_CONFIRMATION
    context.user_data.clear()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Course Certificate.\nStudent's name?", reply_markup=RESET_KEYBOARD)
    return GET_CERT_NAME

async def get_cert_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("Email address?", reply_markup=RESET_KEYBOARD)
    return GET_CERT_EMAIL

async def get_cert_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['email'] = update.message.text.strip()
    await update.message.reply_text("Domain/Course name?", reply_markup=RESET_KEYBOARD)
    return GET_CERT_DOMAIN

async def get_cert_domain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['domain'] = update.message.text.strip()
    await update.message.reply_text("Issue Date? (e.g., 15 November, 2025)", reply_markup=RESET_KEYBOARD)
    return GET_CERT_DATE

async def get_cert_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['date'] = update.message.text.strip()
    await update.message.reply_text("Certificate ID for QR code?", reply_markup=RESET_KEYBOARD)
    return GET_CERT_ID

async def get_cert_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['cert_id'] = update.message.text.strip()
    msg = await update.message.reply_text("⚙️ Generating preview... please wait.")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='upload_photo')
    try:
        pdf_path, preview_path = await asyncio.to_thread(pdf_generator.generate_completion_certificate, name=context.user_data['name'], issue_date=context.user_data['date'], domain=context.user_data['domain'], identifier_id=context.user_data['cert_id'])
        context.user_data['pdf_path'], context.user_data['preview_path'] = pdf_path, preview_path
        abs_preview = os.path.join(BASE_DIR, preview_path) if not os.path.isabs(preview_path) else preview_path
        await msg.delete()
        with open(abs_preview, 'rb') as photo_file: await update.message.reply_photo(photo=photo_file)
        keyboard = [[InlineKeyboardButton("✅ Yes, Send Now", callback_data="send_cert")], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_final")]]
        await update.message.reply_text(f"Send to **{context.user_data['email']}**?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_CERT
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
        return await reset_command(update, context)

async def start_ca_cert_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    if not await gatekeeper_check(update, context): return AWAITING_PAYMENT_CONFIRMATION
    context.user_data.clear()
    await context.bot.send_message(chat_id=update.effective_chat.id, text="CA Certificate.\nCandidate's name?", reply_markup=RESET_KEYBOARD)
    return GET_CACERT_NAME

async def get_ca_cert_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text("Email address?", reply_markup=RESET_KEYBOARD)
    return GET_CACERT_EMAIL

async def get_ca_cert_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['email'] = update.message.text.strip()
    await update.message.reply_text("Issue Date?", reply_markup=RESET_KEYBOARD)
    return GET_CACERT_DATE

async def get_ca_cert_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['date'] = update.message.text.strip()
    msg = await update.message.reply_text("⚙️ Generating preview... please wait.")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='upload_photo')
    try:
        pdf_path, preview_path = await asyncio.to_thread(pdf_generator.ca_certificate, name=context.user_data['name'], issue_date=context.user_data['date'])
        context.user_data['pdf_path'], context.user_data['preview_path'] = pdf_path, preview_path
        abs_preview = os.path.join(BASE_DIR, preview_path) if not os.path.isabs(preview_path) else preview_path
        await msg.delete()
        with open(abs_preview, 'rb') as photo_file: await update.message.reply_photo(photo=photo_file)
        keyboard = [[InlineKeyboardButton("✅ Yes, Send Now", callback_data="send_cacert")], [InlineKeyboardButton("❌ Cancel", callback_data="cancel_final")]]
        await update.message.reply_text(f"Send to **{context.user_data['email']}**?", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_CACERT
    except Exception as e:
        await msg.edit_text(f"❌ Error: {e}")
        return await reset_command(update, context)

# ==========================================
# 3. GLOBAL SINGLETON (The Magic Fix)
# ==========================================

def get_telegram_handlers():
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(handle_payment_confirmation, pattern="^check_payment_status$"),
            CallbackQueryHandler(start_ca_flow, pattern="^opt_ca_letter$"),
            CallbackQueryHandler(start_intern_flow, pattern="^opt_intern_letter$"),
            CallbackQueryHandler(start_offer_letter_flow, pattern="^opt_offer_letter$"),
            CallbackQueryHandler(start_certificate_flow, pattern="^opt_cert$"),
            CallbackQueryHandler(start_ca_cert_flow, pattern="^opt_ca_cert$")
        ],
        states={
            AWAITING_PAYMENT_CONFIRMATION: [CallbackQueryHandler(handle_payment_confirmation, pattern="^check_payment_status$")],
            GET_CA_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_ca_name)],
            GET_CA_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_ca_email)],
            CONFIRM_CA: [CallbackQueryHandler(lambda u, c: process_and_send_letter(u, c, "CA"), pattern="^send_ca$")],
            GET_INTERN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), process_intern_name)],
            CONFIRM_INTERN: [CallbackQueryHandler(lambda u, c: process_and_send_letter(u, c, "Intern"), pattern="^send_intern$")],
            GET_OFFER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_offer_name)],
            GET_OFFER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_offer_email)],
            GET_OFFER_TRAINING_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_offer_training_date)],
            CONFIRM_OFFER: [CallbackQueryHandler(lambda u, c: process_and_send_letter(u, c, "Offer"), pattern="^send_offer$")],
            GET_CERT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_cert_name)],
            GET_CERT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_cert_email)],
            GET_CERT_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_cert_domain)],
            GET_CERT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_cert_date)],
            GET_CERT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_cert_id)],
            CONFIRM_CERT: [CallbackQueryHandler(lambda u, c: process_and_send_letter(u, c, "Certificate"), pattern="^send_cert$")],
            GET_CACERT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_ca_cert_name)],
            GET_CACERT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_ca_cert_email)],
            GET_CACERT_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^🏠"), get_ca_cert_date)],
            CONFIRM_CACERT: [CallbackQueryHandler(lambda u, c: process_and_send_letter(u, c, "CA_Certificate"), pattern="^send_cacert$")],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("menu", reset_command),
            CommandHandler("reset", reset_command),
            MessageHandler(filters.Regex("^🏠 Main Menu / Reset$"), reset_command),
            CallbackQueryHandler(reset_command, pattern="^cancel_final$"),
            CallbackQueryHandler(handle_payment_confirmation, pattern="^check_payment_status$")
        ],
        name="my_main_conversation",
        persistent=True
    )

    return [
        conv_handler,  # <-- Place conv_handler first so it processes states cleanly

        # Keep global fallback handlers just in case the user resets out of the conversation
        CommandHandler("start", start),
        CommandHandler("menu", reset_command),
        CommandHandler("reset", reset_command),
        MessageHandler(filters.Regex("^🏠 Main Menu / Reset$"), reset_command),
    ]

# Keep bot in memory across all requests
global_bot = None
global_loop = None

def get_bot():
    global global_bot, global_loop
    if global_bot is None:
        global_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(global_loop)

        my_persistence = PicklePersistence(filepath=os.path.join(BASE_DIR, 'bot_memory.pickle'))

        # concurrent_updates(False) blocks process_update until email finishes.
        global_bot = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).persistence(my_persistence).concurrent_updates(False).build()

        for handler in get_telegram_handlers():
            global_bot.add_handler(handler)

        global_loop.run_until_complete(global_bot.initialize())
        global_loop.run_until_complete(global_bot.start())

    return global_bot, global_loop

# ==========================================
# 4. WEB APP ROUTES
# ==========================================

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
        flash("Preview generated. Please review it before sending.", "success")
    except Exception as exc:
        logging.exception("Web preview generation failed")
        flash(str(exc))

    return redirect(url_for("web_dashboard"))


@app.route("/app/send", methods=["POST"])
@web_auth.require_active_subscription
def web_send():
    requested_draft_id = request.form.get("draft_id")
    active_draft_id = session.get("web_draft_id")
    if requested_draft_id and requested_draft_id != active_draft_id:
        flash("The staged preview changed. Please review the latest preview before sending.")
        return redirect(url_for("web_dashboard"))

    draft = draft_store.load_draft(active_draft_id)
    if not draft:
        flash("Generate a preview before sending.")
        return redirect(url_for("web_dashboard"))

    session["selected_letter_type"] = draft["letter_type"]

    try:
        sent, recipient_data = letter_service.send_letter_from_preview(draft)
        status_text = "✅ Sent" if sent else "⚠️ Failed"
        database_handler.log_activity(
            recipient_data["letter_type"],
            recipient_data["name"],
            recipient_data["email"],
            "Web App",
            status_text,
        )
        if sent:
            flash(f"Letter sent successfully to {recipient_data['name']}.", "success")
            clear_session_draft()
        else:
            flash(f"Email could not be sent to {recipient_data['name']}. Please try again.")
    except Exception as exc:
        logging.exception("Web send failed")
        flash(f"An unexpected error occurred while sending: {exc}")

    return redirect(url_for("web_dashboard"))


@app.route("/app/clear", methods=["POST"])
@web_auth.require_active_subscription
def web_clear_draft():
    selected_type = session.get("selected_letter_type")
    clear_scope = request.form.get("clear_scope", "all")
    clear_session_draft()
    if clear_scope != "preview_only":
        _clear_form_values(selected_type)
    flash("Draft cleared.")
    return redirect(url_for("web_dashboard"))


@app.route("/app/preview-image", methods=["GET"])
def web_preview_image():
    draft = draft_store.load_draft(session.get("web_draft_id"))
    if not draft:
        return ("Preview not found", 404)

    preview_path = draft.get("preview_path")
    if not preview_path or not os.path.exists(preview_path):
        return ("Preview file missing", 404)

    return send_file(preview_path, mimetype="image/png")


@app.route("/app/bulk/start", methods=["POST"])
@web_auth.require_active_subscription
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
@web_auth.require_active_subscription
def web_bulk_status(job_id):
    job = bulk_service.get_bulk_job(job_id)
    if not job:
        return jsonify({"ok": False, "error": "Bulk job not found."}), 404
    return jsonify({"ok": True, "job": job})


@app.route("/app/bulk/failed/<job_id>", methods=["GET"])
@web_auth.require_active_subscription
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


# ==========================================
# 5. FLASK WEBHOOK
# ==========================================

@app.route(f'/{SECRET}', methods=['POST'])
def webhook():
    try:
        json_update = request.get_json(force=True)
        update_id = json_update.get('update_id')

        # Instantly filters duplicate 5-second retries sent by Telegram while email processes
        if update_id in processed_updates:
            return "OK", 200
        processed_updates.append(update_id)

    except Exception as e:
        logging.error(f"Failed to decode update: {e}")
        return "OK", 200

    try:
        # Load the ALREADY AWAKE bot instance from RAM
        bot_instance, loop = get_bot()

        update = Update.de_json(json_update, bot_instance.bot)

        # Blocks and securely processes the update
        loop.run_until_complete(bot_instance.process_update(update))

        # Flushes memory to disk natively
        if bot_instance.persistence:
            loop.run_until_complete(bot_instance.persistence.flush())

    except Exception as e:
        logging.error(f"Bot execution error: {e}")

    return "OK", 200

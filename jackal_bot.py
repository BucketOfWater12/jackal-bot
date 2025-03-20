import logging
import gspread
import json
import os
import asyncio
import datetime
from flask import Flask
from google.oauth2.service_account import Credentials
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ✅ Flask App for Cloud Run Health Check
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Jackal Bot is running on Railway!"

# ✅ Load Environment Variables (from Railway)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")

# ✅ Ensure Environment Variables Exist
if not TELEGRAM_BOT_TOKEN or not GOOGLE_CREDENTIALS_JSON or not SPREADSHEET_NAME:
    raise ValueError("🚨 Missing required environment variables!")

# ✅ Connect to Google Sheets with Correct OAuth Scopes
google_credentials = json.loads(GOOGLE_CREDENTIALS_JSON)
scopes = [
    "https://www.googleapis.com/auth/spreadsheets", 
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_info(google_credentials, scopes=scopes)
client = gspread.authorize(creds)
sheet = client.open(SPREADSHEET_NAME).sheet1

# ✅ Logging Setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ✅ Function to Get Medical Status
def get_medical_status(syn_no):
    try:
        form_sheet = client.open(SPREADSHEET_NAME).worksheet("Form responses 1")
        form_data = form_sheet.get_all_records()
        today = datetime.datetime.today().date()

        for row in reversed(form_data):
            if row['SYN NO'] == syn_no:
                start_date = datetime.datetime.strptime(row['Start Date'], "%d/%m/%Y").date()
                end_date = datetime.datetime.strptime(row['End Date'], "%d/%m/%Y").date()

                if start_date <= today <= end_date:
                    return f"STATUS: {row['Medical Status']} ({row['Start Date']} - {row['End Date']})"
        return None
    except Exception as e:
        logger.error(f"Error fetching medical status: {e}")
        return None

# ✅ Telegram Bot Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Welcome to Jackal Medical Bot! Use /help for commands.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Commands:\n"
        "/search SYN_NO - Get user details\n"
        "/pes PES_CODE - List users by PES\n"
        "/all - Show all personnel\n"
        "/update - Update Medical Status"
    )

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /search SYN_NO")
        return

    syn_no = context.args[0].upper()
    data = sheet.get_all_records()
    user_details = None

    for row in data:
        if row['SYN NO'] == syn_no:
            user_details = f"{row['RANK']} {row['NAME']}\nPES: {row['PES']}"
            break

    if not user_details:
        await update.message.reply_text("SYN NO not found.")
        return

    latest_status = get_medical_status(syn_no)
    response = user_details
    if latest_status:
        response += f"\n{latest_status}"

    await update.message.reply_text(response)

async def search_pes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Usage: /pes PES_CODE")
        return

    pes_code = context.args[0].upper()
    data = sheet.get_all_records()
    response = ""

    for row in data:
        if row['PES'] == pes_code:
            syn_no = row['SYN NO']
            status = get_medical_status(syn_no)
            response += f"{row['RANK']} {row['NAME']}\nPES: {row['PES']}"
            if status:
                response += f"\n{status}"
            response += "\n\n"

    await update.message.reply_text(response if response else "No personnel found with this PES status.")

async def show_all(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    data = sheet.get_all_records()
    response = ""

    for row in data:
        syn_no = row['SYN NO']
        status = get_medical_status(syn_no)
        response += f"{row['RANK']} {row['NAME']}\nPES: {row['PES']}"
        if status:
            response += f"\n{status}"
        response += "\n\n"

    await update.message.reply_text(response)

async def update_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "To update Medical Status, please use this form:\n"
        "https://docs.google.com/forms/d/e/1FAIpQLSeb1nvty2OuR4WXp8MNsR4SuBs1vhQ1Nyx0n_b8Dmaaj53AZQ/viewform?usp=dialog"
    )

# ✅ Start Telegram Bot
async def start_telegram_bot():
    bot_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_command))
    bot_app.add_handler(CommandHandler("search", search_user))
    bot_app.add_handler(CommandHandler("pes", search_pes))
    bot_app.add_handler(CommandHandler("update", update_status))

    print("✅ Jackal Medical Bot is running on Railway!")
    await bot_app.run_polling()

# ✅ Start Everything (Flask as Main Process)
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    
    # ✅ Ensure event loop is running properly
    if loop.is_running():
        asyncio.ensure_future(start_telegram_bot())
    else:
        loop.run_until_complete(start_telegram_bot())

    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

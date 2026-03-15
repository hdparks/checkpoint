"""Entry point for running the Telegram bot."""
import os
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.bot import (
    handle_callback,
    handle_message,
    interval_command,
    myid_command,
    mood_command,
    ping_command,
    ping_off_command,
    ping_on_command,
    pinghours_command,
    settings_command,
    skip_command,
    start_command,
    stats_command,
    timezone_command,
    tzlist_command,
)
from app.scheduler import ping_users

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if not TOKEN or TOKEN == "your_bot_token_here":
    print("ERROR: Please set TELEGRAM_BOT_TOKEN in .env file")
    print("Copy .env.example to .env and add your bot token")
    sys.exit(1)

scheduler = AsyncIOScheduler()


def run_bot():
    """Initialize and run the bot with all handlers and scheduler."""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("mood", mood_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("ping_on", ping_on_command))
    application.add_handler(CommandHandler("ping_off", ping_off_command))
    application.add_handler(CommandHandler("interval", interval_command))
    application.add_handler(CommandHandler("pinghours", pinghours_command))
    application.add_handler(CommandHandler("timezone", timezone_command))
    application.add_handler(CommandHandler("tzlist", tzlist_command))
    application.add_handler(CommandHandler("skip", skip_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    scheduler.add_job(
        ping_users,
        IntervalTrigger(minutes=10),
        args=(application.bot,),
        id="ping_job",
        replace_existing=True
    )
    scheduler.start()
    print("Scheduler started!")

    application.run_polling()


if __name__ == "__main__":
    print("Starting Checkpoint Bot...")
    run_bot()

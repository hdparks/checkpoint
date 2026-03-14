import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from dotenv import load_dotenv
from app.scheduler import ping_users

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
if not TOKEN or TOKEN == "your_bot_token_here":
    print("ERROR: Please set TELEGRAM_BOT_TOKEN in .env file")
    print("Copy .env.example to .env and add your bot token")
    exit(1)

from app.bot import (
    start_command,
    ping_command,
    mood_command,
    handle_callback,
    handle_message,
    stats_command,
    settings_command,
    ping_on_command,
    ping_off_command,
    interval_command,
    skip_command,
)

scheduler = AsyncIOScheduler()


def run_bot():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("mood", mood_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("ping_on", ping_on_command))
    application.add_handler(CommandHandler("ping_off", ping_off_command))
    application.add_handler(CommandHandler("interval", interval_command))
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

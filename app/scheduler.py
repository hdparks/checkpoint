import random
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.database import SessionLocal, Settings, get_or_create_settings

MOOD_EMOJIS = {1: "😢", 2: "😕", 3: "😐", 4: "🙂", 5: "😄"}

scheduler = AsyncIOScheduler()
bot_instance = None


def set_bot(bot):
    global bot_instance
    bot_instance = bot


async def ping_random_user():
    db = SessionLocal()
    try:
        settings_list = db.query(Settings).filter(Settings.ping_enabled == True).all()
        if not settings_list:
            return
        
        now = datetime.utcnow()
        current_hour = now.hour
        
        for settings in settings_list:
            if not settings.ping_enabled:
                continue
            
            if settings.ping_start_hour is not None and settings.ping_end_hour is not None:
                if not (settings.ping_start_hour <= current_hour < settings.ping_end_hour):
                    continue
            
            if settings.last_ping:
                hours_since_last = (now - settings.last_ping).total_seconds() / 3600
                if hours_since_last < settings.min_interval_hours:
                    continue
            
            interval = random.randint(settings.min_interval_hours, settings.max_interval_hours)
            if not settings.last_ping or (now - settings.last_ping).total_seconds() / 3600 >= interval:
                if bot_instance:
                    try:
                        keyboard = [
                            [InlineKeyboardButton(f"{MOOD_EMOJIS[i]} {i}", callback_data=f"mood_{i}") for i in range(1, 6)]
                        ]
                        await bot_instance.send_message(
                            chat_id=settings.telegram_id,
                            text="How are you feeling?",
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                        settings.last_ping = now
                        db.commit()
                    except Exception as e:
                        print(f"Failed to ping user {settings.telegram_id}: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(ping_random_user, IntervalTrigger(minutes=10), id="ping_job", replace_existing=True)
    scheduler.start()
    print("Scheduler started!")

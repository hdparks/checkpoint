import os
import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.database import SessionLocal, Settings

MOOD_EMOJIS = {1: "😢", 2: "😕", 3: "😐", 4: "🙂", 5: "😄"}


async def ping_users(bot):
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
                try:
                    keyboard = [
                        [InlineKeyboardButton(f"{MOOD_EMOJIS[i]} {i}", callback_data=f"mood_{i}") for i in range(1, 6)]
                    ]
                    await bot.send_message(
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

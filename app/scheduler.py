import os
import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from app.database import SessionLocal, Settings

MOOD_EMOJIS = {1: "😢", 2: "😕", 3: "😐", 4: "🙂", 5: "😄"}


async def ping_users(bot):
    db = SessionLocal()
    try:
        settings_list = db.execute(select(Settings).where(Settings.ping_enabled == True)).scalars().all()
        if not settings_list:
            return
        
        now = datetime.utcnow()
        utc_hour = now.hour
        
        for settings in settings_list:
            if not settings.ping_enabled:
                continue
            
            local_hour = (utc_hour + settings.timezone_offset) % 24
            
            if settings.ping_start_hour is not None and settings.ping_end_hour is not None:
                start = settings.ping_start_hour
                end = settings.ping_end_hour
                
                if start <= end:
                    if not (start <= local_hour < end):
                        continue
                else:
                    if not (local_hour >= start or local_hour < end):
                        continue
            
            if settings.last_ping:
                minutes_since_last = (now - settings.last_ping).total_seconds() / 60
                if minutes_since_last < settings.min_interval_minutes:
                    continue
            
            interval = random.randint(settings.min_interval_minutes, settings.max_interval_minutes)
            if not settings.last_ping or (now - settings.last_ping).total_seconds() / 60 >= interval:
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

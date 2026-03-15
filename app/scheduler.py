"""Scheduler for sending periodic mood check-in prompts to users."""
import random
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from sqlalchemy import select
from app.database import SESSION_LOCAL, Settings

MOOD_EMOJIS = {1: "😢", 2: "😕", 3: "😐", 4: "🙂", 5: "😄"}


async def ping_users(bot):
    """Send mood check-in prompts to enabled users at random intervals."""
    db = SESSION_LOCAL()
    try:
        settings_list = db.execute(select(Settings).where(Settings.ping_enabled)).scalars().all()
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
                    if start > local_hour or local_hour >= end:
                        continue
                else:
                    # Overnight: skip if outside [start, 24) U [0, end)
                    if local_hour < start and local_hour >= end:  # noqa: R1716
                        continue

            if settings.last_ping:
                minutes_since_last = (now - settings.last_ping).total_seconds() / 60
                if minutes_since_last < settings.min_interval_minutes:
                    continue

            interval = random.randint(
                settings.min_interval_minutes,
                settings.max_interval_minutes
            )
            elapsed = (now - settings.last_ping).total_seconds() / 60
            if not settings.last_ping or elapsed >= interval:
                try:
                    keyboard = [
                        [InlineKeyboardButton(f"{MOOD_EMOJIS[i]} {i}", callback_data=f"mood_{i}")
                         for i in range(1, 6)]
                    ]
                    await bot.send_message(
                        chat_id=settings.telegram_id,
                        text="How are you feeling?",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    settings.last_ping = now
                    db.commit()
                except TelegramError:
                    print(f"Failed to ping user {settings.telegram_id}")
    finally:
        db.close()

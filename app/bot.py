"""Telegram bot for daily mood check-ins."""
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from sqlalchemy import select
from app.database import Entry, get_or_create_settings, SESSION_LOCAL

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

MOOD_EMOJIS = {1: "😢", 2: "😕", 3: "😐", 4: "🙂", 5: "😄"}
MOOD_OPTIONS = [
    [InlineKeyboardButton(f"{MOOD_EMOJIS[i]} {i}", callback_data=f"mood_{i}") for i in range(1, 6)]
]
SKIP_OPTIONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("Skip note", callback_data="skip_note")]
])


async def start_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show welcome message and available commands."""
    db = SESSION_LOCAL()
    try:
        get_or_create_settings(db, update.effective_user.id)
        await update.message.reply_text(
            "👋 Hi! I'm your daily check-in bot.\n\n"
            "I'll ping you randomly throughout the day to ask how you're feeling.\n\n"
            "Commands:\n"
            "/ping - Trigger a manual check-in\n"
            "/mood - Log your mood now\n"
            "/stats - View your check-in statistics\n"
            "/settings - Configure ping schedule\n"
            "/pinghours [start] [end] - Set ping hours (local time)\n"
            "/timezone [offset] - Set your UTC offset\n"
            "/tzlist - View common timezone offsets\n"
            "/stop - Stop receiving pings\n"
            "/start - Resume pings"
        )
    finally:
        db.close()


async def ping_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping command - trigger manual check-in."""
    db = SESSION_LOCAL()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.last_ping = datetime.utcnow()
        db.commit()
    finally:
        db.close()
    await send_mood_prompt(update.effective_user.id)


async def send_mood_prompt(telegram_id, bot=None):
    """Send mood selection keyboard to a user."""
    keyboard = InlineKeyboardMarkup(MOOD_OPTIONS)
    message = "How are you feeling right now?"
    if bot:
        await bot.send_message(chat_id=telegram_id, text=message, reply_markup=keyboard)
    return message, keyboard


async def mood_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /mood command - show mood selection keyboard."""
    db = SESSION_LOCAL()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.last_ping = datetime.utcnow()
        db.commit()
    finally:
        db.close()
    keyboard = InlineKeyboardMarkup(MOOD_OPTIONS)
    await update.message.reply_text("How are you feeling?", reply_markup=keyboard)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline callback queries from button presses."""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("mood_"):
        mood = int(query.data.split("_")[1])
        text = f"You selected: {MOOD_EMOJIS[mood]} {mood}/5"
        await query.message.edit_text(text, reply_markup=SKIP_OPTIONS)

        db = SESSION_LOCAL()
        try:
            entry = Entry(telegram_id=update.effective_user.id, mood=mood)
            db.add(entry)

            settings = get_or_create_settings(db, update.effective_user.id)
            settings.last_ping = datetime.utcnow()

            db.commit()
            db.refresh(entry)

            context.user_data["pending_mood"] = mood
            context.user_data["pending_entry_id"] = entry.id
        finally:
            db.close()
        return

    if query.data == "skip_note":
        entry_id = context.user_data.get("pending_entry_id")
        if entry_id:
            db = SESSION_LOCAL()
            try:
                entry = db.execute(select(Entry).where(Entry.id == entry_id)).scalars().first()
                if entry:
                    text = f"Logged: {MOOD_EMOJIS[entry.mood]} {entry.mood}/5"
                    await query.message.edit_text(text)
            finally:
                db.close()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages for pending mood notes."""
    if "pending_mood" in context.user_data:
        db = SESSION_LOCAL()
        try:
            entry_id = context.user_data.get("pending_entry_id")
            if entry_id:
                entry = db.execute(select(Entry).where(Entry.id == entry_id)).scalars().first()
                if entry:
                    entry.note = update.message.text
                    db.commit()
                    await update.message.reply_text(
                        f"Logged: {MOOD_EMOJIS[entry.mood]} {entry.mood}/5\n"
                        f"Note: {entry.note}"
                    )
            context.user_data.clear()
        finally:
            db.close()
    elif update.message.text == "/skip":
        pass


async def stats_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show user's check-in statistics."""
    db = SESSION_LOCAL()
    try:
        user_id = update.effective_user.id
        entries = db.execute(select(Entry).where(Entry.telegram_id == user_id)).scalars().all()
        if not entries:
            await update.message.reply_text("No entries yet. Use /mood to log your first mood!")
            return

        total = len(entries)
        avg_mood = sum(e.mood for e in entries) / total
        today = datetime.utcnow().date()
        today_entries = [e for e in entries if e.created_at.date() == today]

        streak = 0
        check_date = today
        while True:
            if any(e.created_at.date() == check_date for e in entries):
                streak += 1
                check_date -= timedelta(days=1)
            else:
                break

        await update.message.reply_text(
            f"📊 Your Stats\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Total check-ins: {total}\n"
            f"Average mood: {avg_mood:.1f}/5\n"
            f"Today's check-ins: {len(today_entries)}\n"
            f"Current streak: {streak} day(s)"
        )
    finally:
        db.close()


async def settings_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command - show current settings and change commands."""
    db = SESSION_LOCAL()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)

        status = "ON 🟢" if settings.ping_enabled else "OFF 🔴"
        if settings.ping_start_hour is not None:
            ping_hours = f"{settings.ping_start_hour}:00 - {settings.ping_end_hour}:00"
        else:
            ping_hours = "Not set"
        tz_info = f"UTC{settings.timezone_offset:+d}" if settings.timezone_offset != 0 else "UTC"

        await update.message.reply_text(
            f"⚙️ Settings\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Pings: {status}\n"
            f"Random interval: "
            f"{settings.min_interval_minutes}-{settings.max_interval_minutes} minutes\n"
            f"Ping hours (local): {ping_hours}\n"
            f"Timezone: {tz_info}\n\n"
            f"Commands to change:\n"
            f"/ping_on - Enable pings\n"
            f"/ping_off - Disable pings\n"
            f"/interval [min] [max] - Set interval range\n"
            f"/pinghours [start] [end] - Set ping hours (0-23)\n"
            f"/timezone [offset] - Set UTC offset (e.g., -5, 0, 8)"
        )
    finally:
        db.close()


async def ping_on_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping_on command - enable scheduled pings."""
    db = SESSION_LOCAL()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.ping_enabled = True
        db.commit()
        await update.message.reply_text("✅ Pings enabled!")
    finally:
        db.close()


async def ping_off_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping_off command - disable scheduled pings."""
    db = SESSION_LOCAL()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.ping_enabled = False
        db.commit()
        await update.message.reply_text("✅ Pings disabled!")
    finally:
        db.close()


async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /interval command - set ping interval range."""
    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /interval [min_minutes] [max_minutes]\nExample: /interval 30 60"
        )
        return

    try:
        min_h = int(context.args[0])
        max_h = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Please enter valid numbers.")
        return

    db = SESSION_LOCAL()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.min_interval_minutes = min_h
        settings.max_interval_minutes = max_h
        db.commit()
        await update.message.reply_text(f"✅ Interval set to {min_h}-{max_h} minutes!")
    finally:
        db.close()


async def pinghours_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pinghours command - set allowed hours for pings."""
    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /pinghours [start_hour] [end_hour]\n"
            "Example: /pinghours 9 17\n"
            "Use 22 6 for overnight (10pm-6am)"
        )
        return

    try:
        start_h = int(context.args[0])
        end_h = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Please enter valid hours (0-23).")
        return

    if not (0 <= start_h <= 23 and 0 <= end_h <= 23):
        await update.message.reply_text("Hours must be between 0 and 23.")
        return

    db = SESSION_LOCAL()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.ping_start_hour = start_h
        settings.ping_end_hour = end_h
        db.commit()

        if start_h <= end_h:
            range_desc = f"{start_h}:00 - {end_h}:00"
        else:
            range_desc = f"{start_h}:00 - {end_h}:00 (overnight)"
        await update.message.reply_text(f"✅ Ping hours set to {range_desc} (your local time)")
    finally:
        db.close()


async def timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /timezone command - set UTC offset for user."""
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /timezone [offset]\n"
            "Example: /timezone -5 for EST\n"
            "/tzlist to see available offsets"
        )
        return

    try:
        offset = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Please enter a valid integer (e.g., -5, 0, 8).")
        return

    if offset < -12 or offset > 14:
        await update.message.reply_text("Offset must be between -12 and +14.")
        return

    db = SESSION_LOCAL()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.timezone_offset = offset
        db.commit()
        await update.message.reply_text(f"✅ Timezone set to UTC{offset:+d}!")
    finally:
        db.close()


async def tzlist_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /tzlist command - show common UTC timezone offsets."""
    common_offsets = [
        (-12, "-12 (Baker Island)"),
        (-11, "-11 (American Samoa)"),
        (-10, "-10 (Hawaii)"),
        (-9, "-9 (Alaska)"),
        (-8, "-8 (Pacific)"),
        (-7, "-7 (Mountain)"),
        (-6, "-6 (Central)"),
        (-5, "-5 (Eastern)"),
        (-4, "-4 (Atlantic)"),
        (-3, "-3 (Brasilia)"),
        (-2, "-2 (Mid-Atlantic)"),
        (-1, "-1 (Azores)"),
        (0, "0 (UTC/London)"),
        (1, "+1 (Paris/Berlin)"),
        (2, "+2 (Cairo/Athens)"),
        (3, "+3 (Moscow/Dubai)"),
        (4, "+4 (Dubai)"),
        (5, "+5 (Pakistan)"),
        (6, "+6 (Bangladesh)"),
        (7, "+7 (Bangkok/Jakarta)"),
        (8, "+8 (Beijing/Singapore)"),
        (9, "+9 (Tokyo/Seoul)"),
        (10, "+10 (Sydney)"),
        (11, "+11 (Noumea)"),
        (12, "+12 (Fiji)"),
        (13, "+13 (Nuku'alofa)"),
        (14, "+14 (Kiritimati)"),
    ]
    msg = "🌍 Common UTC offsets:\n━━━━━━━━━━━━━━━━\n"
    for offset, name in common_offsets:
        msg += f"UTC{offset:+d}: {name}\n"
    await update.message.reply_text(msg)


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /skip command - skip pending note entry."""
    if "pending_entry_id" in context.user_data:
        context.user_data.clear()
        await update.message.reply_text("Note skipped!")
    else:
        await update.message.reply_text("No pending note to skip.")


async def myid_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Handle /myid command - show user's Telegram ID."""
    await update.message.reply_text(f"Your Telegram ID: {update.effective_user.id}")


def run_bot(application):
    """Register all command and message handlers with the application."""
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

    application.run_polling()

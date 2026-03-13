import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from app.database import Entry, Settings, get_db, get_or_create_settings, SessionLocal

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

MOOD_EMOJIS = {1: "😢", 2: "😕", 3: "😐", 4: "🙂", 5: "😄"}
MOOD_OPTIONS = [
    [InlineKeyboardButton(f"{MOOD_EMOJIS[i]} {i}", callback_data=f"mood_{i}") for i in range(1, 6)]
]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
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
            "/stop - Stop receiving pings\n"
            "/start - Resume pings"
        )
    finally:
        db.close()


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_mood_prompt(update.effective_user.id)


async def send_mood_prompt(telegram_id, bot=None):
    keyboard = InlineKeyboardMarkup(MOOD_OPTIONS)
    message = "How are you feeling right now?"
    if bot:
        await bot.send_message(chat_id=telegram_id, text=message, reply_markup=keyboard)
    return message, keyboard


async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup(MOOD_OPTIONS)
    await update.message.reply_text("How are you feeling?", reply_markup=keyboard)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("mood_"):
        mood = int(query.data.split("_")[1])
        await query.message.edit_text(f"You selected: {MOOD_EMOJIS[mood]} {mood}/5")
        await query.message.reply_text("Add a note? (or skip with /skip)")
        
        db = SessionLocal()
        try:
            entry = Entry(telegram_id=update.effective_user.id, mood=mood)
            db.add(entry)
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
            db = SessionLocal()
            try:
                entry = db.query(Entry).filter(Entry.id == entry_id).first()
                if entry:
                    await query.message.edit_text(f"Logged: {MOOD_EMOJIS[entry.mood]} {entry.mood}/5")
            finally:
                db.close()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "pending_mood" in context.user_data:
        db = SessionLocal()
        try:
            entry_id = context.user_data.get("pending_entry_id")
            if entry_id:
                entry = db.query(Entry).filter(Entry.id == entry_id).first()
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


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        entries = db.query(Entry).filter(Entry.telegram_id == update.effective_user.id).all()
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


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        
        status = "ON 🟢" if settings.ping_enabled else "OFF 🔴"
        await update.message.reply_text(
            f"⚙️ Settings\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"Pings: {status}\n"
            f"Random interval: {settings.min_interval_hours}-{settings.max_interval_hours} hours\n\n"
            f"Commands to change:\n"
            f"/ping_on - Enable pings\n"
            f"/ping_off - Disable pings\n"
            f"/interval [min] [max] - Set interval range"
        )
    finally:
        db.close()


async def ping_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.ping_enabled = True
        db.commit()
        await update.message.reply_text("✅ Pings enabled!")
    finally:
        db.close()


async def ping_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.ping_enabled = False
        db.commit()
        await update.message.reply_text("✅ Pings disabled!")
    finally:
        db.close()


async def interval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /interval [min_hours] [max_hours]\nExample: /interval 1 3")
        return
    
    try:
        min_h = int(context.args[0])
        max_h = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Please enter valid numbers.")
        return
    
    db = SessionLocal()
    try:
        settings = get_or_create_settings(db, update.effective_user.id)
        settings.min_interval_hours = min_h
        settings.max_interval_hours = max_h
        db.commit()
        await update.message.reply_text(f"✅ Interval set to {min_h}-{max_h} hours!")
    finally:
        db.close()


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "pending_entry_id" in context.user_data:
        context.user_data.clear()
        await update.message.reply_text("Note skipped!")
    else:
        await update.message.reply_text("No pending note to skip.")


def run_bot(application):
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
    
    application.run_polling()

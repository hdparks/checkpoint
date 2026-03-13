import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
load_dotenv()
# Replace with your actual API token obtained from BotFather
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Define command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("hey, I got a start message! :D")
    await update.message.reply_text("Hi! I am a simple echo bot.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Echo the user message."""
    print("hey, I got a text message! :D Echo! Echo!")
    await update.message.reply_text(update.message.text)

def main():
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()

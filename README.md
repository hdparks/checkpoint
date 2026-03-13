# Checkpoint - Daily Mood Tracker

A Telegram bot that pings you randomly throughout the day to track your mood, with a web dashboard for viewing your data.

## Features

- **Telegram Bot**: Receive random mood check-ins and log your feelings
- **Mood Tracking**: Rate your mood 1-5 with optional notes
- **Random Pings**: Get prompted at random intervals (configurable)
- **Web Dashboard**: View stats, charts, and manage settings

## Prerequisites

- Python 3.12+
- Telegram account

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and start @BotFather
2. Send `/newbot` and follow the instructions
3. Copy your bot token

### 2. Configure the App

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your bot token
nano .env
```

### 3. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run the App

```bash
python run.py
```

The app will start:
- Web interface: http://localhost:8000
- Telegram bot: Your bot on Telegram

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Register and get started |
| `/ping` | Trigger a manual check-in |
| `/mood` | Log your mood now |
| `/stats` | View your statistics |
| `/settings` | Configure ping schedule |
| `/ping_on` | Enable random pings |
| `/ping_off` | Disable random pings |
| `/interval <min> <max>` | Set ping interval (e.g., `/interval 1 3`) |

## Web Dashboard

Access at http://localhost:8000 to see:
- Total check-ins and average mood
- Current streak
- Mood trend chart
- Recent entries list
- Settings configuration

## Project Structure

```
/checkpoint
├── run.py              # Main entry point
├── app/
│   ├── database.py     # SQLite models
│   ├── main.py         # FastAPI server
│   ├── scheduler.py    # Random ping logic
│   └── static/
│       └── index.html  # Web UI
├── .env                # Configuration
├── .env.example        # Config template
└── requirements.txt    # Python dependencies
```

## Development

```bash
# Run in development mode with auto-reload
source .venv/bin/activate
uvicorn app.main:app --reload
```

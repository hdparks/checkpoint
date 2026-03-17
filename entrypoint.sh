#!/bin/bash
set -e

echo "Starting Checkpoint..."

# Run database migrations
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"

# Start both processes in background
echo "Starting web server..."
python run_web.py &
WEB_PID=$!

echo "Starting bot..."
python run_bot.py &
BOT_PID=$!

# Wait for either to exit
wait -n
EXIT_CODE=$?

echo "Process exited with code $EXIT_CODE, killing other process..."
kill $WEB_PID 2>/dev/null || true
kill $BOT_PID 2>/dev/null || true

exit $EXIT_CODE

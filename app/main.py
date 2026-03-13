import os
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db, Entry, Settings, get_or_create_settings

app = FastAPI(title="Checkpoint")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/static")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    entries = db.query(Entry).order_by(Entry.created_at.desc()).limit(50).all()
    total_entries = db.query(Entry).count()
    avg_mood = db.query(Entry).all()
    avg_mood = sum(e.mood for e in avg_mood) / len(avg_mood) if avg_mood else 0
    
    today = datetime.utcnow().date()
    today_count = db.query(Entry).filter(Entry.created_at >= datetime.combine(today, datetime.min.time())).count()
    
    settings = db.query(Settings).first()
    
    entries_json = [
        {
            "id": e.id,
            "mood": e.mood,
            "note": e.note or "",
            "created_at": e.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for e in entries
    ]
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "entries": entries_json,
        "total_entries": total_entries,
        "avg_mood": round(avg_mood, 1),
        "today_count": today_count,
        "settings": settings,
        "bot_token": BOT_TOKEN
    })


@app.get("/api/entries")
async def api_entries(db: Session = Depends(get_db)):
    entries = db.query(Entry).order_by(Entry.created_at.desc()).limit(100).all()
    return [
        {
            "id": e.id,
            "mood": e.mood,
            "note": e.note,
            "created_at": e.created_at.isoformat()
        }
        for e in entries
    ]


@app.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    entries = db.query(Entry).all()
    if not entries:
        return {"total": 0, "avg_mood": 0, "today": 0, "streak": 0}
    
    total = len(entries)
    avg_mood = sum(e.mood for e in entries) / total
    
    today = datetime.utcnow().date()
    today_count = len([e for e in entries if e.created_at.date() == today])
    
    streak = 0
    check_date = today
    while True:
        if any(e.created_at.date() == check_date for e in entries):
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    
    return {"total": total, "avg_mood": round(avg_mood, 1), "today": today_count, "streak": streak}


@app.get("/api/settings")
async def api_settings(db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        return {"ping_enabled": True, "min_interval_hours": 1, "max_interval_hours": 3, "ping_start_hour": None, "ping_end_hour": None}
    return {
        "ping_enabled": settings.ping_enabled,
        "min_interval_hours": settings.min_interval_hours,
        "max_interval_hours": settings.max_interval_hours,
        "ping_start_hour": settings.ping_start_hour,
        "ping_end_hour": settings.ping_end_hour
    }


@app.post("/api/settings")
async def update_settings(data: dict, db: Session = Depends(get_db)):
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(telegram_id=0)
        db.add(settings)
    
    if "ping_enabled" in data:
        settings.ping_enabled = data["ping_enabled"]
    if "min_interval_hours" in data:
        settings.min_interval_hours = data["min_interval_hours"]
    if "max_interval_hours" in data:
        settings.max_interval_hours = data["max_interval_hours"]
    if "ping_start_hour" in data:
        settings.ping_start_hour = data["ping_start_hour"]
    if "ping_end_hour" in data:
        settings.ping_end_hour = data["ping_end_hour"]
    
    db.commit()
    return {"success": True}


@app.post("/api/entries")
async def create_entry(data: dict, db: Session = Depends(get_db)):
    entry = Entry(
        telegram_id=data.get("telegram_id", 0),
        mood=data.get("mood"),
        note=data.get("note")
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "mood": entry.mood, "note": entry.note, "created_at": entry.created_at.isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

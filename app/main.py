import os
import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.database import get_db, Entry, Settings, get_or_create_settings

app = FastAPI(title="Checkpoint")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/static")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    entries = db.execute(select(Entry).order_by(Entry.created_at.desc()).limit(50)).scalars().all()
    total_entries = db.execute(select(func.count(Entry.id))).scalar()
    avg_mood = db.execute(select(Entry)).scalars().all()
    avg_mood = sum(float(e.mood) for e in avg_mood) / len(avg_mood) if avg_mood else 0.0
    
    today = datetime.utcnow().date()
    today_count = db.execute(select(func.count(Entry.id)).where(Entry.created_at >= datetime.combine(today, datetime.min.time()))).scalar()
    
    settings = db.execute(select(Settings)).scalars().first()
    
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
        "avg_mood": round(float(avg_mood), 1),
        "today_count": today_count,
        "settings": settings,
        "bot_token": BOT_TOKEN
    })


@app.get("/api/entries")
async def api_entries(telegram_id: int = 0, db: Session = Depends(get_db)):
    query = select(Entry)
    if telegram_id:
        query = query.where(Entry.telegram_id == telegram_id)
    entries = db.execute(query.order_by(Entry.created_at.desc()).limit(100)).scalars().all()
    return [
        {
            "id": e.id,
            "mood": e.mood,
            "note": e.note,
            "created_at": e.created_at.isoformat()
        }
        for e in entries
    ]


@app.get("/api/users")
async def api_users(db: Session = Depends(get_db)):
    entries = db.execute(select(Entry)).scalars().all()
    users = {}
    for e in entries:
        if e.telegram_id not in users:
            users[e.telegram_id] = {"telegram_id": e.telegram_id, "entry_count": 0, "last_entry": None}
        users[e.telegram_id]["entry_count"] += 1
        if users[e.telegram_id]["last_entry"] is None or e.created_at > users[e.telegram_id]["last_entry"]:
            users[e.telegram_id]["last_entry"] = e.created_at
    
    for user in users.values():
        user["last_entry"] = user["last_entry"].isoformat() if user["last_entry"] else None
    
    user_list = sorted(users.values(), key=lambda x: x["last_entry"] or "", reverse=True)
    return user_list


@app.get("/api/stats")
async def api_stats(telegram_id: int = 0, db: Session = Depends(get_db)):
    query = select(Entry)
    if telegram_id:
        query = query.where(Entry.telegram_id == telegram_id)
    entries = db.execute(query).scalars().all()
    if not entries:
        return {"total": 0, "avg_mood": 0, "today": 0, "streak": 0}
    
    total = len(entries)
    avg_mood = sum(float(e.mood) for e in entries) / total
    
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


@app.get("/api/stats/distribution")
async def api_stats_distribution(telegram_id: int = 0, db: Session = Depends(get_db)):
    query = select(Entry)
    if telegram_id:
        query = query.where(Entry.telegram_id == telegram_id)
    entries = db.execute(query).scalars().all()
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for e in entries:
        mood_val = int(e.mood)
        if mood_val in distribution:
            distribution[mood_val] += 1
    return distribution


@app.get("/api/stats/insights")
async def api_stats_insights(telegram_id: int = 0, db: Session = Depends(get_db)):
    query = select(Entry)
    if telegram_id:
        query = query.where(Entry.telegram_id == telegram_id)
    entries = db.execute(query).scalars().all()
    if not entries:
        return {"best_day": None, "worst_day": None, "avg_by_day": {}}
    
    day_totals = {i: [] for i in range(7)}
    for e in entries:
        day_of_week = e.created_at.weekday()
        day_totals[day_of_week].append(e.mood)
    
    avg_by_day = {}
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for day, moods in day_totals.items():
        if moods:
            avg_by_day[day_names[day]] = round(sum(moods) / len(moods), 1)
    
    best_day = max(avg_by_day.items(), key=lambda x: x[1])[0] if avg_by_day else None
    worst_day = min(avg_by_day.items(), key=lambda x: x[1])[0] if avg_by_day else None
    
    return {"best_day": best_day, "worst_day": worst_day, "avg_by_day": avg_by_day}


@app.get("/api/settings")
async def api_settings(telegram_id: int = 0, db: Session = Depends(get_db)):
    settings = db.execute(select(Settings).where(Settings.telegram_id == telegram_id)).scalars().first()
    if not settings:
        return {
            "ping_enabled": True,
            "min_interval_minutes": 30,
            "max_interval_minutes": 120,
            "ping_start_hour": None,
            "ping_end_hour": None,
            "timezone_offset": 0
        }
    return {
        "ping_enabled": settings.ping_enabled,
        "min_interval_minutes": settings.min_interval_minutes,
        "max_interval_minutes": settings.max_interval_minutes,
        "ping_start_hour": settings.ping_start_hour,
        "ping_end_hour": settings.ping_end_hour,
        "timezone_offset": settings.timezone_offset
    }


@app.post("/api/settings")
async def update_settings(data: dict, db: Session = Depends(get_db)):
    telegram_id = data.get("telegram_id", 0)
    
    settings = db.execute(select(Settings).where(Settings.telegram_id == telegram_id)).scalars().first()
    if not settings:
        settings = Settings(telegram_id=telegram_id)
        db.add(settings)
    
    if "ping_enabled" in data:
        settings.ping_enabled = data["ping_enabled"]
    if "min_interval_minutes" in data:
        settings.min_interval_minutes = data["min_interval_minutes"]
    if "max_interval_minutes" in data:
        settings.max_interval_minutes = data["max_interval_minutes"]
    if "ping_start_hour" in data:
        settings.ping_start_hour = data["ping_start_hour"]
    if "ping_end_hour" in data:
        settings.ping_end_hour = data["ping_end_hour"]
    if "timezone_offset" in data:
        settings.timezone_offset = data["timezone_offset"]
    
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


@app.delete("/api/entries/{entry_id}")
async def delete_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.execute(select(Entry).where(Entry.id == entry_id)).scalars().first()
    if entry:
        db.delete(entry)
        db.commit()
        return {"success": True}
    return {"success": False, "error": "Entry not found"}


@app.get("/api/export")
async def api_export(db: Session = Depends(get_db)):
    entries = db.execute(select(Entry).order_by(Entry.created_at.desc())).scalars().all()
    return [
        {
            "id": e.id,
            "mood": e.mood,
            "note": e.note,
            "created_at": e.created_at.isoformat()
        }
        for e in entries
    ]


@app.get("/api/export/csv")
async def api_export_csv(db: Session = Depends(get_db)):
    entries = db.execute(select(Entry).order_by(Entry.created_at.desc())).scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "mood", "note", "created_at"])
    for e in entries:
        writer.writerow([e.id, e.mood, e.note or "", e.created_at.isoformat()])
    
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mood_data.csv"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

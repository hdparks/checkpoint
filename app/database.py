from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

engine = create_engine("sqlite:///checkpoint.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Entry(Base):
    __tablename__ = "entries"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, nullable=False)
    mood = Column(Integer, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    ping_enabled = Column(Boolean, default=True)
    min_interval_hours = Column(Integer, default=1)
    max_interval_hours = Column(Integer, default=3)
    ping_start_hour = Column(Integer, nullable=True)
    ping_end_hour = Column(Integer, nullable=True)
    last_ping = Column(DateTime, nullable=True)


Base.metadata.create_all(bind=engine)

from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE settings ADD COLUMN ping_start_hour INTEGER"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE settings ADD COLUMN ping_end_hour INTEGER"))
        conn.commit()
    except Exception:
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_settings(db, telegram_id):
    settings = db.query(Settings).filter(Settings.telegram_id == telegram_id).first()
    if not settings:
        settings = Settings(telegram_id=telegram_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

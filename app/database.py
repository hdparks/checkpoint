"""Database models and session management."""
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Integer, String, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker


class Base(DeclarativeBase):
    """Base class for all database models."""

engine = create_engine("sqlite:///checkpoint.db")
SESSION_LOCAL = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Entry(Base):  # pylint: disable=too-few-public-methods
    """Database model for mood check-in entries."""
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(Integer, nullable=False)
    mood: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Settings(Base):  # pylint: disable=too-few-public-methods
    """Database model for user settings."""
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    ping_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    min_interval_minutes: Mapped[int] = mapped_column(Integer, default=30)
    max_interval_minutes: Mapped[int] = mapped_column(Integer, default=120)
    ping_start_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ping_end_hour: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    timezone_offset: Mapped[int] = mapped_column(Integer, default=0)
    last_ping: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


Base.metadata.create_all(bind=engine)


def get_db():
    """Yield database session for dependency injection."""
    db = SESSION_LOCAL()
    try:
        yield db
    finally:
        db.close()


def get_or_create_settings(db: Session, telegram_id: int) -> Settings:
    """Get existing settings or create new ones for a user."""
    settings = db.query(Settings).filter(Settings.telegram_id == telegram_id).first()
    if not settings:
        settings = Settings(telegram_id=telegram_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

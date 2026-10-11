"""Date & time utilities for dummy Home Assistant."""
from datetime import datetime, timezone

DEFAULT_TIME_ZONE = timezone.utc

def now():
    return datetime.now(timezone.utc)

def utcnow():
    return datetime.now(timezone.utc)

def as_utc(d):
    if d is None:
        return None
    if d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)

def as_local(d):
    return d

def parse_datetime(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception:
        return None

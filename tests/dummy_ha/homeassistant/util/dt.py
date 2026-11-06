"""Date & time utilities for dummy Home Assistant."""
from datetime import datetime, timezone, timedelta
import zoneinfo

DEFAULT_TIME_ZONE = timezone.utc
UTC = timezone.utc

def set_default_time_zone(tz):
    global DEFAULT_TIME_ZONE
    if isinstance(tz, str):
        try:
            DEFAULT_TIME_ZONE = zoneinfo.ZoneInfo(tz)
        except Exception:
            if "Rome" in tz or "CET" in tz:
                DEFAULT_TIME_ZONE = timezone(timedelta(hours=1))
            else:
                DEFAULT_TIME_ZONE = timezone.utc
    else:
        DEFAULT_TIME_ZONE = tz

def get_time_zone(time_zone_str):
    try:
        return zoneinfo.ZoneInfo(time_zone_str)
    except Exception:
        if "Rome" in time_zone_str or "CET" in time_zone_str:
            return timezone(timedelta(hours=1))
        return timezone.utc

def now():
    return datetime.now(DEFAULT_TIME_ZONE)

def utcnow():
    return datetime.now(timezone.utc)

def as_utc(d):
    if d is None:
        return None
    if d.tzinfo is None:
        return d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)

def as_local(d):
    if d is None:
        return None
    if d.tzinfo is None:
        return d.replace(tzinfo=DEFAULT_TIME_ZONE)
    return d.astimezone(DEFAULT_TIME_ZONE)

def parse_datetime(dt_str):
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except Exception:
        return None


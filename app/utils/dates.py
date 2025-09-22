from datetime import datetime
import zoneinfo
from app.core.config import settings

def to_local_date_YYYY_MM_DD(dt_utc: datetime) -> str:
    tz = zoneinfo.ZoneInfo(settings.LOCAL_TIMEZONE)
    return dt_utc.astimezone(tz).strftime("%Y-%m-%d")

def local_date_for_now():
    tz = zoneinfo.ZoneInfo(settings.LOCAL_TIMEZONE)
    return datetime.now(tz).date()

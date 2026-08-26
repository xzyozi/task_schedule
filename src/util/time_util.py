# src/util/time_util.py
from datetime import datetime, timezone, tzinfo
from typing import Optional

# A timezone-aware equivalent of datetime.now()
def get_current_utc_time() -> datetime:
    """Returns the current time as a timezone-aware datetime object in UTC."""
    return datetime.now(timezone.utc)

def to_utc(dt: datetime) -> datetime:
    """
    Converts a datetime object to a timezone-aware UTC datetime.

    If the datetime object is naive, it's assumed to be in the system's local timezone.
    """
    if dt.tzinfo is None:
        # If naive, assume local timezone and convert to UTC
        return dt.astimezone(timezone.utc)
    # If already aware, just convert to UTC
    return dt.astimezone(timezone.utc)

def to_local_tz(dt_utc: datetime, local_tz: Optional[tzinfo] = None) -> datetime:
    """
    Converts a timezone-aware UTC datetime object to a local timezone.

    If local_tz is not provided, it defaults to the system's local timezone.
    The input datetime must be timezone-aware.
    """
    if dt_utc.tzinfo is None:
        raise ValueError("Input datetime must be timezone-aware.")
    
    # If no specific timezone is given, convert to the system's local timezone
    if local_tz is None:
        return dt_utc.astimezone()
    
    return dt_utc.astimezone(local_tz)

def ensure_aware(dt: datetime) -> datetime:
    """
    Ensures a datetime object is timezone-aware.
    If naive, it assumes UTC. This is useful for values coming from a DB
    that are known to be UTC but might lack tzinfo.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

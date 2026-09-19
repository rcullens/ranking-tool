"""When Texas six-man actually plays: Thursday, Friday, and Saturday nights."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

CHICAGO = ZoneInfo("America/Chicago")

# Monday=0 … Sunday=6. Six-man also sneaks in the occasional Thursday
# opener and Saturday makeup; Sunday before 2am is still "Saturday night."
FOOTBALL_WEEKDAYS = {3, 4, 5}
SUNDAY = 6
LATE_SUNDAY_HOUR = 2
WINDOW_START_HOUR = 10
WINDOW_END_HOUR = 24


def now_central(when: datetime | None = None) -> datetime:
    if when is None:
        return datetime.now(CHICAGO)
    if when.tzinfo is None:
        return when.replace(tzinfo=CHICAGO)
    return when.astimezone(CHICAGO)


def in_football_window(when: datetime | None = None) -> bool:
    """True during the Thu–Sat (and wee-hours Sunday) live-score window."""

    stamp = now_central(when)
    if stamp.weekday() in FOOTBALL_WEEKDAYS and WINDOW_START_HOUR <= stamp.hour < WINDOW_END_HOUR:
        return True
    if stamp.weekday() == SUNDAY and stamp.hour < LATE_SUNDAY_HOUR:
        return True
    return False


def window_label(when: datetime | None = None) -> str:
    stamp = now_central(when)
    if not in_football_window(stamp):
        return "off"
    names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day = names[stamp.weekday()]
    if stamp.weekday() == SUNDAY:
        return "Saturday late"
    return day


def next_window_start(when: datetime | None = None) -> datetime:
    """Next time the poller should treat as a live football window."""

    stamp = now_central(when)
    if in_football_window(stamp):
        return stamp
    cursor = stamp.replace(minute=0, second=0, microsecond=0)
    for _ in range(8 * 24):
        cursor += timedelta(hours=1)
        if in_football_window(cursor):
            return cursor
    return stamp + timedelta(days=1)

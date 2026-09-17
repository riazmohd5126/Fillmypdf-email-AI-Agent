from __future__ import annotations

import datetime as dt

import holidays

US_HOLIDAYS = holidays.US()

# Weekdays, 8:30-11:30 and 13:30-16:30 local time (design doc section 6.1)
SEND_WINDOWS = [
    (dt.time(8, 30), dt.time(11, 30)),
    (dt.time(13, 30), dt.time(16, 30)),
]


def is_business_day(date: dt.date) -> bool:
    return date.weekday() < 5 and date not in US_HOLIDAYS


def add_business_days(start: dt.date, business_days: int) -> dt.date:
    current = start
    added = 0
    while added < business_days:
        current += dt.timedelta(days=1)
        if is_business_day(current):
            added += 1
    return current


def is_within_send_window(local_dt: dt.datetime) -> bool:
    if not is_business_day(local_dt.date()):
        return False
    return any(start <= local_dt.time() <= end for start, end in SEND_WINDOWS)


def next_send_window_start(after: dt.datetime) -> dt.datetime:
    """Earliest moment >= after that falls inside a send window on a business day."""
    day = after.date()
    for _ in range(60):
        if is_business_day(day):
            for start, end in SEND_WINDOWS:
                window_start = dt.datetime.combine(day, start, tzinfo=after.tzinfo)
                window_end = dt.datetime.combine(day, end, tzinfo=after.tzinfo)
                if after <= window_end:
                    return max(after, window_start)
        day += dt.timedelta(days=1)
        after = dt.datetime.combine(day, dt.time(0, 0), tzinfo=after.tzinfo)
    raise RuntimeError("could not find a send window within 60 days")

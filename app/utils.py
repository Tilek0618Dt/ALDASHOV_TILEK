import datetime as dt

def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def in_30_days() -> dt.datetime:
    return utcnow() + dt.timedelta(days=30)

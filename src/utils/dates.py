from datetime import datetime, timedelta
from typing import Optional

def get_today_str() -> str:
    return datetime.now().strftime('%Y-%m-%d')

def get_lookback_date(end_date: str, days: int) -> str:
    """Returns date string 'days' prior to end_date."""
    dt = datetime.strptime(end_date, '%Y-%m-%d')
    start_dt = dt - timedelta(days=days)
    return start_dt.strftime('%Y-%m-%d')

def parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, '%Y-%m-%d')

"""
Kaivor Time Utilities
"""

from datetime import datetime

try:
    from zoneinfo import ZoneInfo

    _ZONE = ZoneInfo("Europe/London")

    def now():
        return datetime.now(_ZONE)

    def timezone_name():
        return _ZONE.key

except Exception:

    def now():
        return datetime.now()

    def timezone_name():
        return "Local"


def timestamp():
    return now().strftime("%Y%m%d_%H%M%S")


def display_time():
    return now().strftime("%d %b %Y %H:%M:%S")


def display_timezone():
    return timezone_name()

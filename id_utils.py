from datetime import datetime, timezone
from typing import Optional

# Hour-to-letter mapping (24 letters for 24 hours, skip O)
HOUR_LETTERS = "ABCDEFGHIJKLMNPQRSTUVWXY"

def generate_time_based_id(dt: Optional[datetime] = None) -> str:
    """
    Generate a 3-character time-based ID from UTC time.

    Format: [Hour Letter A-Y][Minute 00-59]

    Args:
        dt: datetime object (UTC). If None, uses current UTC time.

    Returns:
        3-character ID string (e.g., "A12", "Q47", "Y59")
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    # Ensure we're working with UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    hour = dt.hour  # 0-23
    minute = dt.minute  # 0-59

    # Generate ID: letter + two-digit minute
    letter = HOUR_LETTERS[hour]
    return f"{letter}{minute:02d}"

# src/utils/dates.py
#
# Tolerant date parsing for the free-form date strings that flow through the
# pipeline (TK documentation dates entered by users, patent grant dates from
# heterogeneous sources). Real data is not always YYYY-MM-DD — it can be
# year-only, year-month, or an ISO timestamp. This helper accepts those forms
# and returns None (never raises) for anything it cannot understand, so callers
# can treat "no parseable date" as "no evidence" rather than crashing.

from datetime import date, datetime
from typing import Optional

# Explicit non-ISO / partial formats, tried in order after ISO parsing.
_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y-%m", "%Y/%m", "%Y")

# Sentinel strings that mean "no date".
_EMPTY = {"", "nan", "none", "null", "n/a", "na", "unknown", "-"}


def parse_date(value: object) -> Optional[date]:
    """Parse a free-form date string into a `date`, or return None.

    Supports:
      * YYYY-MM-DD              -> that date
      * YYYY-MM                 -> first of that month
      * YYYY                    -> Jan 1 of that year
      * ISO 8601 timestamps     -> the date part (e.g. 2020-01-04T12:30:00Z)
      * empty / sentinel / junk -> None  (never raises)
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    s = str(value).strip()
    if s.lower() in _EMPTY:
        return None

    # ISO 8601 first (full dates and timestamps, incl. trailing 'Z' / offsets).
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    # Partial / non-ISO separators.
    for fmt in _FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    return None

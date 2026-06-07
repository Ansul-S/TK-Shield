# Tests for the tolerant date parser (A2) — no network, no models.

from datetime import date, datetime

import pytest

from src.utils.dates import parse_date


@pytest.mark.parametrize("value,expected", [
    ("1994-06-15", date(1994, 6, 15)),   # full ISO date
    ("1994/06/15", date(1994, 6, 15)),   # slash separators
    ("1994.06.15", date(1994, 6, 15)),   # dot separators
    ("1994-06", date(1994, 6, 1)),       # year-month → first of month
    ("1994/06", date(1994, 6, 1)),
    ("1994", date(1994, 1, 1)),          # year only → Jan 1
    ("2020-01-04T12:30:00", date(2020, 1, 4)),    # ISO timestamp
    ("2020-01-04T12:30:00Z", date(2020, 1, 4)),   # ISO timestamp with Z
    ("2020-01-04T12:30:00+05:30", date(2020, 1, 4)),  # with offset
    ("  1994-06-15  ", date(1994, 6, 15)),  # surrounding whitespace
])
def test_parse_valid_forms(value, expected):
    assert parse_date(value) == expected


@pytest.mark.parametrize("value", [
    "", "   ", "nan", "NaN", "none", "None", "null", "n/a", "unknown", "-",
    "circa 1900", "sometime in the 90s", "not a date", "13/13/2020",
    "2020-13-01",   # invalid month
])
def test_invalid_or_empty_returns_none(value):
    assert parse_date(value) is None


def test_none_and_native_types():
    assert parse_date(None) is None
    assert parse_date(date(2001, 2, 3)) == date(2001, 2, 3)
    assert parse_date(datetime(2001, 2, 3, 4, 5)) == date(2001, 2, 3)


def test_never_raises_on_arbitrary_input():
    # Contract: callers can pass anything; we return None, never raise.
    for junk in (12345, [], {}, object(), "🌿", "199"):
        parse_date(junk)  # must not raise

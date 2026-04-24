"""Generate authentication and login events."""

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config import CompanyConfig

EVENT_TYPES = [
    "login_success",
    "login_failure",
    "mfa_challenge",
    "mfa_success",
    "mfa_failure",
    "password_reset",
    "session_expired",
    "logout",
    "account_locked",
    "account_unlocked",
]

# Probability distribution for event types (normal user, per session)
EVENT_WEIGHTS = {
    "login_success": 0.45,
    "mfa_challenge": 0.20,
    "mfa_success": 0.18,
    "logout": 0.07,
    "session_expired": 0.04,
    "login_failure": 0.03,
    "mfa_failure": 0.01,
    "password_reset": 0.01,
    "account_locked": 0.005,
    "account_unlocked": 0.005,
}

BROWSERS = [
    "Chrome 122",
    "Chrome 121",
    "Chrome 120",
    "Firefox 123",
    "Firefox 122",
    "Safari 17.3",
    "Safari 17.2",
    "Edge 122",
    "Edge 121",
]

OS_LIST = [
    "macOS 14.3",
    "macOS 14.2",
    "macOS 13.6",
    "Windows 11",
    "Windows 10",
    "Ubuntu 22.04",
    "Ubuntu 20.04",
]

# City → (country, lat, lon) for geo data
GEO_DATA = {
    "New York": ("US", 40.7128, -74.0060),
    "San Francisco": ("US", 37.7749, -122.4194),
    "Austin": ("US", 30.2672, -97.7431),
    "Chicago": ("US", 41.8781, -87.6298),
    "Seattle": ("US", 47.6062, -122.3321),
    "Denver": ("US", 39.7392, -104.9903),
    "Boston": ("US", 42.3601, -71.0589),
    "Atlanta": ("US", 33.7490, -84.3880),
    "Los Angeles": ("US", 34.0522, -118.2437),
    "Miami": ("US", 25.7617, -80.1918),
    "Portland": ("US", 45.5152, -122.6784),
    "London": ("GB", 51.5074, -0.1278),
    "Toronto": ("CA", 43.6532, -79.3832),
    "Singapore": ("SG", 1.3521, 103.8198),
    "Tokyo": ("JP", 35.6762, 139.6503),
    "Sydney": ("AU", -33.8688, 151.2093),
}


def _user_geo(employee: dict) -> dict:
    """Get geo data for an employee based on location."""
    location = employee.get("location", "Remote")
    # Extract city from "City, ST" format
    city = location.split(",")[0].strip()

    if city in GEO_DATA:
        country, lat, lon = GEO_DATA[city]
    elif city == "Remote":
        city = random.choice(list(GEO_DATA.keys()))
        country, lat, lon = GEO_DATA[city]
    else:
        country, lat, lon = "US", 40.7128, -74.0060

    # Small jitter to avoid identical coords
    lat += random.uniform(-0.05, 0.05)
    lon += random.uniform(-0.05, 0.05)

    return {
        "city": city,
        "country": country,
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
    }


def _user_ip(employee: dict) -> str:
    """Generate a consistent-ish IP for a user (based on employee_id hash)."""
    seed_val = hash(employee["employee_id"]) % 10000
    rng = random.Random(seed_val)
    return (
        f"{rng.randint(50, 220)}.{rng.randint(1, 254)}"
        f".{rng.randint(1, 254)}.{rng.randint(1, 254)}"
    )


def _generate_auth_time(day: date) -> str:
    """Generate login timestamp biased toward morning (start of workday)."""
    if day.weekday() < 5:
        hour = int(random.gauss(9, 2.5))
        hour = max(5, min(23, hour))
    else:
        hour = random.randint(8, 22)

    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    dt = datetime(
        day.year,
        day.month,
        day.day,
        hour,
        minute,
        second,
        tzinfo=timezone.utc,
    )
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _generate_session_events(
    employee: dict,
    day: date,
) -> list[dict]:
    """Generate auth events for one user's session on a given day."""
    events = []
    ip = _user_ip(employee)
    geo = _user_geo(employee)
    session_id = f"sess-{uuid.uuid4().hex[:12]}"
    has_mfa = employee.get("mfa_enrolled") is True

    # Pick event types for this session
    event_types = list(EVENT_WEIGHTS.keys())
    weights = list(EVENT_WEIGHTS.values())

    # Typical session: login → mfa → work → logout/expire
    num_events = random.randint(1, 4)

    for _ in range(num_events):
        event_type = random.choices(event_types, weights=weights, k=1)[0]

        # Skip MFA events if user doesn't have MFA
        if "mfa" in event_type and not has_mfa:
            event_type = "login_success"

        event = {
            "timestamp": _generate_auth_time(day),
            "event_id": f"auth-{uuid.uuid4().hex[:12]}",
            "event_type": event_type,
            "user_id": employee["employee_id"],
            "email": employee["email"],
            "source_ip": ip,
            "geo": geo,
            "device": {
                "type": random.choice(["desktop", "laptop", "mobile"]),
                "os": random.choice(OS_LIST),
                "browser": random.choice(BROWSERS),
            },
            "session_id": session_id,
            "mfa_used": has_mfa and event_type in ("login_success", "mfa_success"),
            "risk_score": round(random.uniform(0.0, 0.3), 2),
        }

        # Imperfection: 8% missing device info
        if random.random() < 0.08:
            del event["device"]

        # Imperfection: occasional timezone inconsistency
        if random.random() < 0.03:
            event["timestamp"] = event["timestamp"].replace("Z", "-05:00")

        events.append(event)

    return events


def generate_auth_day(
    day: date,
    employees: list[dict],
) -> list[dict]:
    """Generate auth events for all employees on a single day."""
    events = []
    is_weekday = day.weekday() < 5
    active = [e for e in employees if e["status"] == "active"]

    for emp in active:
        # Weekdays: 85% of users log in. Weekends: 5%
        if (is_weekday and random.random() > 0.15) or (
            not is_weekday and random.random() < 0.05
        ):
            events.extend(_generate_session_events(emp, day))

    # Sort by timestamp
    events.sort(key=lambda e: e["timestamp"])
    return events


def generate_auth_events(
    config: CompanyConfig,
    company_data: dict,
    start_date: date,
) -> dict[str, list[dict]]:
    """Generate auth events for the full activity window."""
    daily_events = {}

    for day_offset in range(config.activity_days):
        day = start_date + timedelta(days=day_offset)
        events = generate_auth_day(day, company_data["employees"])
        daily_events[day.isoformat()] = events

    return daily_events

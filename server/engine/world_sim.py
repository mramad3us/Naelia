"""World simulation — time advancement, NPC schedules, background events."""

import json

from server.database.connection import fetch_one, fetch_all, execute
from server.engine.weather import check_weather_transition
from server.config import CONFIG


async def advance_time(hours: int = 0, minutes: int = 0) -> dict:
    """Advance in-game time and trigger any world sim effects.

    Returns the new world state plus any events that fired.
    """
    # Fetch current state
    ws = await fetch_one("SELECT * FROM world_state WHERE id = 1")
    if ws is None:
        return {"error": "World state not initialized"}

    # Calculate new time
    total_minutes = (ws["current_hour"] * 60 + ws["current_minute"]) + (hours * 60 + minutes)
    new_days = total_minutes // (24 * 60)
    remaining = total_minutes % (24 * 60)
    new_hour = remaining // 60
    new_minute = remaining % 60

    # Advance date if needed
    new_date = ws["current_date"]
    if new_days > 0:
        new_date = _advance_date(ws["current_date"], new_days)

    # Determine season from date
    new_season = _get_season(new_date)

    # Update world state
    await execute(
        """UPDATE world_state
           SET current_date = ?, current_hour = ?, current_minute = ?, season = ?
           WHERE id = 1""",
        (new_date, new_hour, new_minute, new_season),
    )

    events = []

    # Check weather transitions for each hour that passed
    weather_by_location = json.loads(ws["weather_by_location"]) if ws["weather_by_location"] else {}
    for loc_name in weather_by_location:
        weather_change = await check_weather_transition(loc_name, new_hour, new_season)
        if weather_change:
            events.append({
                "type": "weather_change",
                "location": loc_name,
                "weather": weather_change,
            })

    # Check NPC schedules if enabled
    if CONFIG.get("world_simulation", {}).get("npc_schedule_enabled", True):
        schedule_events = await _check_npc_schedules(new_hour, new_date)
        events.extend(schedule_events)

    return {
        "previous": {
            "date": ws["current_date"],
            "hour": ws["current_hour"],
            "minute": ws["current_minute"],
        },
        "current": {
            "date": new_date,
            "hour": new_hour,
            "minute": new_minute,
            "season": new_season,
        },
        "days_advanced": new_days,
        "events": events,
    }


async def set_time(date: str = None, hour: int = None, minute: int = None) -> dict:
    """Set exact date/time (for narrative jumps like 'three days later')."""
    ws = await fetch_one("SELECT * FROM world_state WHERE id = 1")
    new_date = date or ws["current_date"]
    new_hour = hour if hour is not None else ws["current_hour"]
    new_minute = minute if minute is not None else ws["current_minute"]
    new_season = _get_season(new_date)

    await execute(
        """UPDATE world_state
           SET current_date = ?, current_hour = ?, current_minute = ?, season = ?
           WHERE id = 1""",
        (new_date, new_hour, new_minute, new_season),
    )

    return {
        "date": new_date,
        "hour": new_hour,
        "minute": new_minute,
        "season": new_season,
    }


async def _check_npc_schedules(current_hour: int, current_date: str) -> list[dict]:
    """Check if any NPC schedule entries are active for the current time."""
    # Get current day of tenday (1-10)
    day_of_tenday = _get_day_of_tenday(current_date)

    schedules = await fetch_all(
        """SELECT ns.*, c.name as character_name, l.name as location_name
           FROM npc_schedules ns
           JOIN characters c ON ns.character_id = c.id
           LEFT JOIN locations l ON ns.location_id = l.id
           WHERE ns.hour_start <= ? AND ns.hour_end > ?
             AND (ns.day_of_tenday IS NULL OR ns.day_of_tenday = ?)""",
        (current_hour, current_hour, day_of_tenday),
    )

    events = []
    for s in schedules:
        # Move NPC to scheduled location
        if s["location_id"]:
            await execute(
                "UPDATE characters SET current_location_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (s["location_id"], s["character_id"]),
            )
            events.append({
                "type": "npc_schedule",
                "character": s["character_name"],
                "location": s["location_name"],
                "activity": s["activity"],
            })

    return events


def _advance_date(date_str: str, days: int) -> str:
    """Advance a DR date string by N days. Simple calendar (30 days/month, 12 months/year)."""
    parts = date_str.split("-")
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])

    day += days
    while day > 30:
        day -= 30
        month += 1
    while month > 12:
        month -= 12
        year += 1

    return f"{year:04d}-{month:02d}-{day:02d}"


def _get_season(date_str: str) -> str:
    """Determine season from date. Faerunian calendar approximation."""
    month = int(date_str.split("-")[1])
    if month in (12, 1, 2):
        return "winter"
    elif month in (3, 4, 5):
        return "spring"
    elif month in (6, 7, 8):
        return "summer"
    else:
        return "autumn"


def _get_day_of_tenday(date_str: str) -> int:
    """Get day within the current tenday (1-10)."""
    day = int(date_str.split("-")[2])
    return ((day - 1) % 10) + 1

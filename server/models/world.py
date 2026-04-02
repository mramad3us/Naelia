"""Model layer for world state, weather tables, and world history."""

from typing import Optional

from server.database.connection import (
    fetch_one,
    fetch_all,
    execute,
    to_json,
    parse_row_json,
)

JSON_FIELDS = ("weather_by_location",)


# ---------------------------------------------------------------------------
# World State (singleton, id=1)
# ---------------------------------------------------------------------------

async def get_world_state() -> Optional[dict]:
    """Fetch the singleton world-state row, parsing JSON fields."""
    row = await fetch_one("SELECT * FROM world_state WHERE id = 1", ())
    if row is None:
        return None
    return parse_row_json(row, *JSON_FIELDS)


async def update_world_state(updates: dict) -> Optional[dict]:
    """Update any fields on the world-state singleton.

    JSON-typed fields are serialized automatically.
    """
    if not updates:
        return await get_world_state()

    fields = dict(updates)
    for key in JSON_FIELDS:
        if key in fields and not isinstance(fields[key], str):
            fields[key] = to_json(fields[key])

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    params = tuple(fields.values()) + (1,)

    await execute(
        f"UPDATE world_state SET {set_clause} WHERE id = ?",
        params,
    )
    return await get_world_state()


async def advance_time(hours: int = 0, minutes: int = 0) -> Optional[dict]:
    """Add hours/minutes to the current world clock.

    Handles minute overflow (>=60 → extra hours) and hour overflow
    (>=24 → increments current_date by one day per overflow).
    Returns the updated world state.
    """
    state = await get_world_state()
    if state is None:
        return None

    total_minutes = state["current_minute"] + minutes
    extra_hours, new_minute = divmod(total_minutes, 60)

    total_hours = state["current_hour"] + hours + extra_hours
    extra_days, new_hour = divmod(total_hours, 24)

    updates: dict = {"current_hour": new_hour, "current_minute": new_minute}

    if extra_days:
        # Advance the date string (ISO format YYYY-MM-DD)
        from datetime import datetime, timedelta

        current = datetime.strptime(state["current_date"], "%Y-%m-%d")
        new_date = current + timedelta(days=extra_days)
        updates["current_date"] = new_date.strftime("%Y-%m-%d")

    return await update_world_state(updates)


# ---------------------------------------------------------------------------
# Weather Tables
# ---------------------------------------------------------------------------

async def get_weather_table(season: str) -> list[dict]:
    """Return all weather-table rows for a given season."""
    return await fetch_all(
        "SELECT * FROM weather_tables WHERE season = ? ORDER BY roll_min",
        (season,),
    )


# ---------------------------------------------------------------------------
# World History
# ---------------------------------------------------------------------------

async def get_world_history(
    public_only: bool = True,
    limit: int = 50,
) -> list[dict]:
    """Return world-history entries ordered by date descending."""
    query = "SELECT * FROM world_history"
    params: list = []

    if public_only:
        query += " WHERE is_public = 1"

    query += " ORDER BY date_dr DESC LIMIT ?"
    params.append(limit)
    return await fetch_all(query, tuple(params))


async def add_world_history(
    date_dr: str,
    title: str,
    description: str,
    importance: int = 3,
    is_public: int = 1,
) -> int:
    """Insert a world-history entry and return its id."""
    return await execute(
        """
        INSERT INTO world_history (date_dr, title, description, importance, is_public)
        VALUES (?, ?, ?, ?, ?)
        """,
        (date_dr, title, description, importance, is_public),
    )

"""Model layer for sessions, session events, and dice rolls."""

from datetime import datetime, timezone
from typing import Optional

from server.database.connection import (
    fetch_one,
    fetch_all,
    execute,
    to_json,
    parse_row_json,
)

JSON_FIELDS = ("characters_involved",)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------

async def start_session() -> dict:
    """Create a new session row and activate it in world_state.

    Computes session_number as MAX(session_number)+1, records start_real_time,
    and captures the current in-game date from world_state.
    """
    row = await fetch_one(
        "SELECT MAX(session_number) AS max_num FROM sessions", ()
    )
    next_number = (row["max_num"] or 0) + 1 if row else 1

    world = await fetch_one("SELECT current_date FROM world_state WHERE id = 1", ())
    in_game_date = world["current_date"] if world else None

    now = _now()
    session_id = await execute(
        """
        INSERT INTO sessions (session_number, start_real_time, in_game_date_start)
        VALUES (?, ?, ?)
        """,
        (next_number, now, in_game_date),
    )

    await execute(
        "UPDATE world_state SET active_session_id = ? WHERE id = 1",
        (session_id,),
    )

    return await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))


async def end_session(summary: str) -> Optional[dict]:
    """End the active session.

    Sets end_real_time, summary, captures the current in-game date as
    in_game_date_end, and clears world_state.active_session_id.
    """
    world = await fetch_one(
        "SELECT active_session_id, current_date FROM world_state WHERE id = 1", ()
    )
    if world is None or world["active_session_id"] is None:
        return None

    session_id = world["active_session_id"]
    now = _now()

    await execute(
        """
        UPDATE sessions
        SET end_real_time = ?, summary = ?, in_game_date_end = ?
        WHERE id = ?
        """,
        (now, summary, world["current_date"], session_id),
    )

    await execute(
        "UPDATE world_state SET active_session_id = NULL WHERE id = 1", ()
    )

    return await fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))


async def get_current_session() -> Optional[dict]:
    """Fetch the session currently marked active in world_state."""
    world = await fetch_one(
        "SELECT active_session_id FROM world_state WHERE id = 1", ()
    )
    if world is None or world["active_session_id"] is None:
        return None

    return await fetch_one(
        "SELECT * FROM sessions WHERE id = ?",
        (world["active_session_id"],),
    )


async def get_session_history(limit: int = 20) -> list[dict]:
    """Return recent sessions ordered by session_number descending."""
    return await fetch_all(
        "SELECT * FROM sessions ORDER BY session_number DESC LIMIT ?",
        (limit,),
    )


# ---------------------------------------------------------------------------
# Session Events
# ---------------------------------------------------------------------------

async def log_event(
    session_id: int,
    event_type: str,
    description: str,
    characters_involved: list | None = None,
    location_id: int | None = None,
) -> int:
    """Log a session event. Returns the new event id."""
    # Get event_order as max + 1 for this session
    row = await fetch_one(
        "SELECT MAX(event_order) AS max_order FROM session_events WHERE session_id = ?",
        (session_id,),
    )
    event_order = (row["max_order"] or 0) + 1 if row else 1

    return await execute(
        """
        INSERT INTO session_events
            (session_id, event_order, event_type, description, location_id,
             participants)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            event_order,
            event_type,
            description,
            location_id,
            to_json(characters_involved) if characters_involved else "[]",
        ),
    )


# ---------------------------------------------------------------------------
# Dice Rolls
# ---------------------------------------------------------------------------

async def log_dice_roll(
    session_id: int,
    character_id: int,
    expression: str,
    result: int,
    details: dict,
    purpose: str,
) -> int:
    """Log a dice roll. Returns the new roll id."""
    return await execute(
        """
        INSERT INTO dice_rolls
            (session_id, character_id, roll_expression, roll_result,
             roll_details, purpose, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            character_id,
            expression,
            result,
            to_json(details),
            purpose,
            _now(),
        ),
    )

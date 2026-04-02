"""Combat model — async query and update functions for the combat_encounters table."""

from datetime import datetime, timezone
from typing import Optional

from server.database.connection import (
    fetch_one, fetch_all, execute, to_json, from_json, parse_row_json,
)


_JSON_FIELDS = ("combatants",)


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

async def get_combat_state(encounter_id: int) -> Optional[dict]:
    """Fetch an encounter by ID with parsed combatants and joined location name."""
    row = await fetch_one(
        "SELECT ce.*, l.name AS location_name "
        "FROM combat_encounters ce "
        "LEFT JOIN locations l ON l.id = ce.location_id "
        "WHERE ce.id = ?",
        (encounter_id,),
    )
    if row is None:
        return None
    return parse_row_json(row, *_JSON_FIELDS)


async def get_active_combat() -> Optional[dict]:
    """Fetch the most recent active encounter with parsed combatants."""
    row = await fetch_one(
        "SELECT ce.*, l.name AS location_name "
        "FROM combat_encounters ce "
        "LEFT JOIN locations l ON l.id = ce.location_id "
        "WHERE ce.status = 'active' "
        "ORDER BY ce.started_at DESC LIMIT 1",
        (),
    )
    if row is None:
        return None
    return parse_row_json(row, *_JSON_FIELDS)


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

async def start_combat(
    session_id: int,
    location_id: int,
    combatant_ids: list[int],
    teams: dict | None = None,
) -> int:
    """Create a new combat encounter and return its ID.

    Fetches each character's hp_current to populate the initial combatants
    JSON.  ``teams`` is an optional mapping of character_id → team name.
    """
    teams = teams or {}
    combatants = []

    for cid in combatant_ids:
        char = await fetch_one(
            "SELECT id, hp_current FROM characters WHERE id = ?", (cid,)
        )
        if char is None:
            raise ValueError(f"Character {cid} not found")
        combatants.append({
            "character_id": char["id"],
            "initiative": None,
            "is_current_turn": False,
            "hp_current": char["hp_current"],
            "conditions": [],
            "team": teams.get(cid),
        })

    now = datetime.now(timezone.utc).isoformat()
    encounter_id = await execute(
        "INSERT INTO combat_encounters "
        "(session_id, location_id, combatants, current_round, status, started_at) "
        "VALUES (?, ?, ?, 1, 'active', ?)",
        (session_id, location_id, to_json(combatants), now),
    )
    return encounter_id


async def set_initiative(encounter_id: int, initiatives: dict) -> dict:
    """Set initiative values, sort combatants DESC, and mark the highest as current.

    ``initiatives`` maps character_id (int) → roll value (int/float).
    Returns the updated combat state.
    """
    state = await get_combat_state(encounter_id)
    if state is None:
        raise ValueError(f"Encounter {encounter_id} not found")

    combatants = state["combatants"]

    for c in combatants:
        if c["character_id"] in initiatives:
            c["initiative"] = initiatives[c["character_id"]]

    combatants.sort(key=lambda c: c["initiative"] or -1, reverse=True)

    for c in combatants:
        c["is_current_turn"] = False
    combatants[0]["is_current_turn"] = True

    await execute(
        "UPDATE combat_encounters SET combatants = ? WHERE id = ?",
        (to_json(combatants), encounter_id),
    )
    return await get_combat_state(encounter_id)


async def next_turn(encounter_id: int) -> dict:
    """Advance to the next combatant's turn.

    If the last combatant just finished, increment current_round and loop
    back to the first.  Returns the updated combat state.
    """
    state = await get_combat_state(encounter_id)
    if state is None:
        raise ValueError(f"Encounter {encounter_id} not found")

    combatants = state["combatants"]
    current_round = state["current_round"]

    current_idx = next(
        (i for i, c in enumerate(combatants) if c["is_current_turn"]), 0
    )

    combatants[current_idx]["is_current_turn"] = False

    next_idx = current_idx + 1
    if next_idx >= len(combatants):
        next_idx = 0
        current_round += 1

    combatants[next_idx]["is_current_turn"] = True

    await execute(
        "UPDATE combat_encounters SET combatants = ?, current_round = ? WHERE id = ?",
        (to_json(combatants), current_round, encounter_id),
    )
    return await get_combat_state(encounter_id)


async def update_combatant(
    encounter_id: int, character_id: int, updates: dict
) -> dict:
    """Update fields on a specific combatant within the encounter JSON.

    Common update keys: hp_current, conditions, etc.
    Returns the updated combat state.
    """
    state = await get_combat_state(encounter_id)
    if state is None:
        raise ValueError(f"Encounter {encounter_id} not found")

    combatants = state["combatants"]

    for c in combatants:
        if c["character_id"] == character_id:
            c.update(updates)
            break
    else:
        raise ValueError(
            f"Character {character_id} not in encounter {encounter_id}"
        )

    await execute(
        "UPDATE combat_encounters SET combatants = ? WHERE id = ?",
        (to_json(combatants), encounter_id),
    )
    return await get_combat_state(encounter_id)


async def end_combat(encounter_id: int, outcome: str) -> dict:
    """Mark an encounter as completed with an outcome.

    Returns the final combat state.
    """
    now = datetime.now(timezone.utc).isoformat()
    await execute(
        "UPDATE combat_encounters "
        "SET status = 'completed', ended_at = ?, outcome = ? "
        "WHERE id = ?",
        (now, outcome, encounter_id),
    )
    return await get_combat_state(encounter_id)

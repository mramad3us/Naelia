"""Character model — async query and update functions for the characters table."""

from datetime import datetime, timezone
from typing import Optional

from server.database.connection import (
    fetch_one, fetch_all, execute, to_json, parse_row_json,
)

# Every JSON column on the characters table.
_JSON_FIELDS = (
    "aliases", "class_levels",
    "saves_proficient", "skills",
    "damage_resistances", "damage_immunities", "condition_immunities",
    "spell_slots", "spells_known", "innate_spells",
    "class_features", "racial_traits", "special_abilities",
    "legendary_actions", "lair_actions",
    "conditions", "quest_tags",
)

# Columns that store JSON and must be serialized on write.
_JSON_COLUMNS = set(_JSON_FIELDS)

# Lightweight projection used by list queries.
_BASIC_COLUMNS = (
    "id", "name", "type", "race", "status",
    "current_location_id", "importance",
    "hp_current", "hp_max", "ac", "cr",
)

# The DB column is "int" but we expose it as "int_" in Python.
_COL_ALIAS = {"int_": "int"}


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

async def get_character(character_id: int) -> Optional[dict]:
    """Fetch a single character by ID with all JSON fields parsed."""
    row = await fetch_one("SELECT * FROM characters WHERE id = ?", (character_id,))
    if row is None:
        return None
    return parse_row_json(row, *_JSON_FIELDS)


async def get_characters(filters: dict | None = None) -> list[dict]:
    """Return a filtered list of characters (basic columns only).

    Supported filter keys:
        type, status, location_id, importance, name (LIKE),
        is_public, org_id (joins through org_memberships).
    """
    filters = filters or {}

    if "org_id" in filters:
        base = (
            "SELECT DISTINCT c.{cols} FROM characters c "
            "JOIN org_memberships om ON om.character_id = c.id "
            "WHERE om.org_id = ?"
        ).format(cols=", c.".join(_BASIC_COLUMNS))
        params: list = [filters["org_id"]]
    else:
        base = "SELECT {cols} FROM characters c WHERE 1=1".format(
            cols=", ".join(f"c.{c}" for c in _BASIC_COLUMNS),
        )
        params = []

    if "type" in filters:
        base += " AND c.type = ?"
        params.append(filters["type"])
    if "status" in filters:
        base += " AND c.status = ?"
        params.append(filters["status"])
    if "location_id" in filters:
        base += " AND c.current_location_id = ?"
        params.append(filters["location_id"])
    if "importance" in filters:
        base += " AND c.importance >= ?"
        params.append(filters["importance"])
    if "name" in filters:
        base += " AND c.name LIKE ?"
        params.append(f"%{filters['name']}%")
    if "is_public" in filters:
        base += " AND c.is_public = ?"
        params.append(int(filters["is_public"]))

    base += " ORDER BY c.importance DESC, c.name"
    return await fetch_all(base, tuple(params))


async def get_characters_at_location(location_id: int) -> list[dict]:
    """Return all characters currently at a given location (basic columns)."""
    cols = ", ".join(_BASIC_COLUMNS)
    return await fetch_all(
        f"SELECT {cols} FROM characters WHERE current_location_id = ? "
        "ORDER BY importance DESC, name",
        (location_id,),
    )


async def get_character_relationships(character_id: int) -> list[dict]:
    """Return all relationships for a character, including the target's name."""
    return await fetch_all(
        "SELECT cr.id, cr.character_id, cr.target_id, "
        "       cr.relationship_type, cr.description, "
        "       cr.sentiment, cr.is_secret, "
        "       c.name AS target_name "
        "FROM character_relationships cr "
        "JOIN characters c ON c.id = cr.target_id "
        "WHERE cr.character_id = ? "
        "ORDER BY cr.relationship_type, c.name",
        (character_id,),
    )


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

async def update_character(character_id: int, updates: dict) -> int:
    """Update arbitrary columns on a character row.

    JSON-typed fields are automatically serialized.  ``updated_at`` is set to
    the current UTC timestamp.
    """
    updates = dict(updates)  # shallow copy so we don't mutate the caller's dict
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    set_clauses: list[str] = []
    params: list = []
    for key, value in updates.items():
        col = _COL_ALIAS.get(key, key)
        if key in _JSON_COLUMNS and value is not None:
            value = to_json(value)
        set_clauses.append(f'"{col}" = ?')
        params.append(value)

    params.append(character_id)
    query = f"UPDATE characters SET {', '.join(set_clauses)} WHERE id = ?"
    return await execute(query, tuple(params))


async def move_character(character_id: int, location_id: int) -> int:
    """Move a character to a new location."""
    return await update_character(character_id, {"current_location_id": location_id})

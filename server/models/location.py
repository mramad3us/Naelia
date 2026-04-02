"""Query functions for the locations table."""

from typing import Optional

from server.database.connection import fetch_one, fetch_all, parse_row_json

JSON_FIELDS = ("climate_modifier",)


async def get_location(location_id: int) -> Optional[dict]:
    """Return a single location by ID with parsed JSON fields."""
    row = await fetch_one("SELECT * FROM locations WHERE id = ?", (location_id,))
    if row is None:
        return None
    return parse_row_json(row, *JSON_FIELDS)


async def get_locations(filters: Optional[dict] = None) -> list[dict]:
    """Return locations matching optional filters.

    Supported filter keys:
        parent_id  — exact match (use None for root locations)
        type       — exact match on location type
        name       — substring match (LIKE %name%)
        is_public  — 0 or 1
        is_secret  — compatibility alias; converted by the route layer
    """
    clauses: list[str] = []
    params: list = []

    if filters:
        if "parent_id" in filters:
            if filters["parent_id"] is None:
                clauses.append("parent_id IS NULL")
            else:
                clauses.append("parent_id = ?")
                params.append(filters["parent_id"])

        if "type" in filters:
            clauses.append("type = ?")
            params.append(filters["type"])

        if "name" in filters:
            clauses.append("name LIKE ?")
            params.append(f"%{filters['name']}%")

        if "is_public" in filters:
            clauses.append("is_public = ?")
            params.append(filters["is_public"])

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = await fetch_all(f"SELECT * FROM locations{where}", tuple(params))
    return [parse_row_json(r, *JSON_FIELDS) for r in rows]


async def get_location_children(location_id: int) -> list[dict]:
    """Return direct children of a location."""
    rows = await fetch_all(
        "SELECT * FROM locations WHERE parent_id = ?", (location_id,)
    )
    return [parse_row_json(r, *JSON_FIELDS) for r in rows]


async def get_location_path(location_id: int) -> list[dict]:
    """Walk up the parent chain and return the full hierarchy from root to leaf."""
    path: list[dict] = []
    current_id: Optional[int] = location_id

    while current_id is not None:
        row = await fetch_one("SELECT * FROM locations WHERE id = ?", (current_id,))
        if row is None:
            break
        path.append(parse_row_json(row, *JSON_FIELDS))
        current_id = row["parent_id"]

    path.reverse()
    return path


async def get_characters_at_location(location_id: int) -> list[dict]:
    """Return basic info for characters whose current_location_id matches."""
    return await fetch_all(
        "SELECT id, name, type, status FROM characters WHERE current_location_id = ?",
        (location_id,),
    )

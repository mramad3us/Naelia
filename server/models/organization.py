"""Model layer for organizations, memberships, and inter-org relationships."""

from typing import Optional

from server.database.connection import fetch_one, fetch_all, execute


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

async def get_organization(org_id: int) -> Optional[dict]:
    """Return full details for a single organization."""
    return await fetch_one(
        "SELECT * FROM organizations WHERE id = ?",
        (org_id,),
    )


async def get_organizations(filters: dict | None = None) -> list[dict]:
    """Return organizations matching optional filters.

    Supported filter keys: type, parent_org_id, is_secret.
    """
    query = "SELECT * FROM organizations"
    clauses: list[str] = []
    params: list = []

    if filters:
        for key in ("type", "parent_org_id", "is_secret"):
            if key in filters:
                clauses.append(f"{key} = ?")
                params.append(filters[key])

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY name"
    return await fetch_all(query, tuple(params))


async def get_org_members(org_id: int) -> list[dict]:
    """Return members of an organization with character names."""
    return await fetch_all(
        """
        SELECT
            m.id,
            m.character_id,
            c.name AS character_name,
            m.role,
            m.rank,
            m.is_public,
            m.joined_date,
            m.notes
        FROM org_memberships m
        JOIN characters c ON c.id = m.character_id
        WHERE m.org_id = ?
        ORDER BY m.rank, c.name
        """,
        (org_id,),
    )


async def get_org_relationships(org_id: int) -> list[dict]:
    """Return inter-org relationships for an organization."""
    return await fetch_all(
        """
        SELECT
            r.id,
            r.org_id,
            r.target_org_id,
            o.name AS target_org_name,
            r.relationship_type,
            r.description,
            r.is_secret
        FROM org_relationships r
        JOIN organizations o ON o.id = r.target_org_id
        WHERE r.org_id = ?
        ORDER BY r.relationship_type, o.name
        """,
        (org_id,),
    )


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------

UPDATABLE_FIELDS = {
    "name",
    "parent_org_id",
    "type",
    "description",
    "headquarters_location_id",
    "symbol_description",
    "is_secret",
}


async def update_organization(org_id: int, updates: dict) -> Optional[dict]:
    """Update allowed fields on an organization and return the updated row.

    Returns None if org_id does not exist or no valid fields are provided.
    """
    fields = {k: v for k, v in updates.items() if k in UPDATABLE_FIELDS}
    if not fields:
        return None

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    params = tuple(fields.values()) + (org_id,)

    await execute(
        f"UPDATE organizations SET {set_clause} WHERE id = ?",
        params,
    )
    return await get_organization(org_id)

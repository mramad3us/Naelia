"""Model layer for plot threads, clues, and character involvement."""

from datetime import datetime, timezone
from typing import Optional

from server.database.connection import fetch_one, fetch_all, execute


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Plot Threads
# ---------------------------------------------------------------------------

async def get_plot_threads(filters: dict | None = None) -> list[dict]:
    """Return plot threads matching optional filters.

    Supported filter keys: status, priority.
    """
    query = "SELECT * FROM plot_threads"
    clauses: list[str] = []
    params: list = []

    if filters:
        if "status" in filters:
            clauses.append("status = ?")
            params.append(filters["status"])
        if "priority" in filters:
            clauses.append("priority = ?")
            params.append(filters["priority"])

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY priority DESC, created_at DESC"
    return await fetch_all(query, tuple(params))


async def get_plot_thread(plot_id: int) -> Optional[dict]:
    """Return a plot thread with its clues and involved characters."""
    thread = await fetch_one(
        "SELECT * FROM plot_threads WHERE id = ?",
        (plot_id,),
    )
    if thread is None:
        return None

    clues = await fetch_all(
        "SELECT * FROM plot_clues WHERE plot_id = ? ORDER BY created_at",
        (plot_id,),
    )

    characters = await fetch_all(
        """
        SELECT
            pc.character_id,
            c.name AS character_name,
            pc.role
        FROM plot_characters pc
        JOIN characters c ON c.id = pc.character_id
        WHERE pc.plot_id = ?
        ORDER BY pc.role, c.name
        """,
        (plot_id,),
    )

    thread["clues"] = clues
    thread["characters"] = characters
    return thread


async def create_plot_thread(data: dict) -> int:
    """Create a new plot thread and return its id."""
    now = _now()
    return await execute(
        """
        INSERT INTO plot_threads
            (title, status, priority, description, created_session_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["title"],
            data.get("status", "active"),
            data.get("priority", 3),
            data.get("description", ""),
            data.get("created_session_id"),
            now,
            now,
        ),
    )


UPDATABLE_THREAD_FIELDS = {"status", "priority", "description", "resolved_session_id"}


async def update_plot_thread(plot_id: int, updates: dict) -> Optional[dict]:
    """Update allowed fields on a plot thread.

    Automatically sets updated_at.  Returns the updated thread or None.
    """
    fields = {k: v for k, v in updates.items() if k in UPDATABLE_THREAD_FIELDS}
    if not fields:
        return None

    fields["updated_at"] = _now()

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    params = tuple(fields.values()) + (plot_id,)

    await execute(
        f"UPDATE plot_threads SET {set_clause} WHERE id = ?",
        params,
    )
    return await get_plot_thread(plot_id)


# ---------------------------------------------------------------------------
# Plot Clues
# ---------------------------------------------------------------------------

async def add_clue(plot_id: int, description: str) -> int:
    """Add a new undiscovered clue to a plot thread. Returns clue id."""
    return await execute(
        """
        INSERT INTO plot_clues (plot_id, description, is_discovered, created_at)
        VALUES (?, ?, 0, ?)
        """,
        (plot_id, description, _now()),
    )


async def discover_clue(
    clue_id: int,
    session_id: int,
    details: str,
) -> Optional[dict]:
    """Mark a clue as discovered. Returns the updated clue row."""
    await execute(
        """
        UPDATE plot_clues
        SET is_discovered = 1, discovered_session_id = ?, discovery_details = ?
        WHERE id = ?
        """,
        (session_id, details, clue_id),
    )
    return await fetch_one(
        "SELECT * FROM plot_clues WHERE id = ?",
        (clue_id,),
    )

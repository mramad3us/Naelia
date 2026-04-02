"""Model layer for custom mechanics, guild contracts, and token ledger."""

from datetime import datetime, timezone
from typing import Optional

from server.database.connection import (
    fetch_one, fetch_all, execute, to_json, parse_row_json,
)


# ---------------------------------------------------------------------------
# Custom mechanics
# ---------------------------------------------------------------------------

async def get_mechanic(name: str) -> Optional[dict]:
    """Fetch a custom mechanic by name, with rule_data parsed."""
    row = await fetch_one(
        "SELECT * FROM custom_mechanics WHERE name = ?",
        (name,),
    )
    if row is None:
        return None
    return parse_row_json(row, "rule_data")


async def get_all_mechanics() -> list[dict]:
    """List all custom mechanics (summary only, no full rules)."""
    return await fetch_all(
        "SELECT id, name, category, description FROM custom_mechanics "
        "ORDER BY category, name",
    )


# ---------------------------------------------------------------------------
# Guild contracts
# ---------------------------------------------------------------------------

async def get_guild_contracts(filters: dict | None = None) -> list[dict]:
    """Return guild contracts matching optional filters.

    Supported filter keys: status, difficulty, claimed_by (character_id).
    """
    query = "SELECT * FROM guild_contracts"
    clauses: list[str] = []
    params: list = []

    if filters:
        if "status" in filters:
            clauses.append("status = ?")
            params.append(filters["status"])
        if "difficulty" in filters:
            clauses.append("difficulty = ?")
            params.append(filters["difficulty"])
        if "claimed_by" in filters:
            clauses.append("claimed_by_character_id = ?")
            params.append(filters["claimed_by"])

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY created_at DESC"
    return await fetch_all(query, tuple(params))


async def get_guild_contract(contract_id: int) -> Optional[dict]:
    """Fetch a single guild contract with poster and claimer character names."""
    return await fetch_one(
        """
        SELECT
            gc.*,
            poster.name  AS posted_by_name,
            claimer.name AS claimed_by_name
        FROM guild_contracts gc
        LEFT JOIN characters poster  ON poster.id  = gc.posted_by_character_id
        LEFT JOIN characters claimer ON claimer.id = gc.claimed_by_character_id
        WHERE gc.id = ?
        """,
        (contract_id,),
    )


async def create_guild_contract(data: dict) -> int:
    """Insert a new guild contract and return its id."""
    return await execute(
        """
        INSERT INTO guild_contracts
            (title, description, status, reward_tokens, difficulty,
             posted_by_character_id)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data["title"],
            data.get("description"),
            data.get("status", "open"),
            data.get("reward_tokens", 0),
            data.get("difficulty"),
            data.get("posted_by_character_id"),
        ),
    )


async def update_guild_contract(contract_id: int, updates: dict) -> int:
    """Update fields on a guild contract.

    Common updates: status, claimed_by_character_id, staked_tokens,
    claimed_at, completed_at.
    """
    if not updates:
        return 0

    set_clauses = [f"{k} = ?" for k in updates]
    params = list(updates.values())
    params.append(contract_id)

    return await execute(
        f"UPDATE guild_contracts SET {', '.join(set_clauses)} WHERE id = ?",
        tuple(params),
    )


# ---------------------------------------------------------------------------
# Token ledger
# ---------------------------------------------------------------------------

async def add_token_ledger_entry(
    character_id: int,
    amount: int,
    reason: str,
    contract_id: int | None = None,
    session_id: int | None = None,
) -> int:
    """Record a token transaction and update the character's balance.

    Returns the new ledger entry id.
    """
    entry_id = await execute(
        """
        INSERT INTO guild_token_ledger
            (character_id, amount, reason, contract_id, session_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (character_id, amount, reason, contract_id, session_id),
    )

    await execute(
        "UPDATE characters SET guild_tokens = guild_tokens + ? WHERE id = ?",
        (amount, character_id),
    )

    return entry_id


async def get_token_ledger(character_id: int, limit: int = 50) -> list[dict]:
    """Return the most recent ledger entries for a character."""
    return await fetch_all(
        "SELECT * FROM guild_token_ledger "
        "WHERE character_id = ? "
        "ORDER BY created_at DESC "
        "LIMIT ?",
        (character_id, limit),
    )

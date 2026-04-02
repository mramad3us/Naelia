"""Guild Token economy engine — simplified rank system."""

import json

from server.database.connection import fetch_one, fetch_all, execute


async def _load_guild_rules() -> dict:
    """Fetch guild_token_economy rules from custom_mechanics."""
    row = await fetch_one(
        "SELECT rule_data FROM custom_mechanics WHERE name = ?",
        ("guild_token_economy",),
    )
    if row is None:
        raise ValueError("guild_token_economy mechanic not found")
    return json.loads(row["rule_data"])


async def _get_character(character_id: int) -> dict:
    """Fetch a character or raise."""
    char = await fetch_one(
        "SELECT id, name, guild_rank, guild_tokens FROM characters WHERE id = ?",
        (character_id,),
    )
    if char is None:
        raise ValueError(f"Character {character_id} not found")
    return char


def _rank_for_balance(rules: dict, balance: int) -> tuple[str, dict]:
    """Determine the highest rank a balance qualifies for. Returns (rank_name, rank_data)."""
    ranks = rules["rank_thresholds"]
    current_rank = "copper"
    current_data = ranks["copper"]

    # Find the highest rank this balance qualifies for
    for rank_name, rank_data in ranks.items():
        if balance >= rank_data["gt"]:
            current_rank = rank_name
            current_data = rank_data

    return current_rank, current_data


async def get_character_rank(character_id: int) -> dict:
    """Determine a character's current guild rank based on token balance."""
    char = await _get_character(character_id)
    rules = await _load_guild_rules()

    rank_name, rank_data = _rank_for_balance(rules, char["guild_tokens"])

    # Find next rank
    next_threshold = None
    for rank, data in rules["rank_thresholds"].items():
        if data["gt"] > char["guild_tokens"]:
            if next_threshold is None or data["gt"] < next_threshold:
                next_threshold = data["gt"]

    return {
        "character_name": char["name"],
        "guild_tokens": char["guild_tokens"],
        "rank_name": rank_name,
        "rank_data": rank_data,
        "next_rank_threshold": next_threshold,
        "tokens_to_next": (next_threshold - char["guild_tokens"]) if next_threshold else 0,
    }


async def check_rank_change(character_id: int) -> dict | None:
    """Check if character's rank should change. Update if needed."""
    char = await _get_character(character_id)
    rules = await _load_guild_rules()

    new_rank, new_data = _rank_for_balance(rules, char["guild_tokens"])

    if char["guild_rank"] == new_rank:
        return None

    await execute(
        "UPDATE characters SET guild_rank = ? WHERE id = ?",
        (new_rank, character_id),
    )

    return {
        "character_name": char["name"],
        "old_rank": char["guild_rank"],
        "new_rank": new_rank,
        "guild_tokens": char["guild_tokens"],
    }


async def claim_contract(
    character_id: int, contract_id: int, session_id: int = None,
) -> dict:
    """Simplified: just mark contract as claimed."""
    char = await _get_character(character_id)
    contract = await fetch_one(
        "SELECT * FROM guild_contracts WHERE id = ?", (contract_id,),
    )
    if contract is None:
        raise ValueError(f"Contract {contract_id} not found")
    if contract["status"] != "open":
        raise ValueError(f"Contract is not open (status: {contract['status']})")

    await execute(
        "UPDATE guild_contracts SET status = 'claimed', claimed_by_character_id = ?, claimed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (character_id, contract_id),
    )

    return {
        "contract_id": contract_id,
        "claimed_by": char["name"],
        "status": "claimed",
    }


async def complete_contract(contract_id: int, session_id: int = None) -> dict:
    """Mark contract completed and award tokens."""
    contract = await fetch_one(
        "SELECT * FROM guild_contracts WHERE id = ?", (contract_id,),
    )
    if contract is None:
        raise ValueError(f"Contract {contract_id} not found")

    character_id = contract["claimed_by_character_id"]
    reward = contract["reward_tokens"]

    # Add tokens to character
    await execute(
        "UPDATE characters SET guild_tokens = guild_tokens + ? WHERE id = ?",
        (reward, character_id),
    )

    # Add ledger entry
    await execute(
        "INSERT INTO guild_token_ledger (character_id, amount, reason, contract_id, session_id) VALUES (?, ?, ?, ?, ?)",
        (character_id, reward, f"Contract completed: {contract['title']}", contract_id, session_id),
    )

    # Mark complete
    await execute(
        "UPDATE guild_contracts SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (contract_id,),
    )

    char = await _get_character(character_id)
    return {
        "contract_id": contract_id,
        "character": char["name"],
        "reward_tokens": reward,
        "new_balance": char["guild_tokens"] + reward,
    }


async def fail_contract(contract_id: int, session_id: int = None) -> dict:
    """Mark contract as failed."""
    contract = await fetch_one(
        "SELECT * FROM guild_contracts WHERE id = ?", (contract_id,),
    )
    if contract is None:
        raise ValueError(f"Contract {contract_id} not found")

    await execute(
        "UPDATE guild_contracts SET status = 'failed', completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        (contract_id,),
    )

    return {
        "contract_id": contract_id,
        "status": "failed",
    }


async def get_token_ledger(character_id: int, limit: int = 50) -> list[dict]:
    """Get transaction history for a character."""
    return await fetch_all(
        "SELECT * FROM guild_token_ledger WHERE character_id = ? ORDER BY created_at DESC LIMIT ?",
        (character_id, limit),
    )

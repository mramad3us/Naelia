"""Talent System engine — custom tier-based leveling mechanic for Naelia."""

import json

from server.database.connection import fetch_one, fetch_all, execute
from server.config import CONFIG


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_talent_rules() -> dict:
    """Fetch talent_system rules from the custom_mechanics table."""
    row = await fetch_one(
        "SELECT rule_data FROM custom_mechanics WHERE name = ?",
        ("talent_system",),
    )
    if row is None:
        raise ValueError("talent_system mechanic not found in custom_mechanics")
    return json.loads(row["rule_data"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_talent_tier(character_id: int) -> dict:
    """Return a character's talent tier with full tier details.

    Returns dict with: character_name, talent_tier, tier_name, description,
    stat_roll_bonus, max_ability_score.
    """
    char = await fetch_one(
        "SELECT name, talent_tier FROM characters WHERE id = ?",
        (character_id,),
    )
    if char is None:
        raise ValueError(f"Character with id {character_id} not found")

    rules = await _load_talent_rules()
    tier = char["talent_tier"]
    tier_info = _find_tier(rules, tier)

    return {
        "character_name": char["name"],
        "talent_tier": tier,
        "tier_name": tier_info["name"],
        "description": tier_info["description"],
        "stat_roll_bonus": rules["stat_roll_bonus"][f"tier_{tier}"],
        "max_ability_score": rules["max_ability_score"][f"tier_{tier}"],
    }


def determine_tier_from_cr(cr: float) -> int:
    """Determine which talent tier a given CR falls into.

    CR ranges: 0-0.5 -> tier 0, 1-5 -> tier 1, 6-15 -> tier 2, 16+ -> tier 3.
    """
    if cr <= 0.5:
        return 0
    if cr <= 5:
        return 1
    if cr <= 15:
        return 2
    return 3


async def get_tier_info(tier: int) -> dict:
    """Fetch full details for a specific talent tier from the mechanic rules.

    Returns the tier entry dict plus stat_roll_bonus and max_ability_score.
    """
    if tier < 0 or tier > 3:
        raise ValueError(f"Invalid tier: {tier}. Must be 0-3.")

    rules = await _load_talent_rules()
    tier_entry = _find_tier(rules, tier)

    return {
        "tier": tier,
        "name": tier_entry["name"],
        "description": tier_entry["description"],
        "cr_range": tier_entry["cr_range"],
        "population_pct": tier_entry["population_pct"],
        "stat_roll_bonus": rules["stat_roll_bonus"][f"tier_{tier}"],
        "max_ability_score": rules["max_ability_score"][f"tier_{tier}"],
    }


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _find_tier(rules: dict, tier: int) -> dict:
    """Look up a tier entry by number from the loaded rules."""
    for entry in rules["tiers"]:
        if entry["tier"] == tier:
            return entry
    raise ValueError(f"Tier {tier} not found in talent_system rules")

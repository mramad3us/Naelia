"""Intoxication mechanic — tavern drinking system for Naelia."""

import json

from server.database.connection import fetch_one


async def _load_rules() -> dict:
    """Fetch the intoxication mechanic rules from the database."""
    row = await fetch_one(
        "SELECT rule_data FROM custom_mechanics WHERE name = ?",
        ("intoxication",),
    )
    return json.loads(row["rule_data"])


async def calculate_threshold(character_id: int) -> dict:
    """Compute the intoxication threshold for a character."""
    char = await fetch_one(
        "SELECT name, race, con FROM characters WHERE id = ?",
        (character_id,),
    )
    rules = await _load_rules()

    con_mod = (char["con"] - 10) // 2
    race = char["race"] or "Human"
    racial_mod = rules["racial_modifiers"].get(race, 0)

    # threshold_formula: min(7 + racial_modifier + (con_modifier * 3), 1)
    threshold = max(1, min(7 + racial_mod + (con_mod * 3), 100))

    return {
        "base": 7,
        "con_mod": con_mod,
        "racial_mod": racial_mod,
        "threshold": threshold,
    }


async def check_intoxication(
    character_id: int, drinks_consumed: int, drink_strength: str = "Moderate"
) -> dict:
    """Determine a character's intoxication level."""
    char = await fetch_one(
        "SELECT name FROM characters WHERE id = ?",
        (character_id,),
    )
    rules = await _load_rules()
    thresh = await calculate_threshold(character_id)

    strength_mult = rules["drink_strength"].get(drink_strength, 2)
    effective_drinks = drinks_consumed * strength_mult
    ratio = effective_drinks / thresh["threshold"] if thresh["threshold"] > 0 else 0

    # Map ratio to effect level
    effect_key = "0.5x"
    if ratio < 0.5:
        effect_key = "0.5x"
    elif ratio < 0.75:
        effect_key = "0.75x"
    elif ratio < 1.0:
        effect_key = "1.0x"
    elif ratio < 1.5:
        effect_key = "1.5x"
    else:
        effect_key = "2.0x"

    effect_data = rules["effects_by_threshold"].get(effect_key, {})
    is_blackout = effect_key == "2.0x"

    return {
        "character_name": char["name"],
        "drinks_consumed": drinks_consumed,
        "drink_strength": drink_strength,
        "effective_drinks": effective_drinks,
        "threshold": thresh["threshold"],
        "ratio": round(ratio, 2),
        "effect_level": effect_key,
        "effect_data": effect_data,
        "is_blackout": is_blackout,
        "requires_save": is_blackout,
    }

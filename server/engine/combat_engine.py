"""Combat engine — initiative, action resolution, damage calculation."""

from server.engine.dice import roll, roll_expression
from server.engine.checks import attack_roll, damage_roll, get_ability_modifier
from server.database.connection import fetch_one, fetch_all
from server.models.combat import (
    start_combat,
    get_combat_state,
    get_active_combat,
    set_initiative,
    next_turn,
    update_combatant,
    end_combat,
)
import json


async def roll_initiative_for_all(encounter_id: int) -> dict:
    """Roll initiative for every combatant in an encounter."""
    state = await get_combat_state(encounter_id)
    if state is None:
        return {"error": "No encounter found"}

    initiatives = {}
    for combatant in state["combatants"]:
        char = await fetch_one(
            "SELECT dex, class_features FROM characters WHERE id = ?",
            (combatant["character_id"],),
        )
        if char is None:
            continue
        dex_mod = get_ability_modifier(char["dex"] or 10)
        result = roll(f"1d20+{dex_mod}")
        initiatives[combatant["character_id"]] = result["total"]

    await set_initiative(encounter_id, initiatives)
    return await get_combat_state(encounter_id)


async def process_attack(
    encounter_id: int,
    attacker_id: int,
    target_id: int,
    is_melee: bool = True,
    is_spell: bool = False,
    damage_expression: str = None,
    advantage: bool = False,
    disadvantage: bool = False,
    bonus: int = 0,
) -> dict:
    """Process a full attack action: roll to hit, roll damage if hit."""
    # Get target AC
    target = await fetch_one(
        "SELECT ac, name, hp_current FROM characters WHERE id = ?", (target_id,)
    )
    if target is None:
        return {"error": f"Target {target_id} not found"}

    # Roll attack
    atk = await attack_roll(
        attacker_id,
        is_melee=is_melee,
        is_spell=is_spell,
        advantage=advantage,
        disadvantage=disadvantage,
        bonus=bonus,
        target_ac=target["ac"],
    )

    result = {
        "attacker": atk["character_name"],
        "target": target["name"],
        "attack_roll": atk,
        "damage": None,
        "target_hp_before": target["hp_current"],
        "target_hp_after": target["hp_current"],
    }

    # If hit and damage expression provided, roll damage
    if atk.get("hits") and damage_expression:
        dmg = await damage_roll(damage_expression, is_critical=atk.get("is_critical", False))
        new_hp = max(0, (target["hp_current"] or 0) - dmg["total"])
        result["damage"] = dmg
        result["target_hp_after"] = new_hp

        # Update target HP in combat state and character table
        await update_combatant(encounter_id, target_id, {"hp_current": new_hp})
        from server.database.connection import execute

        await execute(
            "UPDATE characters SET hp_current = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_hp, target_id),
        )

    return result


async def process_healing(
    encounter_id: int,
    healer_id: int,
    target_id: int,
    heal_expression: str,
) -> dict:
    """Process a healing action during combat."""
    target = await fetch_one(
        "SELECT name, hp_current, hp_max FROM characters WHERE id = ?", (target_id,)
    )
    if target is None:
        return {"error": f"Target {target_id} not found"}

    heal_roll = roll(heal_expression)
    new_hp = min(target["hp_max"] or 0, (target["hp_current"] or 0) + heal_roll["total"])

    await update_combatant(encounter_id, target_id, {"hp_current": new_hp})
    from server.database.connection import execute

    await execute(
        "UPDATE characters SET hp_current = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_hp, target_id),
    )

    healer = await fetch_one("SELECT name FROM characters WHERE id = ?", (healer_id,))

    return {
        "healer": healer["name"] if healer else "Unknown",
        "target": target["name"],
        "heal_roll": heal_roll,
        "hp_before": target["hp_current"],
        "hp_after": new_hp,
        "hp_max": target["hp_max"],
    }

"""Ability check, saving throw, and attack resolution engine (D&D 5e)."""

import json
import re
from typing import Optional

from server.engine.dice import roll
from server.database.connection import fetch_one
from server.config import CONFIG


# ---------------------------------------------------------------------------
# Skill-to-ability mapping
# ---------------------------------------------------------------------------

SKILL_ABILITY_MAP: dict[str, str] = {
    "athletics": "str",
    "acrobatics": "dex",
    "sleight_of_hand": "dex",
    "stealth": "dex",
    "arcana": "int",
    "history": "int",
    "investigation": "int",
    "nature": "int",
    "religion": "int",
    "animal_handling": "wis",
    "insight": "wis",
    "medicine": "wis",
    "perception": "wis",
    "survival": "wis",
    "deception": "cha",
    "intimidation": "cha",
    "performance": "cha",
    "persuasion": "cha",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_ability_modifier(score: int) -> int:
    """Return the standard D&D 5e ability modifier for a given score."""
    return (score - 10) // 2


async def _fetch_character(character_id: int) -> dict:
    """Fetch a character row from the DB and parse its JSON fields."""
    row = await fetch_one(
        "SELECT * FROM characters WHERE id = ?", (character_id,)
    )
    if row is None:
        raise ValueError(f"Character with id {character_id} not found")

    # Parse JSON columns
    for field in ("saves_proficient", "skills", "conditions", "class_levels"):
        if row.get(field) is not None and isinstance(row[field], str):
            row[field] = json.loads(row[field])

    return row


def _resolve_skill_modifier(
    skills: dict, skill: str, ability_mod: int, proficiency_bonus: int
) -> tuple[int, bool]:
    """Return (total_modifier, uses_custom_bonus) for a given skill.

    The database stores skills in one of two formats:
      1. Custom bonus: {"Perception": {"bonus": 82}} — total modifier is the
         bonus value directly (already includes ability mod + proficiency +
         any other bonuses).  Return (bonus, True).
      2. Legacy proficiency type: {"perception": "proficient"} — compute
         ability_mod + proficiency contribution.  Return (computed, False).

    When uses_custom_bonus is True the caller must NOT add ability_mod again.
    """
    if skills is None:
        return (ability_mod, False)

    # Try case-insensitive match (DB stores "Perception", API may send "perception")
    entry = None
    for k, v in skills.items():
        if k.lower() == skill.lower():
            entry = v
            break

    if entry is None:
        return (ability_mod, False)

    # Format 1: {"bonus": N, ...}
    if isinstance(entry, dict) and "bonus" in entry:
        return (entry["bonus"], True)

    # Format 2: "proficient" / "expertise" / "half"
    if isinstance(entry, str):
        if entry == "expertise":
            return (ability_mod + proficiency_bonus * 2, False)
        if entry == "proficient":
            return (ability_mod + proficiency_bonus, False)
        if entry == "half":
            return (ability_mod + proficiency_bonus // 2, False)

    return (ability_mod, False)


def _double_dice_expression(expression: str) -> str:
    """Double the dice (not modifiers) in a dice expression for criticals.

    E.g. "2d6+3" -> "4d6+3", "1d8+1d6+5" -> "2d8+2d6+5".
    """
    def _double_match(m: re.Match) -> str:
        count = int(m.group(1)) if m.group(1) else 1
        return f"{count * 2}d{m.group(2)}"

    return re.sub(r"(\d*)d(\d+)", _double_match, expression)


# ---------------------------------------------------------------------------
# Core resolution functions
# ---------------------------------------------------------------------------

async def ability_check(
    character_id: int,
    ability: str,
    skill: Optional[str] = None,
    advantage: bool = False,
    disadvantage: bool = False,
    dc: Optional[int] = None,
) -> dict:
    """Resolve a D&D 5e ability check (optionally with a skill)."""
    char = await _fetch_character(character_id)

    ability_score = char[ability]
    ability_mod = get_ability_modifier(ability_score)

    if skill is not None:
        modifier, custom = _resolve_skill_modifier(
            char.get("skills"), skill, ability_mod, char["proficiency_bonus"]
        )
    else:
        modifier = ability_mod
        custom = False

    die_result = roll("1d20", advantage=advantage, disadvantage=disadvantage)
    natural = die_result["kept"][0] if die_result.get("kept") else die_result["total"]
    total = die_result["total"] + modifier

    # Nat 1 always fails, regardless of modifier
    if natural == 1:
        success = False
    elif dc is not None:
        success = total >= dc
    else:
        success = None

    return {
        "character_name": char["name"],
        "check_type": "ability_check",
        "ability": ability,
        "skill": skill,
        "modifier": modifier,
        "natural_roll": natural,
        "roll": die_result,
        "total": total,
        "dc": dc,
        "success": success,
    }


async def saving_throw(
    character_id: int,
    ability: str,
    advantage: bool = False,
    disadvantage: bool = False,
    dc: Optional[int] = None,
) -> dict:
    """Resolve a D&D 5e saving throw."""
    char = await _fetch_character(character_id)

    ability_score = char[ability]
    ability_mod = get_ability_modifier(ability_score)
    modifier = ability_mod

    saves_proficient = char.get("saves_proficient") or []
    if ability in saves_proficient:
        modifier += char["proficiency_bonus"]

    die_result = roll("1d20", advantage=advantage, disadvantage=disadvantage)
    total = die_result["total"] + modifier

    success: Optional[bool] = None
    if dc is not None:
        success = total >= dc

    return {
        "character_name": char["name"],
        "check_type": "saving_throw",
        "ability": ability,
        "skill": None,
        "modifier": modifier,
        "roll": die_result,
        "total": total,
        "dc": dc,
        "success": success,
    }


async def attack_roll(
    character_id: int,
    is_melee: bool = True,
    is_spell: bool = False,
    advantage: bool = False,
    disadvantage: bool = False,
    bonus: int = 0,
    target_ac: Optional[int] = None,
) -> dict:
    """Resolve a D&D 5e attack roll (melee, ranged, or spell)."""
    char = await _fetch_character(character_id)

    if is_spell:
        attack_type = "spell"
        modifier = char["spell_attack_mod"]
    elif is_melee:
        attack_type = "melee"
        str_mod = get_ability_modifier(char["str"])
        dex_mod = get_ability_modifier(char["dex"])
        # Use higher of STR/DEX for melee (accounts for finesse)
        modifier = max(str_mod, dex_mod) + char["proficiency_bonus"]
    else:
        attack_type = "ranged"
        modifier = get_ability_modifier(char["dex"]) + char["proficiency_bonus"]

    modifier += bonus

    die_result = roll("1d20", advantage=advantage, disadvantage=disadvantage)
    total = die_result["total"] + modifier

    is_critical = die_result.get("is_critical", False)

    hits: Optional[bool] = None
    if target_ac is not None:
        hits = is_critical or total >= target_ac

    return {
        "character_name": char["name"],
        "attack_type": attack_type,
        "modifier": modifier,
        "roll": die_result,
        "total": total,
        "target_ac": target_ac,
        "hits": hits,
        "is_critical": is_critical,
    }


async def damage_roll(
    expression: str,
    is_critical: bool = False,
) -> dict:
    """Roll damage. On a critical hit, double the dice (not modifiers)."""
    effective_expr = expression
    if is_critical:
        effective_expr = _double_dice_expression(expression)

    die_result = roll(effective_expr)

    return {
        "expression": effective_expr,
        "is_critical": is_critical,
        "roll": die_result,
        "total": die_result["total"],
    }

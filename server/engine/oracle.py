"""Oracle's Burden engine — Naelia's prophetic vision system."""

import json

from server.engine.dice import roll
from server.database.connection import fetch_one


def _lookup_d100(table: list[dict], value: int) -> dict:
    """Find the row where value falls between d100_min and d100_max."""
    for entry in table:
        if entry["d100_min"] <= value <= entry["d100_max"]:
            return entry
    return table[-1]


def _lookup_d20(table: list[dict], value: int) -> dict:
    """Find the row where value falls between d20_min and d20_max."""
    for entry in table:
        if entry["d20_min"] <= value <= entry["d20_max"]:
            return entry
    return table[-1]


async def roll_oracle_burden() -> dict:
    """Roll Naelia's Oracle's Burden: determine vision count and importance."""
    row = await fetch_one(
        "SELECT rule_data FROM custom_mechanics WHERE name = ?",
        ("oracle_burden",),
    )
    rules = json.loads(row["rule_data"])

    vision_result = roll("1d100")
    vision_roll = vision_result["total"]
    entry = _lookup_d100(rules["vision_count_table"], vision_roll)
    vision_count = entry["visions"]

    visions = []
    for _ in range(vision_count):
        imp_result = roll("1d20")
        imp_roll = imp_result["total"]
        imp_entry = _lookup_d20(rules["vision_importance_table"], imp_roll)
        visions.append({
            "importance_roll": imp_roll,
            "importance": imp_entry["importance"],
            "description": imp_entry.get("description", ""),
        })

    return {
        "vision_count_roll": vision_roll,
        "vision_count": vision_count,
        "visions": visions,
    }

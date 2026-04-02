"""Core dice rolling engine for D&D expressions.

Handles standard notation: NdS, NdS+M, NdSkhN, NdSklN, compound expressions.
Respects physical_dice config for tabletop play.
"""

import random
import re
from typing import Optional

from server.config import CONFIG

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

_DICE_CFG = CONFIG["dice"]
CRITICAL_HIT_RANGE: int = _DICE_CFG["critical_hit_range"]
CRITICAL_FAIL: int = _DICE_CFG["critical_fail"]
ADVANTAGE_DISADVANTAGE: bool = _DICE_CFG["advantage_disadvantage"]
PHYSICAL_DICE: bool = CONFIG["player"]["physical_dice"]

# ---------------------------------------------------------------------------
# Regex for a single dice group: "2d6kh3", "1d20", "4d6kl1", etc.
# Also matches a plain integer modifier like "+4" or "-2".
# ---------------------------------------------------------------------------

_DICE_GROUP_RE = re.compile(
    r"(?P<count>\d+)d(?P<sides>\d+)"
    r"(?:kh(?P<kh>\d+)|kl(?P<kl>\d+))?"
)
_MODIFIER_RE = re.compile(r"[+\-]\d+$")


# ---------------------------------------------------------------------------
# parse_expression
# ---------------------------------------------------------------------------

def parse_expression(expression: str) -> dict:
    """Parse a compound dice expression into structured data.

    Supports expressions like:
        "2d6+4"        -> single group with modifier
        "1d20+2d6+3"   -> two dice groups plus a flat modifier
        "4d6kh3"       -> keep-highest notation

    Returns::

        {
            "groups": [
                {"count": 2, "sides": 6, "keep_highest": None, "keep_lowest": None},
                ...
            ],
            "modifier": 4,
        }
    """
    expr = expression.lower().replace(" ", "")

    groups: list[dict] = []
    modifier = 0

    # Split the expression on +/- while keeping the delimiter.
    # We walk through tokens left-to-right.
    tokens = re.split(r"(?=[+\-])", expr)

    for token in tokens:
        token = token.strip()
        if not token:
            continue

        # Determine sign from leading +/- (default positive)
        sign = 1
        raw = token
        if raw.startswith("+"):
            raw = raw[1:]
        elif raw.startswith("-"):
            sign = -1
            raw = raw[1:]

        dice_match = _DICE_GROUP_RE.fullmatch(raw)
        if dice_match:
            count = int(dice_match.group("count"))
            sides = int(dice_match.group("sides"))
            kh = dice_match.group("kh")
            kl = dice_match.group("kl")
            groups.append({
                "count": count,
                "sides": sides,
                "keep_highest": int(kh) if kh else None,
                "keep_lowest": int(kl) if kl else None,
                "sign": sign,
            })
        elif raw.isdigit():
            modifier += sign * int(raw)
        else:
            raise ValueError(f"Unrecognised token in dice expression: '{token}'")

    return {"groups": groups, "modifier": modifier}


# ---------------------------------------------------------------------------
# Internal rolling helpers
# ---------------------------------------------------------------------------

def _roll_dice(count: int, sides: int) -> list[int]:
    """Roll *count* dice each with *sides* faces."""
    return [random.randint(1, sides) for _ in range(count)]


def _apply_keep(rolls: list[int], keep_highest: Optional[int], keep_lowest: Optional[int]) -> list[int]:
    """Return the subset of *rolls* to keep based on kh/kl rules."""
    if keep_highest is not None:
        return sorted(rolls, reverse=True)[:keep_highest]
    if keep_lowest is not None:
        return sorted(rolls)[:keep_lowest]
    return list(rolls)


# ---------------------------------------------------------------------------
# roll
# ---------------------------------------------------------------------------

def roll(
    expression: str,
    advantage: bool = False,
    disadvantage: bool = False,
) -> dict:
    """Roll a full D&D dice expression.

    Parameters
    ----------
    expression:
        A dice string such as ``"1d20+5"`` or ``"4d6kh3"``.
    advantage:
        If True, roll the d20 portion twice and keep the higher result.
    disadvantage:
        If True, roll the d20 portion twice and keep the lower result.

    Returns
    -------
    dict with keys: expression, rolls, kept, modifier, total, is_critical,
    is_fumble, advantage_used, disadvantage_used.

    If ``physical_dice`` is enabled in game config, returns a prompt dict
    instead of computed results.
    """
    # --- Physical dice mode ------------------------------------------------
    if PHYSICAL_DICE:
        return {
            "physical_dice": True,
            "expression": expression,
            "prompt": f"Roll {expression} and tell me the result",
        }

    # --- Parse -------------------------------------------------------------
    parsed = parse_expression(expression)
    groups = parsed["groups"]
    modifier = parsed["modifier"]

    # Advantage/disadvantage only allowed when the config flag is on
    use_advantage = advantage and ADVANTAGE_DISADVANTAGE
    use_disadvantage = disadvantage and ADVANTAGE_DISADVANTAGE
    # Cannot have both at once — they cancel out
    if use_advantage and use_disadvantage:
        use_advantage = False
        use_disadvantage = False

    all_rolls: list[int] = []
    all_kept: list[int] = []
    is_critical = False
    is_fumble = False
    adv_used = False
    disadv_used = False

    for group in groups:
        count = group["count"]
        sides = group["sides"]
        kh = group["keep_highest"]
        kl = group["keep_lowest"]
        sign = group["sign"]

        # --- Advantage / disadvantage on d20 rolls -------------------------
        if sides == 20 and (use_advantage or use_disadvantage):
            roll_a = _roll_dice(count, sides)
            roll_b = _roll_dice(count, sides)

            kept_a = _apply_keep(roll_a, kh, kl)
            kept_b = _apply_keep(roll_b, kh, kl)

            sum_a = sum(kept_a)
            sum_b = sum(kept_b)

            if use_advantage:
                if sum_a >= sum_b:
                    chosen_rolls, chosen_kept = roll_a, kept_a
                else:
                    chosen_rolls, chosen_kept = roll_b, kept_b
                adv_used = True
            else:
                if sum_a <= sum_b:
                    chosen_rolls, chosen_kept = roll_a, kept_a
                else:
                    chosen_rolls, chosen_kept = roll_b, kept_b
                disadv_used = True

            # Record both sets so the caller can see what happened
            all_rolls.extend(chosen_rolls)
            all_kept.extend([sign * v for v in chosen_kept])

            # Check crits on the *natural* kept d20 values
            for v in chosen_kept:
                if v >= CRITICAL_HIT_RANGE:
                    is_critical = True
                if v <= CRITICAL_FAIL:
                    is_fumble = True
        else:
            rolls = _roll_dice(count, sides)
            kept = _apply_keep(rolls, kh, kl)
            all_rolls.extend(rolls)
            all_kept.extend([sign * v for v in kept])

            # Crit/fumble checks only matter for d20s
            if sides == 20:
                for v in kept:
                    if v >= CRITICAL_HIT_RANGE:
                        is_critical = True
                    if v <= CRITICAL_FAIL:
                        is_fumble = True

    total = sum(all_kept) + modifier

    return {
        "expression": expression,
        "rolls": all_rolls,
        "kept": all_kept,
        "modifier": modifier,
        "total": total,
        "is_critical": is_critical,
        "is_fumble": is_fumble,
        "advantage_used": adv_used,
        "disadvantage_used": disadv_used,
    }


# ---------------------------------------------------------------------------
# roll_expression  (simple helper for internal engine use)
# ---------------------------------------------------------------------------

def roll_expression(expression: str) -> int:
    """Roll a dice expression and return only the integer total.

    This is a convenience wrapper used by other engine modules that just
    need a number (e.g., random encounter checks, loot tables).
    """
    result = roll(expression)
    # In physical dice mode the caller must resolve the prompt themselves.
    if result.get("physical_dice"):
        raise RuntimeError(
            "roll_expression cannot auto-resolve in physical_dice mode. "
            "Use roll() and handle the prompt."
        )
    return result["total"]

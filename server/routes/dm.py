"""DM routes — all game-facing REST endpoints called by the LLM."""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/dm", tags=["dm"])


# ---------------------------------------------------------------------------
# Request models (minimal, just for POST body parsing)
# ---------------------------------------------------------------------------

class DiceRollRequest(BaseModel):
    expression: str
    advantage: bool = False
    disadvantage: bool = False
    purpose: str = ""

class AbilityCheckRequest(BaseModel):
    ability: str
    skill: Optional[str] = None
    advantage: bool = False
    disadvantage: bool = False
    dc: Optional[int] = None

class SavingThrowRequest(BaseModel):
    ability: str
    advantage: bool = False
    disadvantage: bool = False
    dc: Optional[int] = None

class AttackRollRequest(BaseModel):
    is_melee: bool = True
    is_spell: bool = False
    advantage: bool = False
    disadvantage: bool = False
    bonus: int = 0
    target_ac: Optional[int] = None

class DamageRollRequest(BaseModel):
    expression: str
    is_critical: bool = False

class CharacterUpdateRequest(BaseModel):
    updates: dict

class MoveRequest(BaseModel):
    location_id: int

class EventLogRequest(BaseModel):
    event_type: str = "narrative"
    description: str
    characters_involved: Optional[list] = None
    location_id: Optional[int] = None

class SessionEndRequest(BaseModel):
    summary: str

class PlotCreateRequest(BaseModel):
    title: str
    description: str = ""
    priority: int = 3
    status: str = "active"

class PlotUpdateRequest(BaseModel):
    updates: dict

class ClueAddRequest(BaseModel):
    description: str

class ClueDiscoverRequest(BaseModel):
    session_id: int
    details: str = ""

class CombatStartRequest(BaseModel):
    combatant_ids: list[int]
    location_id: int
    teams: Optional[dict] = None

class CombatActionRequest(BaseModel):
    attacker_id: int
    target_id: int
    is_melee: bool = True
    is_spell: bool = False
    damage_expression: Optional[str] = None
    advantage: bool = False
    disadvantage: bool = False
    bonus: int = 0

class CombatHealRequest(BaseModel):
    healer_id: int
    target_id: int
    heal_expression: str

class CombatEndRequest(BaseModel):
    outcome: str

class IntoxicationCheckRequest(BaseModel):
    drinks_consumed: int
    drink_strength: str = "moderate"

class WorldAdvanceTimeRequest(BaseModel):
    hours: int = 0
    minutes: int = 0

class WorldSetTimeRequest(BaseModel):
    date: Optional[str] = None
    hour: Optional[int] = None
    minute: Optional[int] = None

class WorldUpdateRequest(BaseModel):
    updates: dict

class WeatherRollRequest(BaseModel):
    location_name: str

class OrgUpdateRequest(BaseModel):
    updates: dict

class ContractCreateRequest(BaseModel):
    title: str
    description: str = ""
    reward_tokens: int
    difficulty: str = "moderate"
    posted_by_character_id: Optional[int] = None

class ContractClaimRequest(BaseModel):
    character_id: int
    session_id: Optional[int] = None

class ContractUpdateRequest(BaseModel):
    updates: dict

class InitiativeRequest(BaseModel):
    initiatives: Optional[dict] = None  # None = auto-roll


# ═══════════════════════════════════════════════════════════════════════════
# WORLD STATE
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/world")
async def get_world():
    from server.models.world import get_world_state
    return await get_world_state()

@router.put("/world")
async def update_world(req: WorldUpdateRequest):
    from server.models.world import update_world_state
    await update_world_state(req.updates)
    from server.models.world import get_world_state
    return await get_world_state()

@router.post("/world/advance-time")
async def world_advance_time(req: WorldAdvanceTimeRequest):
    from server.engine.world_sim import advance_time
    return await advance_time(hours=req.hours, minutes=req.minutes)

@router.post("/world/set-time")
async def world_set_time(req: WorldSetTimeRequest):
    from server.engine.world_sim import set_time
    return await set_time(date=req.date, hour=req.hour, minute=req.minute)

@router.post("/world/weather-roll")
async def world_weather_roll(req: WeatherRollRequest):
    from server.models.world import get_world_state
    from server.engine.weather import roll_weather, update_location_weather
    ws = await get_world_state()
    result = await roll_weather(ws["season"])
    await update_location_weather(req.location_name, result, ws["current_hour"])
    return result


# ═══════════════════════════════════════════════════════════════════════════
# CHARACTERS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/characters")
async def list_characters(
    type: Optional[str] = None,
    status: Optional[str] = None,
    location_id: Optional[int] = None,
    importance: Optional[int] = None,
    name: Optional[str] = None,
    is_public: Optional[int] = None,
    org_id: Optional[int] = None,
):
    from server.models.character import get_characters
    filters = {}
    if type: filters["type"] = type
    if status: filters["status"] = status
    if location_id is not None: filters["location_id"] = location_id
    if importance is not None: filters["importance"] = importance
    if name: filters["name"] = name
    if is_public is not None: filters["is_public"] = is_public
    if org_id is not None: filters["org_id"] = org_id
    return await get_characters(filters)

@router.get("/characters/{character_id}")
async def get_character(character_id: int):
    from server.models.character import get_character
    result = await get_character(character_id)
    if result is None:
        return {"error": "Character not found"}
    return result

@router.get("/characters/{character_id}/relationships")
async def get_character_relationships(character_id: int):
    from server.models.character import get_character_relationships
    return await get_character_relationships(character_id)

@router.put("/characters/{character_id}")
async def update_character(character_id: int, req: CharacterUpdateRequest):
    from server.models.character import update_character
    await update_character(character_id, req.updates)
    from server.models.character import get_character
    return await get_character(character_id)

@router.post("/characters/{character_id}/move")
async def move_character(character_id: int, req: MoveRequest):
    from server.models.character import move_character
    await move_character(character_id, req.location_id)
    return {"moved": True, "character_id": character_id, "location_id": req.location_id}

@router.get("/characters/at-location/{location_id}")
async def characters_at_location(location_id: int):
    from server.models.character import get_characters_at_location
    return await get_characters_at_location(location_id)

@router.post("/characters/{character_id}/ability-check")
async def character_ability_check(character_id: int, req: AbilityCheckRequest):
    from server.engine.checks import ability_check
    return await ability_check(
        character_id, req.ability, skill=req.skill,
        advantage=req.advantage, disadvantage=req.disadvantage, dc=req.dc,
    )

@router.post("/characters/{character_id}/saving-throw")
async def character_saving_throw(character_id: int, req: SavingThrowRequest):
    from server.engine.checks import saving_throw
    return await saving_throw(
        character_id, req.ability,
        advantage=req.advantage, disadvantage=req.disadvantage, dc=req.dc,
    )

@router.post("/characters/{character_id}/attack")
async def character_attack(character_id: int, req: AttackRollRequest):
    from server.engine.checks import attack_roll
    return await attack_roll(
        character_id, is_melee=req.is_melee, is_spell=req.is_spell,
        advantage=req.advantage, disadvantage=req.disadvantage,
        bonus=req.bonus, target_ac=req.target_ac,
    )


# ═══════════════════════════════════════════════════════════════════════════
# ORGANIZATIONS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/organizations")
async def list_organizations(
    type: Optional[str] = None,
    parent_org_id: Optional[int] = None,
    is_secret: Optional[int] = None,
):
    from server.models.organization import get_organizations
    filters = {}
    if type: filters["type"] = type
    if parent_org_id is not None: filters["parent_org_id"] = parent_org_id
    if is_secret is not None: filters["is_secret"] = is_secret
    return await get_organizations(filters)

@router.get("/organizations/{org_id}")
async def get_organization(org_id: int):
    from server.models.organization import get_organization, get_org_members, get_org_relationships
    org = await get_organization(org_id)
    if org is None:
        return {"error": "Organization not found"}
    org["members"] = await get_org_members(org_id)
    org["relationships"] = await get_org_relationships(org_id)
    return org

@router.put("/organizations/{org_id}")
async def update_organization(org_id: int, req: OrgUpdateRequest):
    from server.models.organization import update_organization, get_organization
    await update_organization(org_id, req.updates)
    return await get_organization(org_id)


# ═══════════════════════════════════════════════════════════════════════════
# LOCATIONS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/locations")
async def list_locations(
    parent_id: Optional[int] = None,
    type: Optional[str] = None,
    name: Optional[str] = None,
    is_secret: Optional[int] = None,
):
    from server.models.location import get_locations
    filters = {}
    if parent_id is not None: filters["parent_id"] = parent_id
    if type: filters["type"] = type
    if name: filters["name"] = name
    if is_secret is not None: filters["is_secret"] = is_secret
    return await get_locations(filters)

@router.get("/locations/{location_id}")
async def get_location(location_id: int):
    from server.models.location import get_location, get_location_children, get_characters_at_location
    loc = await get_location(location_id)
    if loc is None:
        return {"error": "Location not found"}
    loc["children"] = await get_location_children(location_id)
    loc["characters_present"] = await get_characters_at_location(location_id)
    return loc

@router.get("/locations/{location_id}/path")
async def get_location_path(location_id: int):
    from server.models.location import get_location_path
    return await get_location_path(location_id)


# ═══════════════════════════════════════════════════════════════════════════
# PLOT THREADS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/plots")
async def list_plots(
    status: Optional[str] = None,
    priority: Optional[int] = None,
):
    from server.models.plot import get_plot_threads
    filters = {}
    if status: filters["status"] = status
    if priority is not None: filters["priority"] = priority
    return await get_plot_threads(filters)

@router.get("/plots/{plot_id}")
async def get_plot(plot_id: int):
    from server.models.plot import get_plot_thread
    result = await get_plot_thread(plot_id)
    if result is None:
        return {"error": "Plot thread not found"}
    return result

@router.post("/plots")
async def create_plot(req: PlotCreateRequest):
    from server.models.plot import create_plot_thread
    plot_id = await create_plot_thread({
        "title": req.title,
        "description": req.description,
        "priority": req.priority,
        "status": req.status,
    })
    from server.models.plot import get_plot_thread
    return await get_plot_thread(plot_id)

@router.put("/plots/{plot_id}")
async def update_plot(plot_id: int, req: PlotUpdateRequest):
    from server.models.plot import update_plot_thread, get_plot_thread
    await update_plot_thread(plot_id, req.updates)
    return await get_plot_thread(plot_id)

@router.post("/plots/{plot_id}/clue")
async def add_clue(plot_id: int, req: ClueAddRequest):
    from server.models.plot import add_clue
    clue_id = await add_clue(plot_id, req.description)
    return {"clue_id": clue_id, "plot_id": plot_id}

@router.put("/plots/{plot_id}/clue/{clue_id}")
async def discover_clue(plot_id: int, clue_id: int, req: ClueDiscoverRequest):
    from server.models.plot import discover_clue
    await discover_clue(clue_id, req.session_id, req.details)
    return {"discovered": True, "clue_id": clue_id}


# ═══════════════════════════════════════════════════════════════════════════
# DICE & MECHANICS
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/dice/roll")
async def dice_roll(req: DiceRollRequest):
    from server.engine.dice import roll
    result = roll(req.expression, advantage=req.advantage, disadvantage=req.disadvantage)
    result["purpose"] = req.purpose
    return result

@router.post("/dice/damage")
async def dice_damage(req: DamageRollRequest):
    from server.engine.checks import damage_roll
    return await damage_roll(req.expression, is_critical=req.is_critical)

@router.post("/dice/oracle-burden")
async def dice_oracle_burden():
    from server.engine.oracle import roll_oracle_burden
    return await roll_oracle_burden()

@router.post("/dice/intoxication-check/{character_id}")
async def dice_intoxication(character_id: int, req: IntoxicationCheckRequest):
    from server.engine.intoxication import check_intoxication
    return await check_intoxication(character_id, req.drinks_consumed, req.drink_strength)

@router.post("/dice/weather")
async def dice_weather(season: str = None):
    from server.engine.weather import roll_weather
    from server.models.world import get_world_state
    if season is None:
        ws = await get_world_state()
        season = ws["season"]
    return await roll_weather(season)

@router.get("/mechanics/{name}")
async def get_mechanic(name: str):
    from server.models.mechanics import get_mechanic
    result = await get_mechanic(name)
    if result is None:
        return {"error": f"Mechanic '{name}' not found"}
    return result

@router.get("/mechanics")
async def list_mechanics():
    from server.models.mechanics import get_all_mechanics
    return await get_all_mechanics()


# ═══════════════════════════════════════════════════════════════════════════
# SESSION MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/session/start")
async def session_start():
    from server.models.session import start_session
    return await start_session()

@router.post("/session/end")
async def session_end(req: SessionEndRequest):
    from server.models.session import end_session
    return await end_session(req.summary)

@router.get("/session/current")
async def session_current():
    from server.models.session import get_current_session
    result = await get_current_session()
    if result is None:
        return {"error": "No active session"}
    return result

@router.get("/session/history")
async def session_history(limit: int = 20):
    from server.models.session import get_session_history
    return await get_session_history(limit)

@router.post("/session/event")
async def session_event(req: EventLogRequest):
    from server.models.session import get_current_session, log_event
    session = await get_current_session()
    if session is None:
        return {"error": "No active session"}
    event_id = await log_event(
        session["id"], req.event_type, req.description,
        characters_involved=req.characters_involved,
        location_id=req.location_id,
    )
    return {"event_id": event_id}


# ═══════════════════════════════════════════════════════════════════════════
# COMBAT
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/combat/start")
async def combat_start(req: CombatStartRequest):
    from server.models.session import get_current_session
    from server.models.combat import start_combat
    session = await get_current_session()
    session_id = session["id"] if session else None
    encounter_id = await start_combat(session_id, req.location_id, req.combatant_ids, req.teams)
    from server.models.combat import get_combat_state
    return await get_combat_state(encounter_id)

@router.post("/combat/initiative")
async def combat_initiative(req: InitiativeRequest = None):
    from server.models.combat import get_active_combat
    combat = await get_active_combat()
    if combat is None:
        return {"error": "No active combat"}
    if req and req.initiatives:
        from server.models.combat import set_initiative
        await set_initiative(combat["id"], req.initiatives)
        from server.models.combat import get_combat_state
        return await get_combat_state(combat["id"])
    else:
        from server.engine.combat_engine import roll_initiative_for_all
        return await roll_initiative_for_all(combat["id"])

@router.post("/combat/action")
async def combat_action(req: CombatActionRequest):
    from server.models.combat import get_active_combat
    combat = await get_active_combat()
    if combat is None:
        return {"error": "No active combat"}
    from server.engine.combat_engine import process_attack
    return await process_attack(
        combat["id"], req.attacker_id, req.target_id,
        is_melee=req.is_melee, is_spell=req.is_spell,
        damage_expression=req.damage_expression,
        advantage=req.advantage, disadvantage=req.disadvantage,
        bonus=req.bonus,
    )

@router.post("/combat/heal")
async def combat_heal(req: CombatHealRequest):
    from server.models.combat import get_active_combat
    combat = await get_active_combat()
    if combat is None:
        return {"error": "No active combat"}
    from server.engine.combat_engine import process_healing
    return await process_healing(combat["id"], req.healer_id, req.target_id, req.heal_expression)

@router.post("/combat/next-turn")
async def combat_next_turn():
    from server.models.combat import get_active_combat, next_turn
    combat = await get_active_combat()
    if combat is None:
        return {"error": "No active combat"}
    return await next_turn(combat["id"])

@router.get("/combat/state")
async def combat_state():
    from server.models.combat import get_active_combat
    result = await get_active_combat()
    if result is None:
        return {"error": "No active combat"}
    return result

@router.post("/combat/end")
async def combat_end(req: CombatEndRequest):
    from server.models.combat import get_active_combat, end_combat
    combat = await get_active_combat()
    if combat is None:
        return {"error": "No active combat"}
    await end_combat(combat["id"], req.outcome)
    return {"ended": True, "outcome": req.outcome}


# ═══════════════════════════════════════════════════════════════════════════
# GUILD TOKENS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/guild/contracts")
async def list_guild_contracts(
    status: Optional[str] = None,
    difficulty: Optional[str] = None,
):
    from server.models.mechanics import get_guild_contracts
    filters = {}
    if status: filters["status"] = status
    if difficulty: filters["difficulty"] = difficulty
    return await get_guild_contracts(filters)

@router.get("/guild/contracts/{contract_id}")
async def get_guild_contract(contract_id: int):
    from server.models.mechanics import get_guild_contract
    return await get_guild_contract(contract_id)

@router.post("/guild/contracts")
async def create_guild_contract(req: ContractCreateRequest):
    from server.models.mechanics import create_guild_contract
    contract_id = await create_guild_contract({
        "title": req.title,
        "description": req.description,
        "reward_tokens": req.reward_tokens,
        "difficulty": req.difficulty,
        "posted_by_character_id": req.posted_by_character_id,
    })
    from server.models.mechanics import get_guild_contract
    return await get_guild_contract(contract_id)

@router.post("/guild/contracts/{contract_id}/claim")
async def claim_guild_contract(contract_id: int, req: ContractClaimRequest):
    from server.engine.guild_tokens import claim_contract
    return await claim_contract(req.character_id, contract_id, req.session_id)

@router.post("/guild/contracts/{contract_id}/complete")
async def complete_guild_contract(contract_id: int, session_id: Optional[int] = None):
    from server.engine.guild_tokens import complete_contract
    return await complete_contract(contract_id, session_id)

@router.post("/guild/contracts/{contract_id}/fail")
async def fail_guild_contract(contract_id: int, session_id: Optional[int] = None):
    from server.engine.guild_tokens import fail_contract
    return await fail_contract(contract_id, session_id)

@router.get("/guild/rank/{character_id}")
async def get_guild_rank(character_id: int):
    from server.engine.guild_tokens import get_character_rank
    return await get_character_rank(character_id)

@router.get("/guild/ledger/{character_id}")
async def get_guild_ledger(character_id: int, limit: int = 50):
    from server.models.mechanics import get_token_ledger
    return await get_token_ledger(character_id, limit)

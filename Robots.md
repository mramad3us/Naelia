# Robots.md: Naelia's Chronicles DM Operator Manual

> **Purpose**: Comprehensive reference for AI agents operating as Dungeon Master via REST API. This document is written for LLM agents; complexity and technical depth are intentional.

---

## TABLE OF CONTENTS

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Server Architecture](#server-architecture)
4. [Character System](#character-system)
5. [Organization System](#organization-system)
6. [Location System](#location-system)
7. [World State & Time](#world-state--time)
8. [Plot Threads](#plot-threads)
9. [Session Management](#session-management)
10. [Dice & Mechanics](#dice--mechanics)
11. [Combat System](#combat-system)
12. [Guild Token Economy](#guild-token-economy)
13. [Archival & Backup](#archival--backup)
14. [REST API Reference](#rest-api-reference)
15. [Mechanics Deep Dives](#mechanics-deep-dives)
16. [NPC Personalities](#npc-personalities)

---

## OVERVIEW

**Naelia's Chronicles** is a living, persistent D&D campaign world operated by an LLM agent as Dungeon Master. The system provides:

- **SQLite backend** containing 80+ characters, 25 organizations, 68 locations, 7 plot threads
- **REST API** (FastAPI, port 8000) with 100+ endpoints for all game operations
- **Game configuration** in `game_config.json` (modifiable settings: dice toggle, archival frequency, backup locations)
- **No browser UI**: Claude Code terminal is the exclusive DM interface
- **Persistent world**: Date/time advancement, NPC schedules, weather simulation, background events
- **Mechanically rich**: 6 custom homebrew systems integrated into core gameplay

### Core Design Principles

1. **State is Truth**: The SQLite database is the authoritative game state. All decisions are persisted immediately.
2. **JSON-Serialized Flexibility**: Complex data (spells, features, relationships) stored as JSON for extensibility without schema changes.
3. **Secret Information**: Fields marked `is_secret` or `is_public` allow LLM to query player-facing vs. hidden information separately.
4. **Stateless API**: Every request is independent; maintain game state within the DB, not in memory.
5. **Narrative-First**: Engine mechanics serve story, never constrain it. Naelia can break rules when dramatically appropriate.

### Key Assumptions

- **LLM operator is competent**: Assumes the agent understands D&D rules, Baldur's Gate lore, and dramatic pacing.
- **Determinism when needed**: `physical_dice: false` in config means the LLM rolls synthetically. Set `true` to ask for manual rolls from a physical player.
- **Archival is automatic**: Every 10 sessions (configurable), old session data compresses into era summaries; keep campaigns fresh without losing history.

---

## QUICK START

### 1. Verify Server is Running

```bash
curl http://127.0.0.1:8000/health
# Expected response:
# {
#   "status": "ok",
#   "campaign": "Naelia's Chronicles",
#   "version": "0.1.0"
# }
```

### 2. Check Current Game State

```bash
curl http://127.0.0.1:8000/dm/world
# Returns: current date (1525-01-01), hour (8), season (winter), active session ID, political summary
```

### 3. Start a Session

```bash
curl -X POST http://127.0.0.1:8000/dm/session/start
# Returns: session number, start time, in-game date. Updates world_state.active_session_id.
```

### 4. Make a Game Decision

Example: Naelia casts a spell and needs a check.

```bash
curl -X POST http://127.0.0.1:8000/dm/characters/1/ability-check \
  -H "Content-Type: application/json" \
  -d '{
    "ability": "int",
    "skill": "arcana",
    "dc": 18
  }'
# Returns: roll result, modifiers applied, success/fail vs DC
```

### 5. Log the Narrative

```bash
curl -X POST http://127.0.0.1:8000/dm/session/event \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "narrative",
    "description": "Naelia gestures toward the summoning circle. Arcane energy crackles as she binds the planar rift.",
    "characters_involved": [1],
    "location_id": 220
  }'
# Records the narrative moment in session history for later reference/archival
```

### 6. Advance Time

```bash
curl -X POST http://127.0.0.1:8000/dm/world/advance-time \
  -H "Content-Type: application/json" \
  -d '{"hours": 4}'
# Updates in-game date/hour, triggers NPC schedule checks, weather transitions, background events
```

### 7. End Session

```bash
curl -X POST http://127.0.0.1:8000/dm/session/end \
  -H "Content-Type: application/json" \
  -d '{"summary": "The party infiltrated Bloomridge Tower, discovered the secret correspondence, and narrowly escaped Watch pursuit."}'
# Closes session, captures in-game end date, clears active_session_id
```

---

## SERVER ARCHITECTURE

### File Structure

```
/Users/deaumas/lab/dnd/Claude/Naelia Chronicles/
├── game_config.json                      # Game settings (editable)
├── server/
│   ├── main.py                           # FastAPI app entry point
│   ├── config.py                         # Config loader
│   ├── requirements.txt                  # Python dependencies
│   ├── database/
│   │   ├── schema.sql                    # DDL for 24 tables
│   │   ├── seed.py                       # Initial data population
│   │   ├── connection.py                 # Async DB helpers
│   │   └── backup.py                     # Backup/restore logic
│   ├── models/                           # Query layers (async)
│   │   ├── character.py                  # Character queries
│   │   ├── organization.py               # Org queries
│   │   ├── location.py                   # Location queries
│   │   ├── world.py                      # World state queries
│   │   ├── plot.py                       # Plot thread queries
│   │   ├── session.py                    # Session & event queries
│   │   ├── mechanics.py                  # Mechanics & guild contract queries
│   │   └── combat.py                     # Combat state queries
│   ├── engine/                           # Business logic (async)
│   │   ├── dice.py                       # D&D dice engine
│   │   ├── checks.py                     # Ability checks, saves, attacks
│   │   ├── combat_engine.py              # Attack resolution, damage, healing
│   │   ├── weather.py                    # Seasonal weather rolls
│   │   ├── oracle.py                     # Oracle's Burden visions
│   │   ├── intoxication.py               # Tavern drinking system
│   │   ├── talent.py                     # Talent tier system
│   │   ├── guild_tokens.py               # Guild rank & contracts
│   │   └── world_sim.py                  # Time advancement, NPC schedules, events
│   └── routes/                           # HTTP endpoints
│       ├── dm.py                         # All game-facing endpoints (100+)
│       └── admin.py                      # Backup, restore, archival, stats
├── server/world.db                       # SQLite database (live, git-ignored)
└── backups/                              # Timestamped backup files
```

### Database Schema (24 Tables)

**Core Entities:**
- `characters` (75 rows): PCs, NPCs, full stat blocks, relationships, inventory
- `organizations` (25 rows): Guilds, cults, councils; self-referencing hierarchy
- `locations` (68 rows): Planes → rooms; hierarchical, secret flags for hidden places
- `items` (8 rows): Equipment with attunement, curses, magical effects

**Relationships:**
- `character_relationships` (41 rows): Directed edges (Naelia→Seraphine, sentiment -10 to +10)
- `org_memberships` (78 rows): Character→Org with role, rank, join date
- `org_relationships` (12 rows): Org→Org (allied, rival, infiltrated, etc.)

**World:**
- `world_state` (singleton): Current date, hour, season, active session, political summary, weather by location
- `world_history` (13 rows): Timeline events (560 DR to 1521 DR)
- `weather_tables` (31 rows): Seasonal d100 rolls → weather type + combat effects
- `npc_schedules` (7 rows): Daily routines by day-of-tenday

**Gameplay:**
- `sessions` (auto-growing): Session number, real-time, in-game date range, summary, archived flag
- `session_events` (auto-growing): Narrative moments, combat actions, discoveries, logs
- `dice_rolls` (auto-growing, pruned): Every roll recorded with expression, result, purpose
- `combat_encounters` (active + completed): Initiative order, combatants, round count, outcome

**Mechanics:**
- `plot_threads` (7 rows): Active/dormant/resolved status, priority, characters involved
- `plot_clues` (4 rows): Discovered flag, discovery details
- `plot_characters` (join table): Which NPCs are suspects/victims/investigators
- `custom_mechanics` (4 rows): JSON-serialized rule systems (Oracle, Intoxication, Talent, Guild Tokens)
- `guild_contracts` (1+ rows): Open/claimed/completed contracts with reward, stake, claimer
- `guild_token_ledger` (auto-growing): Transaction history (claim stake, award reward, forfeit)
- `era_summaries` (auto-growing): Compressed session batches every 10 sessions
- `schema_version` (1 row): Schema tracking

**Admin:**
- `backups` (auto-growing): Timestamped backup records
- `character_snapshots` (era boundaries): Full character state at era boundaries for reconstruction

### Configuration (game_config.json)

```json
{
  "game": {
    "campaign_name": "Naelia's Chronicles",
    "starting_date_dr": "1525-01-01",        // First recorded date
    "starting_hour": 8,
    "starting_season": "winter",
    "starting_location": "Baldur's Gate"
  },
  "player": {
    "physical_dice": false,                  // false = synthetic rolls, true = ask for manual
    "player_character": "Naelia An'Ohren"    // Primary PC
  },
  "dice": {
    "critical_hit_range": 20,                // Natural 20+ is crit
    "critical_fail": 1,                      // Natural 1 is fumble
    "advantage_disadvantage": true           // d20 roll-twice rules
  },
  "world_simulation": {
    "weather_roll_interval_hours": 4,
    "npc_schedule_enabled": true,
    "background_events_enabled": true
  },
  "session": {
    "auto_log_events": true,
    "archival_trigger_sessions": 10,         // Compress every 10 sessions
    "max_dice_rolls_kept": 500,              // Prune older rolls
    "era_summary_min_words": 500
  },
  "backup": {
    "auto_backup_on_game_day_change": true,
    "backup_directory": "backups",
    "max_backups_kept": 100
  },
  "server": {
    "host": "127.0.0.1",
    "port": 8000
  },
  "narrative": {
    "tone": "dark political intrigue with moments of wonder",
    "detail_level": "high",
    "combat_narration": true
  }
}
```

---

## CHARACTER SYSTEM

### Naelia An'Ohren (PC, CR 100)

**Identity:**
- Eladrin celestial, age 2628, Chaotic Neutral
- Aliases: Avatar of the Lady, Silver Queen, Mithral Queen
- Background: Divine being descended into Toril

**Stats (6 values):**
- STR 13, DEX 56, CON 53, INT 67, WIS 70, CHA 70
- HP: 2550/2550, AC 55, Speed: 30 ft., 220 ft. fly, 90 ft. swim
- Proficiency: +26
- Talent Tier: 3 (Legendary)

**Abilities:**
```json
"legendary_actions": [
  "Arcane Bolt: +50 to hit, 7d12+24 damage",
  "Dimension Door: Teleport up to 500 ft.",
  "Legendary Resistance (3/day): Reroll failed save"
],
"lair_actions": [
  "The fabric of reality ripples in a 60 ft. radius",
  "Ambient magic flares, all creatures in area make DC 68 DEX save or take 44 psychic damage"
],
"class_features": {
  "Spellcasting": "Innate, DC 68",
  "Legendary Resistance": "3/day, reroll failed save"
}
```

**Magic:**
- Spells Known: 40+ spells ranging from Cantrips to 9th level (Wish, True Polymorph, Tsunami, etc.)
- Innate Spells: Prestidigitation at will, Divine Favor 3/day
- Spell Slots: Effectively unlimited (treat as always prepared)

**Relationships:**
- Seraphine: +10 (Closest ally, "if you need something, ask")
- Council of Four (collectively): +7 (Respect/caution, formal relationships)
- Blue Dagger: +5 (Useful asset, not fully trusted)
- Ravenshade family: +8 (Protected patroness)

**Location:**
- Primary: Upper City, Manorborn district (Ravenshade manor)
- Current: Material Plane, Toril, Sword Coast, Baldur's Gate, Upper City

**Guild Status:**
- Tokens: 0 (transcends mortal currency)
- Rank: "Avatar" (custom, non-standard)

---

### Seraphine (PC, CR 35)

**Identity:**
- Archfey, ancient being, Chaotic Neutral
- Founder & secret ruler of Gilded Gauntlet (role: "Arthenia, Lady of the Guild")
- Diplomatic facade, ruthless in shadows

**Stats:**
- STR 8, DEX 20, CON 18, INT 19, WIS 18, CHA 21
- HP: 622/622, AC 19, Speed: 30 ft., 60 ft. fly
- Proficiency: +8
- Talent Tier: 2 (Exceptional)

**Abilities:**
- Fey Magic: Cantrips (Mage Hand, Minor Illusion, Prestidigitation) at will
- Dimensional Gateway: Once per long rest, plane shift for herself + 5 willing creatures
- Glamor (20 ft. radius): Advantage on CHA checks, creatures have disadvantage on WIS (Perception)

**Relationships:**
- Naelia: +10 (symbiotic partnership, "together we reshape the coast")
- Ravenshade, Caldwell, Redlocks: +6 each (Political allies)
- Blue Dagger: +4 (Useful but suspicious)

**Location:**
- Primary: Bloomridge Tower, Lower City guildhall (hidden chambers below)
- Maintains formal residence in Manorborn for patrician meetings

**Guild Status:**
- Tokens: 47,000 (accumulated over centuries)
- Rank: Platinum (the highest)

---

### Critical NPCs (Sampling)

**Jade Ravenshade** (CR 8, Grand Duchess)
- Role: Political leader, Naelia's patroness
- Relationships: Naelia +8 (protected), Seraphine +6 (useful partner), Council +5 (rival politics)
- Location: Manorborn, Ravenshade estate (id 301)
- Secrets: Recently poisoned two rivals, covered up by Watch
- Schedule: Day 1-3: Estate, Day 4-10: Parliament

**Olivia Caldwell** (CR 7, Duchess)
- Role: Trade representative, merchant network
- Relationships: Ravenshade +2 (tense), Redlocks -1 (threatened), Naelia +5 (patronage seeker)
- Location: Gray Harbor, Caldwell Mansion (id 302)
- Secrets: Smuggling Calishite goods through Gray Harbor; Blue Dagger contact
- Schedule: Always at Harbor district during business hours (6-18)

**Oriel Redlocks** (CR 9, Duke)
- Role: Military commander, Watch liaison
- Relationships: Ravenshade +3, Caldwell -1, Vammas -2 (council tensions)
- Location: Upper City, Watch Citadel (id 310)
- Secrets: Bribed by Blue Dagger; leaks patrol routes
- Schedule: Citadel every hour (on-duty cycle)

**Phillipe-Michael Vammas** (CR 6, Duke)
- Role: Diplomat, trade negotiations
- Relationships: Ravenshade +1, Caldwell +3, Redlocks -2
- Location: Manorborn, Council chamber (id 311) or traveling
- Secrets: Embezzling council funds for personal property
- Schedule: Council meetings Days 5-10; travels Days 1-4

---

### Character Model Operations

**Fetch Character:**
```bash
curl http://127.0.0.1:8000/dm/characters/1
# Returns: Full sheet (stats, spells, features, relationships, inventory, guild status)
```

**Query Characters:**
```bash
curl "http://127.0.0.1:8000/dm/characters?type=pc"              # PCs only
curl "http://127.0.0.1:8000/dm/characters?status=alive"         # Living characters
curl "http://127.0.0.1:8000/dm/characters?location_id=220"      # At Bloomridge
curl "http://127.0.0.1:8000/dm/characters?importance=1"         # Critical NPCs (importance 1-5)
curl "http://127.0.0.1:8000/dm/characters?is_public=1"          # Player-facing info only
curl "http://127.0.0.1:8000/dm/characters?org_id=1"             # Gilded Gauntlet members
```

**Get Relationships:**
```bash
curl http://127.0.0.1:8000/dm/characters/1/relationships
# Returns: List of outbound relationships (Naelia→everyone) with sentiment, description
```

**Update Character:**
```bash
curl -X PUT http://127.0.0.1:8000/dm/characters/1 \
  -H "Content-Type: application/json" \
  -d '{
    "updates": {
      "hp_current": 2400,
      "conditions": ["petrified"],
      "status": "imprisoned"
    }
  }'
```

**Move Character:**
```bash
curl -X POST http://127.0.0.1:8000/dm/characters/1/move \
  -H "Content-Type: application/json" \
  -d '{"location_id": 240}'  # Move Naelia to The Mudway (Undercity)
```

**Characters at Location:**
```bash
curl http://127.0.0.1:8000/dm/characters/at-location/220
# Returns: All characters currently at Bloomridge
```

---

## ORGANIZATION SYSTEM

### Gilded Gauntlet (Org 1)

**Profile:**
- Type: Guild (adventurer's guild + holy order hybrid)
- Headquarters: Bloomridge Tower (id 300)
- Members: 8,000+ registered, 17 Gold-ranked
- Hidden Ruler: Seraphine ("Arthenia, Lady of the Guild")

**Sub-Organizations (Hierarchy):**

```
Gilded Gauntlet (root)
├── Golden Pixies (107 members, female healers, bronze+)
├── Bronzehands (92 members, smiths/crafters)
├── Brightfire Company (16 members, gold-ranked heavy combat)
├── Oaken Wardens (34 members, druids/rangers, green)
├── Crimson Artificers (8 members, arcane specialists)
├── Shadowsteel Cadre (23 members, silver-ranked assassins, secret)
└── Ravenshade Investigation (2 members, Naelia + deputy)
```

**Member Types & Ranks:**
- Copper (0-99 tokens): Probationary
- Brass (100-9,999 tokens): Active member
- Bronze (10K-99K tokens): Leader rank
- Silver (100K-999K tokens): Veteran
- Gold (1M+ tokens): Master
- Platinum (100M+ tokens): Council

### Blue Dagger (Org 2)

**Profile:**
- Type: Criminal syndicate
- Headquarters: The Undercity, Silver Quarter (id 240)
- Leader: "The Fang" (mysterious, identity protected)
- Operations: Smuggling, assassination, blackmail, intelligence

**Control Strategies:**
- Infiltrates Watch, Parliament, Flaming Fist
- Employs "freelance" assassins (not directly listed as members)
- Operates hidden market in Silver Quarter
- Blackmail network against Patrician class

**Relationships:**
- Gilded Gauntlet: +4 (Professional, not enemies)
- Council of Four: +2 (Careful distance, occasional partnership)
- Naelia: +3 (Respectful fear; doesn't interfere with her agenda)
- Watch: -6 (Official enemies, but informants within)

---

### Organization Model Operations

**List Organizations:**
```bash
curl "http://127.0.0.1:8000/dm/organizations?type=guild"        # All guilds
curl "http://127.0.0.1:8000/dm/organizations?parent_org_id=1"   # Gauntlet sub-orgs
curl "http://127.0.0.1:8000/dm/organizations?is_secret=1"       # Hidden organizations
```

**Fetch Organization:**
```bash
curl http://127.0.0.1:8000/dm/organizations/1
# Returns: Org details + members (name, role, rank) + relationships (allies, enemies, infiltrations)
```

**Update Organization:**
```bash
curl -X PUT http://127.0.0.1:8000/dm/organizations/1 \
  -H "Content-Type: application/json" \
  -d '{
    "updates": {
      "political_summary": "Seraphine consolidates Platinum ranks; Blue Dagger grows bolder"
    }
  }'
```

---

## LOCATION SYSTEM

### World Hierarchy

All locations follow a strict parent-child hierarchy:

```
Material Plane (id 1)
└── Toril (id 10)
    └── Faerun (id 20)
        └── Sword Coast (id 30)
            └── Baldur's Gate (id 100) ⭐ PRIMARY CAMPAIGN CITY
                ├── Upper City (id 200)
                │   ├── Citadel Streets (210)
                │   ├── Manorborn (211)      # Patrician residences
                │   ├── Temples (212)         # Grand cathedrals
                │   └── The Wide (213)        # Main marketplace
                ├── Lower City (id 201)
                │   ├── Bloomridge (220)      # Gilded Gauntlet HQ ⭐
                │   ├── Brampton (221)
                │   ├── Eastway (222)
                │   ├── Heapside (223)
                │   ├── Seatower (224)
                │   ├── The Steeps (225)
                │   ├── Gray Harbor (226)     # Port district
                │   └── Wyrm's Crossing (239) # Bridge
                ├── Outer City (id 202)
                │   ├── Blackgate (230)
                │   ├── Little Calimshan (231)
                │   ├── Norchapel (232)
                │   ├── Rivington (233)       # Smuggling haven
                │   ├── Sow's Foot (234)
                │   ├── Stonyeyes (235)
                │   ├── Tumbledown (236)
                │   ├── Twin Songs (237)
                │   ├── Whitkeep (238)
                │   └── Wyrm's Crossing (239)
                └── Undercity (id 203)
                    ├── Silver Quarter (240)   # Blue Dagger base
                    ├── The Mudway (241)
                    ├── The Underriver (242)
                    ├── Mudbrook (243)
                    └── The Lost Quarter (244)

Plus extraplanar locations:
- Shadowfell (id 50)
- Feywild (id 51)
- Astral Plane (id 52)
- Abyss (id 53)
```

### Key Locations (Details)

**Bloomridge Tower (id 220) - Gilded Gauntlet Headquarters**
- Type: District + Major Building
- Architecture: Upscale boutiques, rooftop gardens, 7-story guildhouse
- Security: Ward glyphs (Seraphine), Platinum-rank guards
- Hidden Areas:
  - Basement level 1: Treasury vault (50M+ GP)
  - Basement level 2: Meeting chamber, scrying pool
  - Sub-basement (secret): Planar gateway (Seraphine's pocket dimension access)
- NPCs:
  - Arthenia (Seraphine, always present or delegates)
  - Master of Coin (manages treasury)
  - Quartermaster (supplies, contracts)

**Manorborn (id 211) - Patrician Estates**
- Type: District
- Residents:
  - Ravenshade Estate (301): Jade + household, 20+ guards
  - Caldwell Mansion (302): Olivia, mercantile staff
  - Redlocks Compound (303): Military barracks
  - Vammas Townhouse (304): Diplomatic chambers
- Atmosphere: Wealth, privilege, power games
- Secret: Assassination plots constantly simmering

**The Undercity / Silver Quarter (id 240) - Blue Dagger Base**
- Type: District (underground)
- Access: From Mudway, The Underriver, secret entrances scattered throughout Lower City
- Features:
  - Clean, dry tunnels (well-maintained by Dagger)
  - Clandestine market (fenced goods, rare items, assassin contracts)
  - Hideouts (multiple safehouses)
  - Intelligence hub
- Security: Blue Dagger operatives, traps, secret doors
- Rumors: Dagger plans expansion deeper into Undercity; relationship with Naelia unclear

---

### Location Model Operations

**List Locations:**
```bash
curl "http://127.0.0.1:8000/dm/locations?type=city"             # All cities
curl "http://127.0.0.1:8000/dm/locations?parent_id=100"         # Baldur's Gate districts
curl "http://127.0.0.1:8000/dm/locations?name=%Bloomridge%"     # Search by name
curl "http://127.0.0.1:8000/dm/locations?is_secret=1"           # Hidden locations
```

**Fetch Location:**
```bash
curl http://127.0.0.1:8000/dm/locations/220
# Returns: Name, parent, type, description, children (sub-districts), characters present, encounters
```

**Get Location Path (Hierarchy):**
```bash
curl http://127.0.0.1:8000/dm/locations/220/path
# Returns: [Material Plane, Toril, Faerun, Sword Coast, Baldur's Gate, Lower City, Bloomridge]
```

**Characters at Location:**
```bash
curl http://127.0.0.1:8000/dm/characters/at-location/220
# Returns: All creatures currently at Bloomridge (Seraphine, guards, visiting guild members)
```

---

## WORLD STATE & TIME

### Current State

```json
{
  "current_date": "1525-01-02",      // Year-Month-Day (DR = Dalereckoning)
  "current_hour": 8,
  "current_minute": 0,
  "season": "winter",                // winter, spring, summer, autumn
  "weather_by_location": {           // JSON object mapping location names to weather
    "Baldur's Gate": {
      "type": "Clear Skies",
      "description": "No modifiers",
      "since_hour": 8                // Last changed at hour 8
    }
  },
  "active_session_id": 1,            // NULL when no session running
  "political_summary": "Baldur's Gate is governed by the Council of Four..."
}
```

### Time Advancement

**Calendar:**
- Year: 1525 DR (Dalereckoning)
- Month: 12 months, 30 days each
- Tenday: 10-day cycle within each month (used for NPC schedules)
- Hour: 0-23 (midnight to 11 PM)

**Seasonal Effects:**
- Winter (months 12, 1, 2): Cold, snow possible, shorter days
- Spring (3, 4, 5): Thaw, rain, mud
- Summer (6, 7, 8): Heat, clear skies, travel season
- Autumn (9, 10, 11): Harvest, cooling, preparation

### Weather System

**Roll Weather (Any Location, Any Time):**
```bash
curl -X POST http://127.0.0.1:8000/dm/dice/weather \
  -H "Content-Type: application/json" \
  -d '{"location_name": "Baldur'\''s Gate"}'  # Optional, uses current season
# Returns: d100 roll, matching weather type, combat effects
```

**Weather Types (Examples):**
- Clear Skies: No modifiers
- Light Rain: Difficult terrain, visibility 60 ft.
- Heavy Snow: Difficult terrain, visibility 30 ft., extreme cold damage
- Fog Bank: Visibility 15 ft., disadvantage on Perception
- Thunderstorm: Lightning strikes (periodic CON saves), wind effects

**NPC Schedules Trigger Every 4 Hours:**
When you advance time by 4+ hours, the system checks `npc_schedules` table:
- Matches current hour and day-of-tenday
- Moves NPCs to scheduled locations
- Returns list of schedule activations

### World State Operations

**Get Current State:**
```bash
curl http://127.0.0.1:8000/dm/world
```

**Advance Time:**
```bash
curl -X POST http://127.0.0.1:8000/dm/world/advance-time \
  -H "Content-Type: application/json" \
  -d '{"hours": 8, "minutes": 30}'
# Triggers: NPC schedules, weather checks, session event logging
```

**Jump to Specific Time:**
```bash
curl -X POST http://127.0.0.1:8000/dm/world/set-time \
  -H "Content-Type: application/json" \
  -d '{
    "date": "1525-01-05",
    "hour": 14,
    "minute": 0
  }'
# Useful for "time skip" narrative moments (one week later, etc.)
```

**Update Political Summary:**
```bash
curl -X PUT http://127.0.0.1:8000/dm/world \
  -H "Content-Type: application/json" \
  -d '{
    "updates": {
      "political_summary": "The assassination of Caldwell's merchant rival has shifted power. Blue Dagger grows bolder."
    }
  }'
```

---

## PLOT THREADS

### Active Plots

**1. The Ravenshade Murders** (Priority 1, Status: ACTIVE)
- Description: Yuuto Ravenshade and wife Sibyll assassinated in 1509 by unknown forces
- Active Contract: Gold-rank Gauntlet contract, 1,000,000 GP reward
- Suspects: Third Lotus monk-assassins (rumor), rival house members, Blue Dagger?
- Clues:
  - [Undiscovered] Scorched letter fragment found at scene
  - [Undiscovered] Witness testimonies in Watch archives
  - [Discovered] Connection to trade agreement negotiation (session 1)
- Characters Involved:
  - Jade Ravenshade (victim's daughter, seeks justice)
  - Watch Captain (investigator, stalled case)
  - Blue Dagger agents (possible perpetrators)
- Next Hook: Naelia discovers the letter fragment in Lower City

**2. The Blue Dagger Expansion** (Priority 2, Status: ACTIVE)
- Description: Blue Dagger systematically infiltrating Watch, Parliament, Flaming Fist
- Significance: Threatens Council of Four's monopoly on power
- Clues:
  - [Discovered] Redlocks takes bribes (hour 18-22 meetings)
  - [Undiscovered] Flaming Fist captain being blackmailed
- Characters Involved:
  - The Fang (Blue Dagger leader, identity unknown)
  - Redlocks (infiltrated by Dagger)
  - Naelia (potential opponent or ally)
- Narrative Hook: Naelia asked to mediate or suppress

**3. Naelia's Arrival** (Priority 1, Status: ACTIVE)
- Description: Avatar of the Lady has arrived; her divine nature reshapes power dynamics
- Significance: THE central thread; everything revolves around her presence
- Clues:
  - [Discovered] Celestial aura visible to those with Truesight
  - [Discovered] Scrying reveals planar connections
- Characters Involved:
  - Naelia (divine being)
  - Seraphine (ally/partner in plans)
  - Council of Four (cautious, seeking alliance/control)
  - Religious orders (seeking blessing/guidance)
- Narrative Hook: Every PC action shapes how Naelia's presence is perceived

---

### Plot Model Operations

**List Plots:**
```bash
curl "http://127.0.0.1:8000/dm/plots?status=active"       # Active threads only
curl "http://127.0.0.1:8000/dm/plots?priority=1"          # Critical threads
```

**Fetch Plot:**
```bash
curl http://127.0.0.1:8000/dm/plots/1
# Returns: Title, status, priority, description, characters involved, clues (discovered + hidden)
```

**Create Plot:**
```bash
curl -X POST http://127.0.0.1:8000/dm/plots \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Cult of Bane Rising",
    "description": "A hidden cult operating in the Outer City prepares a dark ritual",
    "priority": 3,
    "status": "active"
  }'
```

**Update Plot:**
```bash
curl -X PUT http://127.0.0.1:8000/dm/plots/1 \
  -H "Content-Type: application/json" \
  -d '{
    "updates": {
      "status": "resolved",
      "resolved_session_id": 5
    }
  }'
```

**Add Clue:**
```bash
curl -X POST http://127.0.0.1:8000/dm/plots/1/clue \
  -H "Content-Type: application/json" \
  -d '{"description": "A bloody knife matches the wounds from the murder scene"}'
```

**Discover Clue:**
```bash
curl -X PUT http://127.0.0.1:8000/dm/plots/1/clue/3 \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": 2,
    "details": "Found hidden in Olivia Caldwell'\''s private chambers"
  }'
```

---

## SESSION MANAGEMENT

### Session Lifecycle

1. **Start**: Create session, assign number, capture in-game date, set active
2. **Play**: Log events, make checks, roll dice, advance time
3. **End**: Record summary, capture final date, clear active flag
4. **Archive** (every 10 sessions): Compress into era summary, prune old data

### Current Session (Session 1)

```json
{
  "id": 1,
  "session_number": 1,
  "start_real_time": "2026-04-02T01:02:28Z",
  "end_real_time": null,
  "in_game_date_start": "1525-01-02",
  "in_game_date_end": null,
  "summary": null,
  "is_archived": 0
}
```

### Session Model Operations

**Start Session:**
```bash
curl -X POST http://127.0.0.1:8000/dm/session/start
# Returns: New session record with session_number, start time, in-game date
# Side effect: Updates world_state.active_session_id
```

**Get Current Session:**
```bash
curl http://127.0.0.1:8000/dm/session/current
# Returns: The active session (or error if none running)
```

**Log Event:**
```bash
curl -X POST http://127.0.0.1:8000/dm/session/event \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "narrative",
    "description": "Naelia confronts the Council of Four in the Wide",
    "characters_involved": [1, 2, 4, 5, 6],
    "location_id": 213
  }'
# Event types: narrative, combat, dialogue, discovery, travel, rest, other
```

**End Session:**
```bash
curl -X POST http://127.0.0.1:8000/dm/session/end \
  -H "Content-Type: application/json" \
  -d '{
    "summary": "After tense negotiations, the Council agreed to recognize Naelia as a legitimate power. The stage is set for the Council of Four to splinter."
  }'
# Side effect: Clears world_state.active_session_id, captures final in-game date
```

**Session History:**
```bash
curl "http://127.0.0.1:8000/dm/session/history?limit=20"
# Returns: Last 20 sessions (most recent first)
```

---

## DICE & MECHANICS

### The Dice Engine

**Expressions Supported:**
- `1d20`, `2d6`, `4d6kh3` (keep highest 3), `1d20+5`, `2d8+1d6+3` (compound)
- Special D&D logic: Critical hits (natural 20+), fumbles (natural 1), advantage/disadvantage

**Roll a Die:**
```bash
curl -X POST http://127.0.0.1:8000/dm/dice/roll \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "2d6+4",
    "advantage": false,
    "disadvantage": false,
    "purpose": "Fireball damage"
  }'
# Returns: Individual rolls, kept dice, modifiers, total, crit flag, fumble flag
```

**Parse Expressions:**
- `1d20`: Single d20
- `2d6+4`: Two d6, add 4
- `4d6kh3`: Roll 4d6, keep highest 3 (ability score generation)
- `1d20+5+1d4`: Compound expression (roll once for each dice group)
- `1d20` with `advantage=true`: Roll twice, keep higher

### Ability Checks

**Core Formula:**
```
Result = d20 + Ability Modifier + Proficiency (if applicable) + Skill Bonuses
```

**Roll Check:**
```bash
curl -X POST http://127.0.0.1:8000/dm/characters/1/ability-check \
  -H "Content-Type: application/json" \
  -d '{
    "ability": "int",              # str, dex, con, int, wis, cha
    "skill": "arcana",             # Optional; e.g. "arcana", "perception"
    "advantage": false,
    "disadvantage": false,
    "dc": 18
  }'
# Returns: Check type, ability, skill, total modifier, roll detail, success vs DC
```

**Example Results:**
- Naelia (INT 67, proficiency +26) rolls Arcana with advantage DC 18
  - INT mod: +28
  - Proficiency (expertise): +52
  - Total: +80
  - Result: 1d20 (with advantage) + 80 → nearly guaranteed success

### Saving Throws

**Roll Save:**
```bash
curl -X POST http://127.0.0.1:8000/dm/characters/1/saving-throw \
  -H "Content-Type: application/json" \
  -d '{
    "ability": "dex",
    "advantage": false,
    "disadvantage": false,
    "dc": 16
  }'
# Returns: Same format as ability check
```

### Attack Rolls

**Roll Attack:**
```bash
curl -X POST http://127.0.0.1:8000/dm/characters/1/attack \
  -H "Content-Type: application/json" \
  -d '{
    "is_melee": true,
    "is_spell": false,
    "bonus": 0,                     # Additional bonuses
    "advantage": false,
    "disadvantage": false,
    "target_ac": 18
  }'
# Returns: Attack roll total, hits vs AC, critical flag
```

### Damage Rolls

**Roll Damage:**
```bash
curl -X POST http://127.0.0.1:8000/dm/dice/damage \
  -H "Content-Type: application/json" \
  -d '{
    "expression": "2d6+4",
    "is_critical": false
  }'
# If critical: expression "2d6+4" becomes "4d6+4" (dice doubled, modifier stays)
```

---

## COMBAT SYSTEM

### Combat Lifecycle

1. **Initiate**: `/combat/start` with combatant IDs and location
2. **Initiative**: `/combat/initiative` to roll or provide manual initiatives
3. **Turns**: `/combat/next-turn` to advance
4. **Actions**: `/combat/action` for attacks, `/combat/heal` for healing
5. **End**: `/combat/end` to close encounter and determine outcome

### Combat Encounter State

```json
{
  "id": 1,
  "session_id": 1,
  "location_id": 220,
  "current_round": 2,
  "current_turn_index": 0,
  "status": "active",
  "combatants": [
    {
      "character_id": 1,
      "name": "Naelia An'Ohren",
      "initiative": 95,
      "is_current_turn": true,
      "hp_current": 2550,
      "hp_max": 2550,
      "ac": 55,
      "conditions": [],
      "team": "party"
    },
    {
      "character_id": 42,
      "name": "Blue Dagger Assassin",
      "initiative": 24,
      "is_current_turn": false,
      "hp_current": 75,
      "hp_max": 78,
      "ac": 16,
      "conditions": ["unconscious"],
      "team": "enemy"
    }
  ]
}
```

### Combat Operations

**Start Combat:**
```bash
curl -X POST http://127.0.0.1:8000/dm/combat/start \
  -H "Content-Type: application/json" \
  -d '{
    "combatant_ids": [1, 20, 21],   # Naelia, two enemies
    "location_id": 220,
    "teams": {
      "1": "party",
      "20": "enemy",
      "21": "enemy"
    }
  }'
# Creates encounter, initializes combatants with 0 initiative
```

**Roll Initiative:**
```bash
curl -X POST http://127.0.0.1:8000/dm/combat/initiative
# Auto-rolls DEX-based initiative for all, sorts by result
```

**Manual Initiative:**
```bash
curl -X POST http://127.0.0.1:8000/dm/combat/initiative \
  -H "Content-Type: application/json" \
  -d '{
    "initiatives": {
      "1": 24,
      "20": 19,
      "21": 12
    }
  }'
```

**Get Combat State:**
```bash
curl http://127.0.0.1:8000/dm/combat/state
# Returns: Current encounter, current turn, combatants list
```

**Take Turn Action (Attack):**
```bash
curl -X POST http://127.0.0.1:8000/dm/combat/action \
  -H "Content-Type: application/json" \
  -d '{
    "attacker_id": 1,
    "target_id": 20,
    "is_melee": false,
    "is_spell": true,
    "damage_expression": "8d6+28",
    "advantage": false,
    "target_ac": null                # Auto-fetch from combatant
  }'
# Returns: Attack roll, damage roll, target HP before/after
# Side effect: Updates combatant HP and character sheet
```

**Take Turn Action (Heal):**
```bash
curl -X POST http://127.0.0.1:8000/dm/combat/heal \
  -H "Content-Type: application/json" \
  -d '{
    "healer_id": 2,
    "target_id": 1,
    "heal_expression": "2d8+5"
  }'
# Returns: Healing roll, target HP before/after (capped at max)
```

**Next Turn:**
```bash
curl -X POST http://127.0.0.1:8000/dm/combat/next-turn
# Advances to next combatant in initiative order
# If end of round: increments current_round, loops back to start
```

**End Combat:**
```bash
curl -X POST http://127.0.0.1:8000/dm/combat/end \
  -H "Content-Type: application/json" \
  -d '{
    "outcome": "party victory; enemies routed toward Undercity"
  }'
# Sets status to "completed", records outcome, clears current turn
```

---

## GUILD TOKEN ECONOMY

### Rank Structure

| Rank | Min Tokens | CR Max | Examples | Perks |
|------|-----------|--------|----------|-------|
| Copper | 0 | 4 | Adventurers, sellswords | Contract access |
| Brass | 100 | 6 | Seasoned mercenaries | Equipment discount |
| Bronze | 10K | 14 | Leaders, specialists | Guild store access |
| Silver | 100K | 17 | Masters, rare talents | Upper City access |
| Gold | 1M | 20 | Legendary heroes | Political influence |
| Platinum | 100M | Any | Gods, avatars | Favor from Guild |

### Contract System

**Contract Lifecycle:**
1. **Posted** (status: `open`): Reward tokens listed, difficulty set
2. **Claimed** (status: `claimed`): Character stakes 10% of reward (deducted from balance)
3. **Completed** (status: `completed`): Character earns reward + returns stake
4. **Failed** (status: `failed`): Stake is forfeited, no reward

**Example Contract:**
```json
{
  "id": 1,
  "title": "Investigate Ravenshade Assassination",
  "description": "Gold-rank contract seeking actionable intelligence on the 1509 murder of Yuuto and Sibyll Ravenshade.",
  "status": "open",
  "reward_tokens": 1000000,
  "difficulty": "gold",
  "posted_by_character_id": 1  // Jade Ravenshade
}
```

### Guild Token Operations

**Get Character Rank:**
```bash
curl http://127.0.0.1:8000/dm/guild/rank/1
# Returns: Rank name, tokens, next threshold, tokens to next rank
```

**List Contracts:**
```bash
curl "http://127.0.0.1:8000/dm/guild/contracts?status=open"       # Open only
curl "http://127.0.0.1:8000/dm/guild/contracts?difficulty=gold"   # Gold rank
```

**Create Contract:**
```bash
curl -X POST http://127.0.0.1:8000/dm/guild/contracts \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Eliminate Blue Dagger Smuggling Ring",
    "description": "The Watch seeks assistance dismantling the operation in Gray Harbor.",
    "reward_tokens": 50000,
    "difficulty": "silver",
    "posted_by_character_id": 4  // Redlocks
  }'
```

**Claim Contract:**
```bash
curl -X POST http://127.0.0.1:8000/dm/guild/contracts/1/claim \
  -H "Content-Type: application/json" \
  -d '{
    "character_id": 1,           // Must have enough tokens for stake
    "session_id": 2
  }'
# Deducts stake (100K tokens) from Naelia's balance
# Side effect: Ledger entry created
```

**Complete Contract:**
```bash
curl -X POST http://127.0.0.1:8000/dm/guild/contracts/1/complete?session_id=5
# Awards reward + returns stake
# Side effect: Two ledger entries (return stake, award reward)
# Auto-check: Triggers rank promotion if balance now qualifies for higher tier
```

**Fail Contract:**
```bash
curl -X POST http://127.0.0.1:8000/dm/guild/contracts/1/fail?session_id=5
# Marks as failed
# Side effect: Stake is forfeited (ledger entry records loss)
# Auto-check: Triggers rank demotion if balance drops below current rank minimum
```

**View Ledger:**
```bash
curl "http://127.0.0.1:8000/dm/guild/ledger/1?limit=50"
# Returns: Transaction history for character (claim stake, award, forfeit, etc.)
```

---

## ARCHIVAL & BACKUP

### Archival System

**Trigger:** Every 10 completed sessions (configurable in `game_config.json`)

**What Happens:**
1. Gathers all session events from the last 10 sessions
2. Summarizes key narrative moments
3. Creates era summary record with session range, in-game date range, event summary
4. Marks sessions as `is_archived = 1`
5. Deletes old session_events and dice_roll records (keeps only last N rolls)
6. Captures character snapshots at era boundary

**Era Summary Example:**
```json
{
  "id": 1,
  "session_range_start": 1,
  "session_range_end": 10,
  "in_game_date_start": "1525-01-02",
  "in_game_date_end": "1525-02-15",
  "summary": "The Avatar Naelia has reshaped the power structure of Baldur's Gate. Council of Four fractured; Blue Dagger ascendant...",
  "key_events": [
    "Naelia's public revelation as celestial being",
    "Assassination of Caldwell rival (Blue Dagger)",
    "Seraphine consolidates Platinum rank",
    "Watch corruption exposed (Redlocks bribed)"
  ]
}
```

### Backup System

**Auto-Backup:**
- Triggers on in-game day change (midnight)
- Creates timestamped database snapshot: `world_YYYYMMDD_HHMMSS.db`

**Manual Backup:**
```bash
curl -X POST "http://127.0.0.1:8000/admin/backup?label=pre_ravenshade_assassination"
# Creates: world_YYYYMMDD_HHMMSS_pre_ravenshade_assassination.db
```

**List Backups:**
```bash
curl http://127.0.0.1:8000/admin/backups
# Returns: All backup files with dates, sizes
```

**Restore from Backup:**
```bash
curl -X POST "http://127.0.0.1:8000/admin/restore/world_20250401_103000.db"
# WARNING: Replaces current database
# Side effect: Creates safety backup before restore
```

**Database Stats:**
```bash
curl http://127.0.0.1:8000/admin/stats
# Returns: DB size, row counts per table, last backup info, schema version
```

---

## REST API REFERENCE

### Health & Admin

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Server status |
| POST | `/admin/backup` | Manual backup |
| GET | `/admin/backups` | List backups |
| POST | `/admin/restore/{filename}` | Restore from backup |
| GET | `/admin/stats` | DB stats |
| POST | `/admin/archive` | Trigger archival |

### World State

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dm/world` | Current state |
| PUT | `/dm/world` | Update state |
| POST | `/dm/world/advance-time` | Add hours/minutes |
| POST | `/dm/world/set-time` | Jump to date/time |
| POST | `/dm/world/weather-roll` | Roll weather |

### Characters

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dm/characters` | List (filter: type, status, location, org, name) |
| GET | `/dm/characters/{id}` | Full sheet |
| GET | `/dm/characters/{id}/relationships` | Outbound edges |
| PUT | `/dm/characters/{id}` | Update fields |
| POST | `/dm/characters/{id}/move` | Change location |
| GET | `/dm/characters/at-location/{location_id}` | Characters here |
| POST | `/dm/characters/{id}/ability-check` | Roll check |
| POST | `/dm/characters/{id}/saving-throw` | Roll save |
| POST | `/dm/characters/{id}/attack` | Roll attack |

### Organizations

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dm/organizations` | List (filter: type, parent, is_secret) |
| GET | `/dm/organizations/{id}` | Details + members + relationships |
| PUT | `/dm/organizations/{id}` | Update |

### Locations

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dm/locations` | List (filter: type, parent, name, is_secret) |
| GET | `/dm/locations/{id}` | Details + children + characters |
| GET | `/dm/locations/{id}/path` | Hierarchy chain (root to leaf) |

### Plots

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dm/plots` | List (filter: status, priority) |
| GET | `/dm/plots/{id}` | Details + clues + characters |
| POST | `/dm/plots` | Create thread |
| PUT | `/dm/plots/{id}` | Update |
| POST | `/dm/plots/{id}/clue` | Add clue |
| PUT | `/dm/plots/{id}/clue/{clue_id}` | Discover clue |

### Sessions

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/dm/session/start` | Begin session |
| POST | `/dm/session/end` | End session |
| GET | `/dm/session/current` | Active session |
| GET | `/dm/session/history` | Past sessions |
| POST | `/dm/session/event` | Log event |

### Dice

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/dm/dice/roll` | Roll expression |
| POST | `/dm/dice/damage` | Roll damage |
| POST | `/dm/dice/oracle-burden` | Roll Naelia's visions |
| POST | `/dm/dice/intoxication-check/{id}` | Check intoxication |
| POST | `/dm/dice/weather` | Roll weather |
| GET | `/mechanics` | List mechanics |
| GET | `/mechanics/{name}` | Get mechanic details |

### Combat

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/dm/combat/start` | Create encounter |
| POST | `/dm/combat/initiative` | Roll or set initiatives |
| POST | `/dm/combat/action` | Attack action |
| POST | `/dm/combat/heal` | Healing action |
| POST | `/dm/combat/next-turn` | Advance turn |
| GET | `/dm/combat/state` | Current state |
| POST | `/dm/combat/end` | Close encounter |

### Guild

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/dm/guild/contracts` | List (filter: status, difficulty) |
| GET | `/dm/guild/contracts/{id}` | Details |
| POST | `/dm/guild/contracts` | Create |
| POST | `/dm/guild/contracts/{id}/claim` | Claim contract |
| POST | `/dm/guild/contracts/{id}/complete` | Complete |
| POST | `/dm/guild/contracts/{id}/fail` | Fail |
| GET | `/dm/guild/rank/{id}` | Character rank |
| GET | `/dm/guild/ledger/{id}` | Transaction history |

---

## MECHANICS DEEP DIVES

### 1. Oracle's Burden (Naelia's Vision System)

**Trigger:** During long rest (8+ hours uninterrupted sleep)

**Mechanics:**
- Roll 1d100 on `vision_count_table` to determine number of visions
- For each vision, roll 1d20 on `vision_importance_table` to determine theme

**Vision Count Table:**
- Roll 0-94: 1 vision
- Roll 95-100: 2 visions

**Vision Importance Table (1d20):**
- Roll 1-5: Minor (inconsequential encounter, random crime)
- Roll 6-15: Major (important event related to Naelia's preoccupations)
- Roll 16-20: World-shaking (destiny-level revelation)

**Usage:**
```bash
curl -X POST http://127.0.0.1:8000/dm/dice/oracle-burden
# Returns: Number of visions, importance of each, descriptions
```

**Narrative Integration:**
- Visions should foreshadow or relate to active plot threads
- Naelia can act on visions strategically
- Unreliable narrator: sometimes visions are metaphorical, not literal
- Divine beings in Naelia's past may communicate through visions

---

### 2. Intoxication Mechanic (Tavern Drinking)

**Formula:**
```
Threshold = max(1, min(7 + racial_mod + (CON_mod * 3), 100))
Drinks_Over = Effective_Drinks - Threshold
Ratio = Drinks_Over / Threshold
Effect = [0.5x, 0.75x, 1.0x, 1.5x, 2.0x] based on ratio
```

**Racial Modifiers:**
- Dwarf: +2 (alcohol resistance in blood)
- Half-Orc: +1
- Elf: -1 (lighter build, less tolerance)
- Human: 0
- [Others in mechanic JSON]

**Drink Strength Multipliers:**
- Non-Alcoholic: 0x
- Light: 1x
- Moderate: 2x
- Strong: 3x
- Very Strong: 4x
- Deadly: 5x

**Effect Levels:**
- **0.5x Threshold**: +1 CHA, normal attacks
- **0.75x Threshold**: +2 CHA, -1 STR, normal attacks
- **1.0x Threshold**: Normal CHA, -2 STR, disadvantage on attacks
- **1.5x Threshold**: -2 CHA, -3 STR, disadvantage on all checks except CHA
- **2.0x Threshold**: Blackout risk — Constitution save DC 10 or pass out

**Usage:**
```bash
curl -X POST http://127.0.0.1:8000/dm/dice/intoxication-check/1 \
  -H "Content-Type: application/json" \
  -d '{"drinks_consumed": 5, "drink_strength": "Strong"}'
# Naelia: CON 53 → CON_mod +21, no racial mod
# Threshold = 7 + 0 + 63 = 70
# Effective = 5 * 3 = 15
# Ratio = 15/70 = 0.21
# Effect: 0.5x (very minor buzz)
```

**Mechanics:**
- Effects persist until character rests
- Detox rate: 1 level per 30 minutes or via Cure Poison spell
- Hangover next day: -3 CON checks, -2 INT checks until long rest

---

### 3. Talent System (Tier-Based Progression)

**Purpose:** Simplified leveling for a high-power campaign where traditional experience feels slow

**Tier 0 (Mundane):**
- CR 0-0.5
- Population: 85%
- Examples: Commoners, basic guards
- Stat bonus: 0
- Max ability score: 18

**Tier 1 (Talented):**
- CR 1-5
- Population: 12%
- Examples: Adventurers, skilled merchants
- Stat bonus: +1 to one ability
- Max ability score: 20

**Tier 2 (Exceptional):**
- CR 6-15
- Population: 2.5%
- Examples: Seraphine, major NPCs
- Stat bonus: +2 to abilities
- Max ability score: 22

**Tier 3 (Legendary):**
- CR 16+
- Population: 0.5%
- Examples: Naelia, divine beings
- Stat bonus: +4 to abilities
- Max ability score: 30

**Usage:**
```bash
curl http://127.0.0.1:8000/dm/guild/rank/1
# Returns character's tier and associated bonuses
```

---

### 4. Weather System

**Roll Frequency:** Every 4 hours (in-game time)

**Seasonal Tables (d100 lookup):**
- Winter: Snow, Blizzard, Freezing Rain, Clear Skies
- Spring: Rain, Moderate Rain, Heavy Rain, Muddy, Clear
- Summer: Clear, Thunderstorm, Scattered Clouds, Hot/Drought
- Autumn: Moderate Weather, Wind, Light Snow, Crisp Clear

**Combat Effects:**
- **Fog** (visibility 15 ft.): Disadvantage on Perception, ranged attacks disadvantage
- **Rain** (difficult terrain): Movement reduced, visibility 60 ft.
- **Blizzard** (extreme cold): Constitution saves for cold damage, visibility 30 ft.
- **Thunderstorm**: Lightning strikes (periodic DEX saves), wind pushes creatures

**Integration:**
- Weather auto-updates when time advances
- Affects outdoor encounters, travel speeds, visibility
- Can trap parties if terrain becomes impassable

---

### 5. Guild Token Economy (Advanced Rules)

**Law of the Dozen:** A character cannot hold more than 12 active contracts simultaneously.

**The Squeeze:** If a character's token balance drops below their rank minimum, they have 30 days to recover or get demoted to the highest rank they qualify for.

**Stake Rules:** Claiming a contract requires staking 10% of the reward. Forfeited on failure, returned on success.

**Freelance vs. Guild:** High-rank members sometimes take freelance contracts outside the guild (negotiated rewards). These don't generate ledger entries but build reputation.

---

### 6. World Simulation (Background Events)

**NPC Schedules:**
- Each NPC has routine activities by day-of-tenday and hour
- When time advances, system checks `npc_schedules` and moves characters to assigned locations
- Example: Redlocks is at the Watch Citadel every hour 6-18, meetings with Blue Dagger agents 18-22

**Background Events (Future):**
- Random encounters in districts based on recent events
- Merchant caravans arriving/departing
- Social events (noble parties, guild meetings)
- Rumors spreading through the city

---

## NPC PERSONALITIES

### Jade Ravenshade (Grand Duchess, CR 8)

**Voice & Mannerism:**
- Speaks with aristocratic precision; every word measured
- Favors indirect requests ("I wonder if someone might...") over direct commands
- Emotional baseline: controlled, reveals little
- Rare show of vulnerability when discussing Yuuto's murder

**Motivations:**
- Justice for slain parents (top priority)
- Consolidate power within Council of Four
- Prove herself as worthy successor to Ravenshade legacy
- Maintain Naelia's patronage (sees her as checkmate against rivals)

**Relationships (Internal Monologue):**
- **Naelia**: "The Avatar is our salvation. With her blessing, I am unassailable. I must prove my worth constantly."
- **Seraphine**: "The Fey woman is too clever. Her smile hides daggers. But she respects strength, and if Naelia trusts her, I will too—carefully."
- **Olivia Caldwell**: "The merchant thinks she can outmaneuver me. Her husband's death weakened her; I'll exploit it."
- **Redlocks**: "A soldier, easily influenced. His corruption is useful but temporary."

**Dialogue Patterns:**
- Asks questions that reveal others' thinking
- Rarely makes direct threats (prefers others to draw conclusions)
- Uses formal titles; expects same in return
- References Ravenshade legacy often (family pride/burden)

**Secrets:**
- Suspected the Blue Dagger poisoned her parents; waiting for proof
- Has offered bounty on Blue Dagger leadership (whispers only)
- Writes coded letters to intelligence network every week

---

### Seraphine (Archfey, CR 35)

**Voice & Mannerism:**
- Crystalline laugh, slightly too long to be natural (inhuman)
- Speaks in layers: surface conversation + hidden meanings
- Switches between warm and cold instantaneously
- Loves wordplay, puns, trickster logic

**Motivations:**
- Expand Guild influence (long-term goal: every major city in Sword Coast)
- Secure planar gateway in Bloomridge (prevents outsiders' access)
- Maintain Naelia as ally but not reveal deeper plans
- Observe mortals for amusement and philosophical insight

**Relationships:**
- **Naelia**: "She is becoming so much more than I expected. Divine, yes, but also growing attached to this realm. That's delicious."
- **Guild Members**: "Excellent tools. Ambitious, predictable, easily motivated."
- **Council of Four**: "Playing chess with children. They move, I'm six moves ahead."
- **Blue Dagger**: "Interesting rivals. Their ruthlessness appeals to me. Perhaps we might ally against the Watch."

**Dialogue Patterns:**
- Compliments wrapped around insults
- Asks riddles or trick questions
- Laughs at her own jokes (finds mortals amusing)
- Speaks of centuries-old events as if recent
- Uses "dear" and "darling" excessively

**Secrets:**
- Planar pocket dimension beneath Bloomridge stores artifacts and allies
- Ancient magic ritual in progress (purpose unknown)
- Has backup plans if Naelia becomes uncontrollable
- Harbors romantic interest in Naelia (unspoken, denies if asked)

---

### The Fang (Blue Dagger Leader, CR Unknown)

**Profile:** Deliberately obscured identity. May be multiple people rotating the title. Communicates only through intermediaries.

**Known Facts:**
- Commands Blue Dagger with absolute authority
- Strategic mind; long-term planning evident
- Personally assassinated (rumored) 3+ targets
- Relationship with planar entities suspected

**Theories:**
- Former Watch commander (explains intelligence access)
- Planar being using mortals as proxies
- Shadow Guild leader (doppelgänger?)
- Collective council (no single Fang)

**Operational Style:**
- Minimal waste; every operation has multiple objectives
- Collects blackmail on Patricians systematically
- Respects worthy adversaries (treats them with formal courtesy even in conflict)
- Interested in Naelia's intentions toward Baldur's Gate

---

## APPENDIX: COMMON QUERIES

### "What does Naelia do right now?"

Query the current session and location:
```bash
curl http://127.0.0.1:8000/dm/session/current
curl http://127.0.0.1:8000/dm/characters/1
# Review current_location_id, last event in session
```

### "What's Seraphine's opinion of this situation?"

Reference the relationships JSON, then roleplay. Use her motivations (expand guild, maintain power) and dialogue patterns.

### "Can Naelia be ambushed?"

Mechanically, no (AC 55, legendary resistances). Narratively, yes (imprisoned, cursed, negotiation leads to truce). Ask: Is this a mechanical challenge or a story moment?

### "What would happen if they visited the Undercity?"

Query Blue Dagger assets:
```bash
curl http://127.0.0.1:8000/dm/organizations/2  # Blue Dagger
# Check relationships, controlled locations, NPCs
```

Prepare encounters based on her tactical profile. Consider political angles: Is Naelia recognized? Do they want war or negotiation?

### "How much time has passed since Session 1?"

```bash
curl http://127.0.0.1:8000/dm/world
# Check current_date, compare to in_game_date from previous session
```

---

## END OF ROBOTS.MD

**Last Updated:** 2026-04-02
**Seasons Tracked:** 1 (Winter → ongoing)
**Sessions Logged:** 1+
**Archive Status:** Current era not yet archived (requires 10 sessions)

**For Support:** The server is deterministic and stateless. If something breaks, restore from backup and replay events via session event logging.

**Final Note:** This manual is written for agents. It assumes you understand D&D rules, narrative pacing, and the value of keeping players surprised. Naelia's world is yours to inhabit. Make it memorable.

---

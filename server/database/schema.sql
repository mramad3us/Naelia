-- ============================================================================
-- NAELIA'S CHRONICLES — Database Schema
-- Version: 1
-- Engine: SQLite 3
-- ============================================================================
-- This database IS the world. Every character, location, organization, plot
-- thread, session event, and dice roll lives here. The LLM-DM reads and writes
-- to this database via the game server's REST API.
-- ============================================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA encoding = 'UTF-8';

-- ============================================================================
-- INFRASTRUCTURE
-- ============================================================================

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO schema_version (version) VALUES (1);

CREATE TABLE IF NOT EXISTS backups (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    backup_date     TEXT NOT NULL DEFAULT (datetime('now')),
    in_game_date    TEXT,
    file_path       TEXT NOT NULL,
    size_bytes      INTEGER,
    checksum        TEXT,
    notes           TEXT
);

-- ============================================================================
-- LOCATIONS (must come before characters due to FK references)
-- ============================================================================
-- Hierarchical: plane > world > continent > region > city > district > building > room
-- Self-referencing via parent_id

CREATE TABLE IF NOT EXISTS locations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,
    parent_id           INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    type                TEXT NOT NULL CHECK (type IN (
                            'plane', 'world', 'continent', 'region', 'city',
                            'district', 'building', 'room', 'wilderness', 'dungeon', 'other'
                        )),
    description         TEXT,
    climate_modifier    TEXT DEFAULT '{}',   -- JSON: modifiers for weather rolls
    coordinates_x       REAL,
    coordinates_y       REAL,
    is_public           INTEGER NOT NULL DEFAULT 1,  -- 0 = secret/hidden location
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_locations_parent ON locations(parent_id);
CREATE INDEX idx_locations_type ON locations(type);
CREATE INDEX idx_locations_name ON locations(name);

-- ============================================================================
-- CHARACTERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS characters (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identity
    name                    TEXT NOT NULL,
    aliases                 TEXT DEFAULT '[]',       -- JSON array of strings
    type                    TEXT NOT NULL CHECK (type IN (
                                'pc', 'critical', 'major', 'minor', 'legend'
                            )),
    race                    TEXT,
    subrace                 TEXT,
    creature_type           TEXT DEFAULT 'humanoid', -- humanoid, fey, celestial, fiend, undead, elemental, etc.
    sex                     TEXT,
    alignment               TEXT,
    age                     INTEGER,
    cr                      REAL,                    -- Challenge Rating (NULL for leveled characters)

    -- Class & Progression
    class_levels            TEXT DEFAULT '{}',       -- JSON: {"Monk": 20} or {"Paladin": 11, "Rogue": 7}
    talent_tier             INTEGER DEFAULT 0 CHECK (talent_tier BETWEEN 0 AND 3),
                                                     -- 0=none, 1=*, 2=**, 3=***
    background              TEXT,
    xp                      INTEGER DEFAULT 0,

    -- Core Stats
    str                     INTEGER DEFAULT 10,
    dex                     INTEGER DEFAULT 10,
    con                     INTEGER DEFAULT 10,
    int                     INTEGER DEFAULT 10,
    wis                     INTEGER DEFAULT 10,
    cha                     INTEGER DEFAULT 10,

    -- Derived Combat Stats
    hp_max                  INTEGER DEFAULT 10,
    hp_current              INTEGER DEFAULT 10,
    ac                      INTEGER DEFAULT 10,
    speed                   TEXT DEFAULT '30 ft.',   -- Can include fly, swim, etc.
    proficiency_bonus       INTEGER DEFAULT 2,

    -- Proficiencies (JSON)
    saves_proficient        TEXT DEFAULT '[]',       -- JSON: ["dex", "cha"]
    skills                  TEXT DEFAULT '{}',       -- JSON: {"Arcana": {"proficient": true, "expertise": false, "bonus": 0}}
    languages               TEXT DEFAULT '[]',       -- JSON array
    tool_proficiencies      TEXT DEFAULT '[]',       -- JSON array
    armor_proficiencies     TEXT DEFAULT '[]',       -- JSON array
    weapon_proficiencies    TEXT DEFAULT '[]',       -- JSON array

    -- Damage & Condition Modifiers (JSON arrays)
    damage_resistances      TEXT DEFAULT '[]',
    damage_immunities       TEXT DEFAULT '[]',
    damage_vulnerabilities  TEXT DEFAULT '[]',
    condition_immunities    TEXT DEFAULT '[]',

    -- Senses
    senses                  TEXT DEFAULT '{}',       -- JSON: {"darkvision": 60, "truesight": 120, "passive_perception": 15}

    -- Spellcasting
    spellcasting_ability    TEXT,                     -- "cha", "int", "wis", or NULL
    spell_save_dc           INTEGER,
    spell_attack_mod        INTEGER,
    spell_slots             TEXT DEFAULT '{}',       -- JSON: {"1": 4, "2": 3, ...} or {"pact": 2, "pact_level": 5}
    spells_known            TEXT DEFAULT '{}',       -- JSON: {"cantrips": [...], "1": [...], "2": [...], ...}
    innate_spells           TEXT DEFAULT '{}',       -- JSON: {"at_will": [...], "3/day": [...], "1/day": [...]}

    -- Features & Abilities (JSON)
    class_features          TEXT DEFAULT '[]',       -- JSON array of {name, description}
    racial_traits           TEXT DEFAULT '[]',
    special_abilities       TEXT DEFAULT '[]',       -- For monsters/unique NPCs
    legendary_actions       TEXT DEFAULT '{}',       -- JSON: {"per_round": 3, "actions": [...]}
    lair_actions            TEXT DEFAULT '[]',
    reactions               TEXT DEFAULT '[]',

    -- Actions (for NPCs/monsters with defined action blocks)
    actions                 TEXT DEFAULT '[]',       -- JSON array of {name, type, to_hit, damage, range, description}

    -- Current State
    current_location_id     INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    status                  TEXT NOT NULL DEFAULT 'alive' CHECK (status IN (
                                'alive', 'dead', 'undead', 'imprisoned', 'missing',
                                'banished', 'petrified', 'dormant'
                            )),
    conditions              TEXT DEFAULT '[]',       -- JSON: active conditions [{name, duration, source}]
    temp_hp                 INTEGER DEFAULT 0,
    death_saves             TEXT DEFAULT '{}',       -- JSON: {"successes": 0, "failures": 0}

    -- Guild (Gilded Gauntlet)
    guild_rank              TEXT CHECK (guild_rank IN (
                                NULL, 'copper', 'brass', 'bronze', 'silver', 'gold', 'platinum'
                            )),
    guild_tokens            INTEGER DEFAULT 0,       -- Can be very large for high-rank members
    guild_company           TEXT,                     -- Iron Grip, Purple Hand, etc.

    -- Economy
    lifestyle_daily_gp      REAL DEFAULT 0,
    wealth_gp               REAL DEFAULT 0,          -- Current liquid wealth

    -- Narrative
    importance              INTEGER NOT NULL DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
                                                     -- 1=legend, 2=critical, 3=major, 4=minor, 5=background
    is_public               INTEGER NOT NULL DEFAULT 1,  -- 0 = existence is secret
    appearance_text         TEXT,
    backstory_text          TEXT,
    personality_text        TEXT,
    voice_notes             TEXT,                     -- How this NPC speaks, verbal tics, accent
    quest_tags              TEXT DEFAULT '[]',        -- JSON array of quest hook tags

    -- Meta
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_characters_type ON characters(type);
CREATE INDEX idx_characters_status ON characters(status);
CREATE INDEX idx_characters_location ON characters(current_location_id);
CREATE INDEX idx_characters_importance ON characters(importance);
CREATE INDEX idx_characters_name ON characters(name);
CREATE INDEX idx_characters_guild_rank ON characters(guild_rank);
CREATE INDEX idx_characters_alive_importance ON characters(status, importance) WHERE status = 'alive';

-- ============================================================================
-- CHARACTER RELATIONSHIPS
-- ============================================================================
-- Directed graph: character_id has relationship with target_id.
-- For bidirectional relationships, create two rows.

CREATE TABLE IF NOT EXISTS character_relationships (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id        INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    target_id           INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    relationship_type   TEXT NOT NULL CHECK (relationship_type IN (
                            'family', 'friend', 'rival', 'enemy', 'patron', 'servant',
                            'romantic', 'political', 'criminal', 'mentor', 'student',
                            'employer', 'employee', 'ally', 'protector', 'ward'
                        )),
    description         TEXT,
    sentiment           INTEGER DEFAULT 0 CHECK (sentiment BETWEEN -10 AND 10),
                                                 -- -10 = hatred, 0 = neutral, 10 = devotion
    is_secret           INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_char_rel_character ON character_relationships(character_id);
CREATE INDEX idx_char_rel_target ON character_relationships(target_id);
CREATE INDEX idx_char_rel_type ON character_relationships(relationship_type);
CREATE INDEX idx_char_rel_secret ON character_relationships(is_secret);

-- ============================================================================
-- CHARACTER SNAPSHOTS (for archival era boundaries)
-- ============================================================================

CREATE TABLE IF NOT EXISTS character_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id    INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    era_id          INTEGER NOT NULL REFERENCES era_summaries(id) ON DELETE CASCADE,
    snapshot_data   TEXT NOT NULL,    -- JSON: full character state at that moment
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_char_snap_character ON character_snapshots(character_id);
CREATE INDEX idx_char_snap_era ON character_snapshots(era_id);

-- ============================================================================
-- NPC SCHEDULES (for world simulation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS npc_schedules (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id    INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    day_of_tenday   INTEGER CHECK (day_of_tenday BETWEEN 1 AND 10),  -- NULL = every day
    hour_start      INTEGER NOT NULL CHECK (hour_start BETWEEN 0 AND 23),
    hour_end        INTEGER NOT NULL CHECK (hour_end BETWEEN 0 AND 23),
    activity        TEXT NOT NULL,
    location_id     INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    notes           TEXT
);

CREATE INDEX idx_npc_sched_character ON npc_schedules(character_id);
CREATE INDEX idx_npc_sched_time ON npc_schedules(hour_start, hour_end);

-- ============================================================================
-- ITEMS
-- ============================================================================

CREATE TABLE IF NOT EXISTS items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL CHECK (type IN (
                        'weapon', 'armor', 'shield', 'wondrous', 'potion',
                        'scroll', 'ring', 'wand', 'staff', 'rod',
                        'consumable', 'mundane', 'artifact', 'other'
                    )),
    rarity          TEXT CHECK (rarity IN (
                        'common', 'uncommon', 'rare', 'very_rare', 'legendary', 'artifact', NULL
                    )),
    properties      TEXT DEFAULT '{}',   -- JSON: weapon stats, AC bonus, spell stored, etc.
    requires_attunement INTEGER DEFAULT 0,
    attuned_to      INTEGER REFERENCES characters(id) ON DELETE SET NULL,
    held_by         INTEGER REFERENCES characters(id) ON DELETE SET NULL,
    location_id     INTEGER REFERENCES locations(id) ON DELETE SET NULL,  -- If not held by anyone
    equipped        INTEGER DEFAULT 0,
    slot            TEXT,                -- mainhand, offhand, armor, ring1, ring2, neck, head, etc.
    is_cursed       INTEGER DEFAULT 0,
    is_identified   INTEGER DEFAULT 1,
    description     TEXT,
    value_gp        REAL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_items_held_by ON items(held_by);
CREATE INDEX idx_items_location ON items(location_id);
CREATE INDEX idx_items_type ON items(type);

-- ============================================================================
-- ORGANIZATIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS organizations (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT NOT NULL,
    parent_org_id           INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    type                    TEXT NOT NULL CHECK (type IN (
                                'guild', 'criminal', 'religious', 'political', 'military',
                                'secret', 'mercantile', 'noble_house', 'other'
                            )),
    description             TEXT,
    headquarters_location_id INTEGER REFERENCES locations(id) ON DELETE SET NULL,
    symbol_description      TEXT,
    is_secret               INTEGER NOT NULL DEFAULT 0,
    treasury_gp             REAL DEFAULT 0,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_orgs_parent ON organizations(parent_org_id);
CREATE INDEX idx_orgs_type ON organizations(type);
CREATE INDEX idx_orgs_secret ON organizations(is_secret);

-- ============================================================================
-- ORGANIZATION MEMBERSHIPS
-- ============================================================================

CREATE TABLE IF NOT EXISTS org_memberships (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id    INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    org_id          INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role            TEXT,            -- "Guildmaster", "Kingpin", "Mother", "Finger", etc.
    rank            TEXT,            -- Freeform rank within the org
    is_public       INTEGER NOT NULL DEFAULT 1,  -- 0 = secret membership
    joined_date     TEXT,            -- In-world date
    notes           TEXT,
    UNIQUE(character_id, org_id)
);

CREATE INDEX idx_org_mem_character ON org_memberships(character_id);
CREATE INDEX idx_org_mem_org ON org_memberships(org_id);
CREATE INDEX idx_org_mem_public ON org_memberships(is_public);

-- ============================================================================
-- ORGANIZATION RELATIONSHIPS
-- ============================================================================

CREATE TABLE IF NOT EXISTS org_relationships (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    org_a_id            INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    org_b_id            INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    relationship_type   TEXT NOT NULL CHECK (relationship_type IN (
                            'allied', 'hostile', 'neutral', 'infiltrated',
                            'subsidiary', 'rival', 'cooperative', 'unknown'
                        )),
    description         TEXT,
    is_secret           INTEGER NOT NULL DEFAULT 0,
    UNIQUE(org_a_id, org_b_id)
);

CREATE INDEX idx_org_rel_a ON org_relationships(org_a_id);
CREATE INDEX idx_org_rel_b ON org_relationships(org_b_id);

-- ============================================================================
-- WORLD STATE (singleton)
-- ============================================================================

CREATE TABLE IF NOT EXISTS world_state (
    id                      INTEGER PRIMARY KEY CHECK (id = 1),
    current_date            TEXT NOT NULL DEFAULT '1525-01-01',  -- Dale Reckoning
    current_hour            INTEGER NOT NULL DEFAULT 8 CHECK (current_hour BETWEEN 0 AND 23),
    current_minute          INTEGER NOT NULL DEFAULT 0 CHECK (current_minute BETWEEN 0 AND 59),
    season                  TEXT NOT NULL DEFAULT 'winter' CHECK (season IN (
                                'winter', 'spring', 'summer', 'fall'
                            )),
    weather_by_location     TEXT DEFAULT '{}',   -- JSON: {location_id: {type, established, last_roll_hour}}
    active_session_id       INTEGER REFERENCES sessions(id),
    active_combat_id        INTEGER,             -- FK to combat_encounters, nullable
    last_weather_roll_hour  INTEGER DEFAULT 0,
    last_backup_game_date   TEXT,
    political_summary       TEXT DEFAULT '',
    notes                   TEXT DEFAULT '',      -- DM scratch notes
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ============================================================================
-- WEATHER TABLES (reference data for the d100 system)
-- ============================================================================

CREATE TABLE IF NOT EXISTS weather_tables (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    season          TEXT NOT NULL CHECK (season IN ('winter', 'spring', 'summer', 'fall')),
    weather_type    TEXT NOT NULL,
    d100_min        INTEGER NOT NULL,
    d100_max        INTEGER NOT NULL,
    effects         TEXT DEFAULT '{}',   -- JSON: combat modifiers, travel effects, etc.
    description     TEXT
);

CREATE INDEX idx_weather_season ON weather_tables(season);

-- ============================================================================
-- WORLD HISTORY (background timeline, not session events)
-- ============================================================================

CREATE TABLE IF NOT EXISTS world_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    year_dr             INTEGER NOT NULL,    -- Dale Reckoning year
    event_title         TEXT NOT NULL,
    event_description   TEXT,
    characters_involved TEXT DEFAULT '[]',   -- JSON array of character IDs
    significance        TEXT DEFAULT 'major' CHECK (significance IN ('minor', 'major', 'critical')),
    is_public           INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_world_history_year ON world_history(year_dr);

-- ============================================================================
-- PLOT THREADS
-- ============================================================================

CREATE TABLE IF NOT EXISTS plot_threads (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
                            'active', 'dormant', 'resolved', 'failed', 'archived'
                        )),
    priority            INTEGER DEFAULT 3 CHECK (priority BETWEEN 1 AND 5),
                                             -- 1 = critical, 5 = background
    description         TEXT,
    created_session_id  INTEGER REFERENCES sessions(id),
    resolved_session_id INTEGER REFERENCES sessions(id),
    resolution_summary  TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_plot_status ON plot_threads(status);
CREATE INDEX idx_plot_priority ON plot_threads(priority);

-- ============================================================================
-- PLOT CLUES
-- ============================================================================

CREATE TABLE IF NOT EXISTS plot_clues (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    plot_thread_id          INTEGER NOT NULL REFERENCES plot_threads(id) ON DELETE CASCADE,
    description             TEXT NOT NULL,
    is_discovered           INTEGER NOT NULL DEFAULT 0,
    discovered_session_id   INTEGER REFERENCES sessions(id),
    discovered_by_character_id INTEGER REFERENCES characters(id),
    source_description      TEXT,    -- Where/how the clue can be found
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_clues_plot ON plot_clues(plot_thread_id);
CREATE INDEX idx_clues_discovered ON plot_clues(is_discovered);

-- ============================================================================
-- PLOT CHARACTERS (who is involved in which plot)
-- ============================================================================

CREATE TABLE IF NOT EXISTS plot_characters (
    plot_thread_id  INTEGER NOT NULL REFERENCES plot_threads(id) ON DELETE CASCADE,
    character_id    INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    role_in_plot    TEXT NOT NULL CHECK (role_in_plot IN (
                        'protagonist', 'antagonist', 'witness', 'victim',
                        'informant', 'suspect', 'bystander', 'target'
                    )),
    notes           TEXT,
    PRIMARY KEY (plot_thread_id, character_id)
);

CREATE INDEX idx_plot_char_character ON plot_characters(character_id);

-- ============================================================================
-- SESSIONS
-- ============================================================================

CREATE TABLE IF NOT EXISTS sessions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    era_id              INTEGER REFERENCES era_summaries(id),  -- NULL if current era
    session_number      INTEGER NOT NULL,
    start_real_time     TEXT NOT NULL DEFAULT (datetime('now')),
    end_real_time       TEXT,
    in_game_date_start  TEXT,
    in_game_date_end    TEXT,
    summary             TEXT,           -- Compressed summary (filled at session end or archival)
    is_archived         INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_sessions_era ON sessions(era_id);
CREATE INDEX idx_sessions_archived ON sessions(is_archived);
CREATE INDEX idx_sessions_number ON sessions(session_number);

-- ============================================================================
-- SESSION EVENTS
-- ============================================================================

CREATE TABLE IF NOT EXISTS session_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_order     INTEGER NOT NULL,    -- Sequential within session
    event_type      TEXT NOT NULL CHECK (event_type IN (
                        'narrative', 'combat', 'dialogue', 'discovery', 'travel',
                        'rest', 'vision', 'trade', 'social', 'stealth', 'death',
                        'level_up', 'world_change', 'other'
                    )),
    description     TEXT NOT NULL,
    location_id     INTEGER REFERENCES locations(id),
    in_game_time    TEXT,               -- "1525-03-14 14:30" format
    importance      INTEGER DEFAULT 3 CHECK (importance BETWEEN 1 AND 5),
    raw_dm_text     TEXT,               -- The actual narration sent to the player
    participants    TEXT DEFAULT '[]',   -- JSON array of character IDs involved
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_events_session ON session_events(session_id);
CREATE INDEX idx_events_type ON session_events(event_type);
CREATE INDEX idx_events_importance ON session_events(importance);

-- ============================================================================
-- DICE ROLLS (high-volume, prunable)
-- ============================================================================

CREATE TABLE IF NOT EXISTS dice_rolls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    event_id        INTEGER REFERENCES session_events(id) ON DELETE SET NULL,
    roller_type     TEXT NOT NULL CHECK (roller_type IN ('player', 'dm', 'system')),
    character_id    INTEGER REFERENCES characters(id) ON DELETE SET NULL,
    roll_type       TEXT NOT NULL CHECK (roll_type IN (
                        'ability_check', 'saving_throw', 'attack', 'damage',
                        'initiative', 'death_save', 'table_roll', 'custom',
                        'skill_check', 'concentration', 'wild_magic', 'hit_dice'
                    )),
    expression      TEXT NOT NULL,      -- "1d20+8", "2d6+4", "1d100"
    individual_dice TEXT DEFAULT '[]',  -- JSON: [14, 3, 6] — each die result
    natural_roll    INTEGER,            -- The raw d20 (for crits/fumbles), NULL for non-d20
    total           INTEGER NOT NULL,
    modifiers_applied TEXT DEFAULT '{}', -- JSON: {"proficiency": 6, "ability": 5, "advantage": true}
    purpose         TEXT,               -- "Perception check to spot the assassin"
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_dice_session ON dice_rolls(session_id);
CREATE INDEX idx_dice_event ON dice_rolls(event_id);
CREATE INDEX idx_dice_character ON dice_rolls(character_id);
CREATE INDEX idx_dice_created ON dice_rolls(created_at);

-- ============================================================================
-- COMBAT ENCOUNTERS
-- ============================================================================

CREATE TABLE IF NOT EXISTS combat_encounters (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id              INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    location_id             INTEGER REFERENCES locations(id),
    initiative_order        TEXT DEFAULT '[]',   -- JSON: [{character_id, initiative, is_surprised}]
    combatants              TEXT DEFAULT '[]',   -- JSON: [{character_id, hp_start, hp_current, conditions, side}]
    current_round           INTEGER DEFAULT 0,
    current_turn_index      INTEGER DEFAULT 0,
    status                  TEXT NOT NULL DEFAULT 'active' CHECK (status IN (
                                'active', 'resolved', 'fled', 'interrupted'
                            )),
    outcome_summary         TEXT,
    loot                    TEXT DEFAULT '[]',   -- JSON array of items/gold
    started_at              TEXT NOT NULL DEFAULT (datetime('now')),
    ended_at                TEXT
);

CREATE INDEX idx_combat_session ON combat_encounters(session_id);
CREATE INDEX idx_combat_status ON combat_encounters(status);

-- ============================================================================
-- CUSTOM MECHANICS (extensible rule store)
-- ============================================================================

CREATE TABLE IF NOT EXISTS custom_mechanics (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    category        TEXT NOT NULL CHECK (category IN (
                        'intoxication', 'talent', 'weather', 'oracle',
                        'guild', 'combat_house_rule', 'leveling', 'other'
                    )),
    rule_data       TEXT NOT NULL,       -- JSON: the full rule definition
    description     TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_mechanics_category ON custom_mechanics(category);
CREATE INDEX idx_mechanics_name ON custom_mechanics(name);

-- ============================================================================
-- GUILD CONTRACTS (Gilded Gauntlet contract economy)
-- ============================================================================

CREATE TABLE IF NOT EXISTS guild_contracts (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    title               TEXT NOT NULL,
    description         TEXT,
    cr_tier             INTEGER,             -- Recommended CR
    rank_required       TEXT CHECK (rank_required IN (
                            'copper', 'brass', 'bronze', 'silver', 'gold', 'platinum', 'world'
                        )),
    stake_gt            INTEGER NOT NULL,    -- Guild Tokens staked
    reward_gt           INTEGER NOT NULL,    -- Guild Tokens rewarded
    reward_gp           REAL NOT NULL,       -- Gold rewarded
    status              TEXT NOT NULL DEFAULT 'available' CHECK (status IN (
                            'available', 'claimed', 'exclusive', 'completed',
                            'failed', 'expired', 'cancelled'
                        )),
    claimed_by_character_id INTEGER REFERENCES characters(id),
    claimed_at          TEXT,
    exclusive_until     TEXT,                -- For Law of Limited Exclusivity
    posted_session_id   INTEGER REFERENCES sessions(id),
    completed_session_id INTEGER REFERENCES sessions(id),
    notes               TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_contracts_status ON guild_contracts(status);
CREATE INDEX idx_contracts_rank ON guild_contracts(rank_required);
CREATE INDEX idx_contracts_claimed ON guild_contracts(claimed_by_character_id);

-- ============================================================================
-- GUILD TOKEN LEDGER (transactional audit trail)
-- ============================================================================

CREATE TABLE IF NOT EXISTS guild_token_ledger (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id    INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
    amount          INTEGER NOT NULL,    -- Positive = credit, negative = debit
    balance_after   INTEGER NOT NULL,    -- Running balance
    reason          TEXT NOT NULL,
    contract_id     INTEGER REFERENCES guild_contracts(id),
    session_id      INTEGER REFERENCES sessions(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_gt_ledger_character ON guild_token_ledger(character_id);
CREATE INDEX idx_gt_ledger_contract ON guild_token_ledger(contract_id);

-- ============================================================================
-- ERA SUMMARIES (archival)
-- ============================================================================

CREATE TABLE IF NOT EXISTS era_summaries (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    era_name                TEXT NOT NULL,
    era_number              INTEGER NOT NULL,
    start_session_id        INTEGER NOT NULL REFERENCES sessions(id),
    end_session_id          INTEGER NOT NULL REFERENCES sessions(id),
    summary_text            TEXT NOT NULL,        -- Multi-paragraph narrative digest
    key_outcomes            TEXT DEFAULT '[]',    -- JSON array of major outcomes
    key_characters          TEXT DEFAULT '[]',    -- JSON array of character IDs who were central
    world_state_snapshot    TEXT DEFAULT '{}',    -- JSON: political state, faction standings at era end
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_era_number ON era_summaries(era_number);

-- ============================================================================
-- Initialize world state singleton
-- ============================================================================

INSERT INTO world_state (id, current_date, current_hour, season, political_summary)
VALUES (1, '1525-01-01', 8, 'winter',
    'Baldur''s Gate is governed by the Council of Four: Grand Duchess Jade Ravenshade, Duchess Olivia Caldwell, Duke Oriel Redlocks, and Duke Phillipe-Michael Vammas. The Flaming Fist maintains order. The Blue Dagger controls the underworld. The Gilded Gauntlet operates from Bloomridge.');

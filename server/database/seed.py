#!/usr/bin/env python3
"""
Seed script for Naelia's Chronicles.
Populates the SQLite database with all characters, organizations, locations,
custom mechanics, plot threads, and world history extracted from the campaign PDFs.

Usage:
    python -m server.database.seed          # from project root
    python server/database/seed.py          # direct execution
"""

import json
import sqlite3
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from server.config import DB_PATH, SCHEMA_PATH


def j(obj) -> str:
    """Shorthand for JSON serialization."""
    return json.dumps(obj, ensure_ascii=False)


def seed_database():
    """Main seeding function."""
    # Remove existing DB and recreate
    if DB_PATH.exists():
        DB_PATH.unlink()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA foreign_keys = ON")

    # Create schema
    schema_sql = SCHEMA_PATH.read_text()
    db.executescript(schema_sql)

    # Seed in order (respecting FK constraints)
    seed_locations(db)
    seed_organizations(db)
    seed_characters(db)
    seed_org_memberships(db)
    seed_character_relationships(db)
    seed_org_relationships(db)
    seed_items(db)
    seed_custom_mechanics(db)
    seed_weather_tables(db)
    seed_world_history(db)
    seed_plot_threads(db)
    seed_guild_contracts(db)
    seed_npc_schedules(db)

    db.commit()
    db.close()
    print(f"Database seeded successfully at {DB_PATH}")
    print(f"Size: {DB_PATH.stat().st_size / 1024:.1f} KB")


# ============================================================================
# LOCATIONS
# ============================================================================

def seed_locations(db: sqlite3.Connection):
    """Seed the location hierarchy."""
    c = db.cursor()
    locs = [
        # Planes
        (1, "Material Plane", None, "plane", "The prime material plane where Toril exists."),
        (2, "Astral Plane", None, "plane", "The silvery void between planes, home to Seraphine's Palace."),
        (3, "Feywild", None, "plane", "Echo of the Material Plane, vibrant with fey magic."),
        (4, "Arvandor", None, "plane", "The elven afterlife and divine realm of the Seldarine."),
        (5, "Avernus", None, "plane", "First layer of the Nine Hells, ruled by Archdevil Yalas."),
        (6, "Abyss", None, "plane", "Infinite layers of demonic chaos. Home of Lolth's Demonweb Pits."),

        # Worlds
        (10, "Toril", 1, "world", "The planet on which Faerun and other continents exist."),

        # Continents
        (20, "Faerun", 10, "continent", "The western continent of Toril, primary setting."),

        # Regions
        (30, "Sword Coast", 20, "region", "Western coastal region of Faerun, from Luskan to Baldur's Gate."),

        # Cities
        (100, "Baldur's Gate", 30, "city", "A sprawling metropolis on the Sword Coast, one of the largest cities in Faerun. Built on steeply sloping terrain along the Chionthar River harbor."),
        (101, "Waterdeep", 30, "city", "The City of Splendors, largest city on the Sword Coast."),
        (102, "Neverwinter", 30, "city", "The Jewel of the North, rebuilt after the cataclysm."),
        (103, "Luskan", 30, "city", "A port city in the north, once a pirate haven."),
        (104, "Suzail", 20, "city", "Capital of Cormyr, home of the Brass Scales guild."),
        (105, "Calimport", 20, "city", "Capital of Calimshan, home of the Wardens of the Sand guild."),

        # Baldur's Gate Districts
        (200, "Upper City", 100, "district", "Home to the patriar aristocracy, protected by The Watch. Non-residents expelled at nightfall unless holding Watch tokens. Beautiful, wealthy, and tightly controlled."),
        (201, "Lower City", 100, "district", "The commercial heart of Baldur's Gate, between the Upper City and the harbor. Dense tangle of buildings with narrow streets."),
        (202, "Outer City", 100, "district", "Sprawling settlements outside the main walls. The poorest district, home to refugees, tanneries, and stockyards."),
        (203, "Undercity", 100, "district", "Extensive partially flooded tunnel network under Baldur's Gate, built in decommissioned water drainage system. Controlled by the Blue Dagger."),

        # Upper City Neighborhoods
        (210, "Citadel Streets", 200, "district", "Northern Upper City dominated by the Watch Citadel with barracks, training grounds, and jail cells."),
        (211, "Manorborn", 200, "district", "Western Upper City with the Parliament of Peers and the most palatial residences."),
        (212, "Temples", 200, "district", "Central Upper City district with grand cathedrals including Gond's High House of Wonders."),
        (213, "The Wide", 200, "district", "Primary market and largest civic space in the Upper City. Non-residents sell here during the day."),

        # Lower City Neighborhoods
        (220, "Bloomridge", 201, "district", "Wealthiest Lower City area with upscale boutiques and rooftop gardens. Home to the Gilded Gauntlet guildhall."),
        (221, "Brampton", 201, "district", "Easternmost Lower City, notoriously poor, good for smuggling."),
        (222, "Eastway", 201, "district", "Near Basilisk Gate, gateway for travelers, dangerous due to crime."),
        (223, "Heapside", 201, "district", "Middle-class residential area in the Lower City."),
        (224, "Seatower", 201, "district", "Military area around the Seatower of Balduran, full of Flaming Fist members."),
        (225, "The Steeps", 201, "district", "Steep thoroughfares connecting the harbor to the Upper City, home to successful merchants."),
        (226, "Gray Harbor", 201, "district", "The harbor district along the Chionthar River."),

        # Outer City Neighborhoods
        (230, "Blackgate", 202, "district", "Beyond Black Dragon Gate, serves travelers on the Trade Way to Waterdeep."),
        (231, "Little Calimshan", 202, "district", "Walled Calishite community in the Outer City."),
        (232, "Norchapel", 202, "district", "Quietest Outer City neighborhood, pays protection money to the Guild."),
        (233, "Rivington", 202, "district", "Self-contained village of anglers, dominated by the Rivington Rats gang, a smuggling haven."),
        (234, "Sow's Foot", 202, "district", "Diverse area with expatriates from far-flung nations."),
        (235, "Stonyeyes", 202, "district", "Near Basilisk Gate, full of stables and stockyards."),
        (236, "Tumbledown", 202, "district", "Foggy area overlooking the river with Cliffside Cemetery."),
        (237, "Twin Songs", 202, "district", "Diverse religious area with shrines from every faith."),
        (238, "Whitkeep", 202, "district", "Home to the city's largest gnome enclave, artists, and tanneries."),
        (239, "Wyrm's Crossing", 202, "district", "Massive bridge across the Chionthar River, with shops and homes along its edges."),

        # Undercity Areas
        (240, "Silver Quarter", 203, "district", "Northern Undercity under Upper City/Steeps. Clean, dry, maintained tunnels. Caters to elite with goods unavailable on the surface."),
        (241, "The Mudway", 203, "district", "Still-functional flooded tunnels with treacherous inclined walkways covered in mud."),
        (242, "The Underriver", 203, "district", "Water drainage system of cisterns, aqueducts, and mechanisms."),
        (243, "Mudbrook", 203, "district", "Undercity section beneath Eastway, Heapside, Stonyeyes."),
        (244, "The Lost Quarter", 203, "district", "Under the docks, almost completely flooded."),

        # Key Buildings
        (300, "Gilded Gauntlet Guildhall", 220, "building", "Three-story restored estate in Bloomridge. Ground floor: main hall with contract boards, fireplace, four teller desks. Second floor: administration and Guildmaster's office. Guarded at all times by veteran adventurers."),
        (301, "The High Hall", 212, "building", "Former central bastion turned governmental center. Contains duke offices, Parliament chamber (gallery seats 300), court chambers, libraries, feasting hall, public garden, museum/mausoleum with Balduran's relics."),
        (302, "Seatower of Balduran", 224, "building", "Five stout towers on a rocky islet in the harbor. Massive chain to Brampton wharf. ~100 soldiers. Contains armory, kitchens, officers' tower, prison with 3 dungeon levels."),
        (303, "Wyrm's Rock", 239, "building", "Foot-thick granite fortress on a river islet. First checkpoint for taxing northbound travelers. Central tunnel with arrow slits and murder holes."),
        (304, "Lady's Hall", 211, "building", "Temple of Tymora in Manorborn district. One of the wealthiest temples in the city. Oceanic/nautical theme. Hidden entrance to the Silver Quarter beneath a stone pillar."),
        (305, "The Low Lantern", 226, "building", "Three-masted, three-decked ship permanently docked at Eastway docks. First deck: tavern. Second deck: gambling house. Third deck: restricted."),
        (306, "Tara's Magic Shop", 240, "building", "Small nameless magic shop deep in the Silver Quarter. Sells charms, trinkets, curses. Run by Tara."),
        (307, "The Colosseum", 240, "building", "Repurposed massive water cistern beneath the Silver Quarter. Arena floor 20 feet below wooden scaffold walkway. Tiered benches on western wall."),
        (308, "Melissa's Cove", 240, "building", "Famed pleasure house in the middle of the Silver Quarter. Run by Melissa."),
        (309, "Elfsong Tavern", 222, "building", "Famous tavern in Eastway, known for the ghostly elven song that plays at odd hours."),
        (310, "Watch Citadel", 210, "building", "Headquarters of The Watch in the Upper City."),
        (311, "Ravenshade Estate", 211, "building", "Patriar mansion of the Ravenshade family in Manorborn."),
        (312, "Vammas Estate", 211, "building", "Patriar mansion of the Vammas family in Manorborn."),
        (313, "Caldwell Estate", 211, "building", "Patriar mansion of the Caldwell family in Manorborn."),
        (314, "Redlocks Estate", 211, "building", "Patriar mansion of the Redlocks family in Manorborn."),

        # Extraplanar Locations
        (400, "Seraphine's Palace", 2, "building", "Island in an Astral Dominion forged by Seraphine. Only visible to those who know of it. Warded with Epic Magic. Over 1,000 followers. Time does not affect residents."),
        (401, "Seraphine's Glade", 400, "room", "Misty glade within Seraphine's Palace where she has absolute control over reality. Her lair."),
        (402, "Crypt of the Forgotten", 100, "dungeon", "Dangerous dungeon near Baldur's Gate guarded by Ommell Siobarek. Naelia receives tribute from it."),
        (403, "Demonweb Pits", 6, "building", "Lolth's domain in the 66th layer of the Abyss."),

        # Wilderness
        (500, "Cloak Wood", 30, "wilderness", "Dense forest south of Baldur's Gate. Home to Mad Lula Soilmind's swamp shack."),
        (501, "Mad Lula's Shack", 500, "building", "A hag's shack in a swamp of the Cloak Wood. Lures lost adventurers."),
        (502, "Sunset Mountains", 20, "wilderness", "Mountain range east of the Sword Coast. Hidden monastery of the Third Lotus."),
        (503, "Third Lotus Monastery", 502, "building", "Hidden monastery deep in the Sunset Mountains. Over 1,000 years old. Exact location unknown."),
    ]

    c.executemany(
        "INSERT INTO locations (id, name, parent_id, type, description) VALUES (?, ?, ?, ?, ?)",
        locs
    )
    print(f"  Seeded {len(locs)} locations")


# ============================================================================
# ORGANIZATIONS
# ============================================================================

def seed_organizations(db: sqlite3.Connection):
    """Seed all organizations and sub-organizations."""
    c = db.cursor()
    orgs = [
        # (id, name, parent_org_id, type, description, hq_location_id, symbol_desc, is_secret, treasury)
        (1, "Gilded Gauntlet", None, "guild",
         "Over 500-year-old adventurer's guild and holy order. 8,000 registered members, 17 Gold ranked. Sister organizations in every major city. Secretly founded and ruled by Seraphine as 'Arthenia, Lady of the Guild'.",
         300, "A golden armored gauntlet clenching a torch", 0, 6804957000),

        (2, "The Silver Fist", 1, "military",
         "Paladins and Clerics protecting the faith of the Gilded Gauntlet. Guard the guildhall and shrines. Gleaming armor, white cloaks. 8-12 level paladins (Order/Devotion).",
         300, None, 0, 0),

        (3, "The Right Hand", 1, "military",
         "Only Gold Coin bearers. Smallest but most prestigious holy order. Personal protection of prominent faith members. Golden magical armor, powerful magical weapons. 16-19 level Oath of Glory/Devotion/Order/Protection Paladins.",
         300, None, 0, 0),

        (4, "The Other Hand", 1, "secret",
         "Secret order within the Gilded Gauntlet, considered a myth by many. Recruited from Fingers. Vow of secrecy. Best trackers and investigators. Vengeance against the Lady's enemies. Dual-classed Vengeance Paladins/Assassins and Trickery Clerics.",
         300, None, 1, 0),

        (5, "Iron Grip", 1, "guild",
         "Largest company in the Gilded Gauntlet. 3,000+ members, no rank requirement. 10 Silver, 4 Gold members. Captain: Brilleris Gakigum.",
         300, None, 0, 0),

        (6, "Purple Hand", 1, "guild",
         "Most prestigious company in the Gilded Gauntlet. ~700 members, Brass minimum entry. Trials by specialty. 15 Silver, 6 Gold members. Captain: Dimlies. Founded by Dimlies.",
         300, None, 0, 0),

        (7, "Golden Pixies", 1, "guild",
         "107 members (under 15 male). Bronze+ healers only. 3 Silver ranks. Lend services to low-rank parties for minimal reward. Expert at fighting undead/fiends.",
         300, None, 0, 0),

        (8, "The Red Rose", 1, "secret",
         "Assassin company within the Gilded Gauntlet. No way to leave. 3 members who tried to leave or sell secrets disappeared along with anyone suspected of hearing them.",
         300, None, 1, 0),

        (10, "Blue Dagger", None, "criminal",
         "Criminal syndicate dominating all illicit activities in Baldur's Gate. Led by The Beast (Razaaz, a Rakshasa). Has agents in the Flaming Fist, The Watch, and Parliament. Four semi-independent Kingpins govern city territories.",
         None, None, 0, 0),

        (11, "Coven of Webs", None, "secret",
         "Secretive demon-worshipping witch coven in Baldur's Gate. Worships Lolth. 4 Mothers (leaders), 7 Aunts (admins), many Daughters. Periodically sacrifices young elves to be transformed into spiders or Driders.",
         None, "A pointed star with webbed points and a red-eyed center", 1, 0),

        (12, "Cult of Vecna", None, "secret",
         "Secretive cult devoted to the demigod Vecna. Reborn centuries after believed disbanded. Hierarchy named for body parts. Common initiation: gouge out left eye and amputate left hand.",
         None, None, 1, 0),

        (13, "Council of Four", None, "political",
         "Executive governing body of Baldur's Gate. Four Dukes elected for life by Parliament of Peers. One serves as Grand Duke. Seat: The High Hall.",
         301, None, 0, 0),

        (14, "Parliament of Peers", 13, "political",
         "~50 patriar members. Legislative/advisory body. Known for corruption (bribes hidden in cheap jewelry and fake art).",
         301, None, 0, 0),

        (15, "The Flaming Fist", None, "military",
         "Mercenary company serving as Baldur's Gate's city military and police force. Headquartered at the Seatower of Balduran with secondary bastion at Wyrm's Rock.",
         302, None, 0, 0),

        (16, "The Watch", None, "military",
         "Upper City police force. Enforces strict rules including expelling non-residents at nightfall. Reports to the High Constable.",
         310, None, 0, 0),

        (17, "Knights of the Shield", None, "secret",
         "Information dealers and political manipulators. Operated along the Sword Coast for over 1,000 years. One of the most popular intelligence suppliers in Baldur's Gate.",
         None, None, 1, 0),

        (18, "Third Lotus", None, "secret",
         "Ancestral clan of monk-assassins. Hidden monastery deep in the Sunset Mountains. Over 1,000 years old. No known way to contact them. A whisper exists that Yuuto Ravenshade earned the ire of the Lotus.",
         503, "Three-petaled lotus inside a circle", 1, 0),

        (19, "Bloodveil Syndicate", None, "criminal",
         "Assassin collective from Northern/Western Faerun. Came to prominence 1324 DR in Neverwinter. Crippled after the Bloody Years of Reckoning when members were hunted by the Gilded Gauntlet (1501-1507).",
         None, "Circular design with blood-red veil, glowing red eyes, thorn-patterned ring", 0, 0),

        (20, "Caldwell Family", None, "noble_house",
         "Patriar family. Originally made fortune from apple/pear orchards. Expanded into timber, shipping, and now magical items and potions under the Caldwell brand. Also operates 'Olivia's Secret' fine linen line.",
         313, None, 0, 0),

        (21, "Ravenshade Dynasty", None, "noble_house",
         "Patriar family with Waan-Shou heritage. Grand Duchess Jade Ravenshade leads the Council of Four. The family has estates in both Baldur's Gate and Cormyr. Dynasty heir is Daisuke in Cormyr; Baldur's Gate heir is Arnalithah.",
         311, None, 0, 0),

        (22, "Vammas Family", None, "noble_house",
         "Patriar family. Duke Phillipe-Michael Vammas sits on the Council of Four. Heir: Delilah Vammas.",
         312, None, 0, 0),

        (23, "Redlocks Family", None, "noble_house",
         "Patriar family. Duke Oriel Redlocks sits on the Council of Four and serves as Marshal of the Flaming Fist. Wife Aisha assassinated in 1501 during the Bloodveil Conspiracy.",
         314, None, 0, 0),

        # Alliance guilds
        (24, "The Ice Shield", None, "guild", "Sister guild of the Gilded Gauntlet in Waterdeep.", None, None, 0, 0),
        (25, "The Brass Scales", None, "guild", "Sister guild of the Gilded Gauntlet in Suzail.", None, None, 0, 0),
        (26, "The Wardens of the Sand", None, "guild", "Sister guild of the Gilded Gauntlet in Calimport.", None, None, 0, 0),
    ]

    c.executemany(
        """INSERT INTO organizations (id, name, parent_org_id, type, description,
           headquarters_location_id, symbol_description, is_secret, treasury_gp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        orgs
    )
    print(f"  Seeded {len(orgs)} organizations")


# ============================================================================
# CHARACTERS
# ============================================================================

def seed_characters(db: sqlite3.Connection):
    """Seed all characters. This is the largest seeding function."""
    c = db.cursor()

    characters = _build_all_characters()

    for char in characters:
        cols = ", ".join(char.keys())
        placeholders = ", ".join(["?"] * len(char))
        vals = list(char.values())
        c.execute(f"INSERT INTO characters ({cols}) VALUES ({placeholders})", vals)

    print(f"  Seeded {len(characters)} characters")


def _build_all_characters() -> list[dict]:
    """Build the full list of character dicts for insertion."""
    chars = []

    # ---- PC: Naelia An'Ohren ----
    chars.append({
        "id": 1, "name": "Naelia An'Ohren",
        "aliases": j(["Avatar of the Lady", "Silver Queen", "Mithral Queen"]),
        "type": "pc", "race": "Eladrin", "creature_type": "celestial",
        "sex": "Female", "alignment": "Chaotic Neutral", "age": 2628, "cr": 100,
        "class_levels": j({}), "talent_tier": 3, "background": "God",
        "str": 13, "dex": 56, "con": 53, "int": 67, "wis": 70, "cha": 70,
        "hp_max": 2550, "hp_current": 2550, "ac": 55,
        "speed": "30 ft., 220 ft. fly, 90 ft. swim",
        "proficiency_bonus": 26,
        "saves_proficient": j(["dex", "con", "int", "wis", "cha"]),
        "skills": j({
            "Arcana": {"bonus": 80}, "Insight": {"bonus": 82}, "History": {"bonus": 80},
            "Investigation": {"bonus": 54}, "Medicine": {"bonus": 56}, "Perception": {"bonus": 82},
            "Persuasion": {"bonus": 56}, "Sleight of Hand": {"bonus": 23}
        }),
        "languages": j(["All"]),
        "damage_resistances": j(["lightning", "fire", "cold", "acid", "necrotic"]),
        "damage_immunities": j(["non-magical bludgeoning", "non-magical piercing", "non-magical slashing", "radiant", "psychic", "poison"]),
        "condition_immunities": j(["blinded", "charmed", "deafened", "diseased", "frightened", "grappled", "incapacitated", "paralyzed", "petrified", "poisoned", "prone", "sleep", "exhaustion"]),
        "senses": j({"blindsight": 30, "truesight": 240, "passive_perception": 92}),
        "spellcasting_ability": "cha", "spell_save_dc": 64, "spell_attack_mod": 56,
        "innate_spells": j({
            "at_will": ["Wish"],
            "5/round": ["True Resurrection", "True Polymorph", "Time Stop", "Power Word Kill", "Meteor Swarm", "Mass Heal", "Gate", "Astral Projection"]
        }),
        "special_abilities": j([
            {"name": "Divine Oracle", "description": "Range 120 ft. Read thoughts, see immediate future. Advantage on all saves/checks. Attackers have disadvantage. Cannot be surprised. Knows when lied to."},
            {"name": "Greater Magic Immunity", "description": "Advantage on saves vs spells level 6+. Immune to lesser magic and magical effects."},
            {"name": "Divine Wish", "description": "No ill effects from Wish. Thinks a wish for reality to bend exactly as intended."},
            {"name": "Divine Magic", "description": "12 divine points for epic magic (level 10-12 spells). Recharges on long rest."},
            {"name": "Legendary Resistance", "description": "5/round. Choose to succeed on failed saves."},
            {"name": "Oracle's Burden", "description": "Nightly visions during long rest. Vivid scenes from past or future through a mortal's mind. Can act on elements as if real (free teleportation to seen places)."}
        ]),
        "actions": j([
            {"name": "Slap", "type": "melee_spell", "to_hit": 49, "damage": "1d4+23 necrotic", "extra": "DC 64 CON or reduced to 0 HP"},
            {"name": "Healing Touch", "type": "healing", "uses": "5/round", "healing": "8d8+4", "extra": "Removes curse, disease, poison, blindness, deafness"},
            {"name": "Cast Superior Shield", "type": "spell", "description": "20-ft radius sphere, absorbs 120 damage, full cover from outside attacks"}
        ]),
        "legendary_actions": j({"per_round": 3, "actions": [
            {"name": "Cast Spell", "cost": 1, "description": "Cast any spell level 8 and below. Or expend divine points for higher."},
            {"name": "Healing Touch", "cost": 1},
            {"name": "Teleport", "cost": 1, "description": "Teleport up to 120 feet."}
        ]}),
        "reactions": j([
            {"name": "Counterspell", "description": "DC 64 save or silenced until start of next turn."},
            {"name": "Antimagic Area", "description": "30-ft radius antimagic sphere."},
            {"name": "Cast Superior Shield", "description": "20-ft radius, 120 damage absorption, full cover."}
        ]),
        "current_location_id": 100,
        "status": "alive",
        "guild_rank": None, "guild_tokens": 0,
        "lifestyle_daily_gp": 156176,
        "wealth_gp": 57004240,
        "importance": 1, "is_public": 1,
        "appearance_text": "A demi-goddess with elven blood. Clad in a flowing, translucent golden elven gown woven from moonlight and mist. Long silver hair in an elegant loose braid with silver jewellery. Short pointed ears. Luminous hair. Striking grey-silver eyes reflecting wisdom and ageless beauty. Divine elegance and natural grace.",
        "backstory_text": "Daughter of Angharradh the Queen of Arvandor and her eladrin consort. Carries the full powers of a god in an eladrin body. Spent first 500 years in the Feywild in her father's castle. Later joined her mother in Arvandor where her powers matured for over two millennia. Now bonded with Seraphine via the Gowns of Power, forming a being past greater godhood.",
        "personality_text": "Whimsical yet wise. Carries the weight of divine knowledge. Curious about mortal affairs. Her Oracle's Burden gives her deep empathy for mortal struggles.",
        "voice_notes": "Speaks with calm authority but occasional playfulness. Uses 'we' sometimes when Seraphine's influence is strong.",
    })

    # ---- PC: Seraphine ----
    chars.append({
        "id": 2, "name": "Seraphine",
        "aliases": j(["Arthenia", "Lady of the Guild", "Lady of the Gauntlet", "Harpist of the Veil"]),
        "type": "pc", "race": "Archfey", "creature_type": "fey",
        "sex": "Female", "alignment": "Chaotic Neutral", "age": 2570, "cr": 35,
        "class_levels": j({}), "talent_tier": 3, "background": "Archfey",
        "str": 10, "dex": 17, "con": 16, "int": 27, "wis": 30, "cha": 38,
        "hp_max": 622, "hp_current": 622, "ac": 19,
        "speed": "30 ft.",
        "proficiency_bonus": 8,
        "saves_proficient": j(["dex", "con", "int", "wis", "cha"]),
        "skills": j({
            "Arcana": {"bonus": 24}, "Deception": {"bonus": 30}, "History": {"bonus": 16},
            "Insight": {"bonus": 18}, "Medicine": {"bonus": 26}, "Nature": {"bonus": 24},
            "Persuasion": {"bonus": 14}, "Animal Handling": {"bonus": 26}, "Religion": {"bonus": 24}
        }),
        "languages": j(["All"]),
        "damage_resistances": j(["cold", "fire", "force", "lightning", "necrotic", "poison", "psychic", "radiant", "thunder", "acid"]),
        "damage_immunities": j(["non-magical bludgeoning", "non-magical piercing", "non-magical slashing"]),
        "condition_immunities": j(["charmed", "diseased", "frightened", "grappled", "incapacitated", "petrified", "paralyzed", "prone", "restrained", "stunned", "sleep", "exhaustion"]),
        "senses": j({"blindsight": 60, "truesight": 120, "passive_perception": 20}),
        "spellcasting_ability": "cha", "spell_save_dc": 30, "spell_attack_mod": 22,
        "spell_slots": j({"6": 7, "7": 7, "8": 7, "9": 5}),
        "spells_known": j({
            "cantrips": ["Dancing Lights", "Light", "Mage Hand", "Mending", "Message", "Minor Illusion", "Prestidigitation", "True Strike", "Vicious Mockery"],
            "at_will_1": ["Animal Friendship", "Bane", "Charm Person", "Comprehend Languages", "Cure Wounds", "Detect Magic", "Disguise Self", "Faerie Fire", "Feather Fall", "Healing Word", "Heroism", "Identify", "Illusory Script", "Longstrider", "Silent Image", "Sleep", "Speak with Animals", "Hideous Laughter", "Thunderwave", "Unseen Servant"],
            "at_will_2": ["Animal Messenger", "Blindness/Deafness", "Calm Emotions", "Detect Thoughts", "Enhance Ability", "Enthrall", "Heat Metal", "Hold Person", "Invisibility", "Knock", "Lesser Restoration", "Locate Animals or Plants", "Locate Object", "Magic Mouth", "See Invisibility", "Shatter", "Silence", "Suggestion", "Zone of Truth"],
            "at_will_3": ["Bestow Curse", "Clairvoyance", "Dispel Magic", "Fear", "Glyph of Warding", "Hypnotic Pattern", "Tiny Hut", "Major Image", "Nondetection", "Plant Growth", "Sending", "Speak with Dead", "Speak with Plants", "Stinking Cloud", "Tongues"],
            "at_will_4": ["Compulsion", "Confusion", "Dimension Door", "Freedom of Movement", "Greater Invisibility", "Hallucinatory Terrain", "Locate Creature", "Polymorph"],
            "at_will_5": ["Animate Objects", "Awaken", "Dominate Person", "Dream", "Geas", "Greater Restoration", "Hold Monster", "Legend Lore", "Mass Cure Wounds", "Mislead", "Modify Memory", "Planar Binding", "Raise Dead", "Scrying", "Seeming", "Teleportation Circle"],
            "6": ["Eyebite", "Find the Path", "Guards and Wards", "Mass Suggestion", "Irresistible Dance", "Programmed Illusion", "True Seeing"],
            "7": ["Etherealness", "Forcecage", "Mirage Arcane", "Magnificent Mansion", "Arcane Sword", "Project Image", "Regenerate", "Resurrection", "Symbol", "Teleport"],
            "8": ["Dominate Monster", "Feeblemind", "Glibness", "Mind Blank", "Power Word Stun"],
            "9": ["Foresight", "Power Word Kill", "True Polymorph"]
        }),
        "special_abilities": j([
            {"name": "Aura of Serenity", "description": "Creatures within 30 ft have disadvantage on saves vs charmed/frightened. Can end those conditions on chosen creatures at start of turn."},
            {"name": "True Lair Immortality", "description": "Cannot be killed in her glade, even by Wish. If HP reach 0 in glade, reality reorganizes and events reverse."},
            {"name": "Telepathic", "description": "Read thoughts of anyone she can see. Communicate telepathically even through scrying. Sending without message length limits. Verbal components of spells can be omitted."},
            {"name": "Communion with Naelia", "description": "Via the Gowns of Power, she and Naelia are two faces of the same being, past greater godhood."}
        ]),
        "legendary_actions": j({"per_round": 5, "actions": [
            {"name": "Cast Spell", "cost": 1, "description": "Cast any prepared spell of level 7 and below."}
        ]}),
        "lair_actions": j([
            {"name": "True Invisibility", "description": "Invisible to chosen creatures. True Sight creatures: DC 30 WIS or blinded 1 day."},
            {"name": "Melody of Dread", "description": "Each hostile within 120 ft: DC 30 WIS or frightened 1 minute."},
            {"name": "Melody of Life", "description": "Each chosen within 120 ft: recover 50+6d8 HP, freed from negative effects. Revive corpses <1 month old."},
            {"name": "Melody of Truth", "description": "Each creature within 120 ft: DC 30 INT or beneficial magic dispelled."},
            {"name": "Melody of Whims", "description": "Lyrics have effect of Wish. Cannot fail or backfire. Only within glade."},
            {"name": "Phantasmal Harpstrings", "description": "Invisible strings within 60 ft. DC 30 DEX with disadvantage or restrained."},
            {"name": "Overwhelming Authority", "description": "Any save or roll she makes has advantage in her glade."}
        ]),
        "current_location_id": 400,
        "status": "alive",
        "importance": 1, "is_public": 0,
        "appearance_text": "Ethereal, hauntingly beautiful young woman with otherworldly charm. Flowing translucent gown woven from moonlight and mist. Jet black hair cascading in waves. Eyes that glow with soft luminescent amber/orange light. Carries a delicate ornately carved harp.",
        "backstory_text": "Born in the Feywild to the first daughter of the legendary Archfey Titania. Developed a liking to elf songs and harp magic. Donned the mantle of Arthenia over two centuries ago, tricking the first Guildmaster through dreams and visions. She is the real authority behind the Gilded Gauntlet.",
        "personality_text": "Highly whimsical, enjoys riddles and tricks. In her youth she sank ships as a siren and saved lost children as a guiding spirit. Today she finds entertainment in the Gilded Gauntlet. Deeply loyal to Naelia, her childhood friend.",
        "voice_notes": "Speaks with musical cadence. Uses childhood nicknames: calls Naelia 'Nili'. Often cryptic and playful. Can shift to terrifying authority instantly.",
    })

    # ---- CRITICAL: Tara ----
    chars.append({
        "id": 3, "name": "Tara",
        "type": "critical", "race": "Wood Elf", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Chaotic Neutral", "age": 897, "cr": None,
        "class_levels": j({"Warlock": 20}), "talent_tier": 3,
        "background": "Hermit", "xp": 383400,
        "str": 8, "dex": 16, "con": 18, "int": 18, "wis": 13, "cha": 28,
        "hp_max": 183, "hp_current": 183, "ac": 24,
        "speed": "35 ft.", "proficiency_bonus": 6,
        "saves_proficient": j(["wis", "cha"]),
        "skills": j({
            "Arcana": {"bonus": 16, "expertise": True}, "Deception": {"bonus": 21, "expertise": True},
            "Persuasion": {"bonus": 21, "expertise": True}, "Intimidation": {"bonus": 15},
            "Performance": {"bonus": 15}, "Nature": {"bonus": 10}, "Religion": {"bonus": 10},
            "Medicine": {"bonus": 7}, "Perception": {"bonus": 7}
        }),
        "languages": j(["Common", "Elvish", "Sylvan"]),
        "senses": j({"darkvision": 60, "passive_perception": 17}),
        "spellcasting_ability": "cha", "spell_save_dc": 27, "spell_attack_mod": 11,
        "spell_slots": j({"pact": 4, "pact_level": 5}),
        "spells_known": j({
            "cantrips": ["Eldritch Blast", "Mage Hand", "Minor Illusion", "True Strike"],
            "known": ["Charm Person", "Contact Other Plane", "Counterspell", "Crown of Madness", "Dimension Door", "Dispel Magic", "Dream", "Fly", "Hallucinatory Terrain", "Hex", "Hold Monster", "Major Image", "Mirror Image", "Remove Curse", "Witch Bolt"],
            "mystic_arcanum": ["Conjure Fey", "Dominate Monster", "Plane Shift", "True Polymorph"],
            "music_of_the_fey": ["Wish"]
        }),
        "special_abilities": j([
            {"name": "Otherworldly Patron: Harpist of the Veil", "description": "Must define a glade. Powers massively increased in glade. Loses all magic if leaves glade >1 hour. Dies if leaves >1 day."},
            {"name": "Music of the Fey", "description": "In glade: Wish 1/long rest, Foresight always active (advantage on everything, enemies disadvantage), can read specific futures."},
            {"name": "Pact of the Harp", "description": "Sprite or pixie familiar (Selenia). Fey cannot be harmed inside the glade."},
            {"name": "Eldritch Blast", "description": "+23 to hit, 4 beams of 1d10+5 force each."}
        ]),
        "current_location_id": 306,
        "status": "alive",
        "importance": 2, "is_public": 1,
        "appearance_text": "Dark-haired woman in a flowing black hooded gown/cloak. Sometimes with blue highlights and tattoo-like markings on arms. Blue eyes.",
        "backstory_text": "Holds a small nameless magic shop deep in the Silver Quarter. Sells charms, trinkets, magic baubles and deals in curses. Her clientele is mostly upper-class women seeking mind-control charms. Unlike traditional charms, her trinkets only work for the exact purpose specified. Each deal varies, is deceptively innocuous, and must never be spoken of outside the shop. Mysteriously exempt from Blue Dagger taxes despite open hostility from Kingpin Psyche Giannini.",
        "personality_text": "Mysterious, quietly powerful. Speaks little but every word carries weight. Fiercely devoted to Seraphine. Almost never leaves her shop.",
        "voice_notes": "Calm, measured, slightly amused. Speaks in riddles when pressed. Never raises her voice.",
    })

    # ---- CRITICAL: Alim Thunderfist ----
    chars.append({
        "id": 4, "name": "Alim Thunderfist",
        "type": "critical", "race": "Hill Dwarf", "creature_type": "humanoid",
        "sex": "Male", "alignment": "Lawful Good", "age": 180, "cr": None,
        "class_levels": j({"Monk": 20}), "talent_tier": 3,
        "background": "Hermit", "xp": 383400,
        "str": 12, "dex": 20, "con": 15, "int": 8, "wis": 20, "cha": 10,
        "hp_max": 163, "hp_current": 163, "ac": 20,
        "speed": "55 ft.", "proficiency_bonus": 6,
        "saves_proficient": j(["str", "dex", "con", "int", "wis", "cha"]),
        "skills": j({
            "Acrobatics": {"bonus": 11}, "Athletics": {"bonus": 7},
            "Medicine": {"bonus": 11}, "Religion": {"bonus": 5}
        }),
        "languages": j(["Common", "Dwarvish", "Goblin"]),
        "senses": j({"darkvision": 60, "passive_perception": 15}),
        "special_abilities": j([
            {"name": "Way of the Open Hand", "description": "Open Hand Technique, Quivering Palm (3 ki, CON save or 10d10 necrotic/drop to 0), Wholeness of Body, Tranquility"},
            {"name": "Diamond Soul", "description": "Proficient in all saving throws. 1 ki to reroll failed save."},
            {"name": "Empty Body", "description": "4 ki: invisible + resistance all damage except force. 8 ki: astral projection."},
            {"name": "Timeless Body", "description": "No aging effects."},
            {"name": "Ki", "description": "20 ki points, recover on short/long rest."},
            {"name": "Martial Arts", "description": "1d10+5 bludgeoning, magical. Bonus unarmed strike. Deflect Missiles 1d10+25."}
        ]),
        "actions": j([
            {"name": "Unarmed Strike", "type": "melee", "to_hit": 11, "damage": "1d10+5 bludgeoning (magical)"},
            {"name": "Bo Staff", "type": "melee", "to_hit": 11, "damage": "2d4+5 bludgeoning"}
        ]),
        "current_location_id": 300,
        "status": "alive",
        "guild_rank": "gold", "guild_tokens": 0,
        "importance": 2, "is_public": 1,
        "appearance_text": "Muscular stout dwarf with long silver/gray hair and beard, piercing blue eyes. Wearing simple monk robes, barefoot, wielding a bo staff.",
        "backstory_text": "Retired Gold ranked priest chosen as guildmaster by the Lady of the Guild for his immense fervour and dedication. Before dedicating himself to the Lady, spent over a human lifetime completing more contracts than anyone else. Refused injunctions from the Council of Four to lend his strength to military endeavours. Personally protected the High Duchess Jade Ravenshade during the Bloodveil Conspiracy, fending off three assassination attempts. Served as bodyguard and wet nurse for orphaned Arnalithah Ravenshade for three years. Trained Arnalithah in the Way of the Open Hand.",
        "personality_text": "Utterly devoted to the Lady of the Gauntlet. Humble despite immense power. Paternal toward Arnalithah. Refuses wealth and luxury.",
        "voice_notes": "Gruff but warm. Speaks simply and directly. Occasional dry humor. Uses dwarven expressions.",
    })

    # ---- CRITICAL: Amirah ----
    chars.append({
        "id": 5, "name": "Amirah",
        "type": "critical", "race": "Half Genie", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Neutral", "age": 521, "cr": None,
        "class_levels": j({"Bard": 20}), "talent_tier": 3,
        "background": "College of Creation",
        "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10,
        "hp_max": 100, "hp_current": 100, "ac": 15,
        "speed": "30 ft.", "proficiency_bonus": 6,
        "current_location_id": 400,
        "status": "alive",
        "importance": 2, "is_public": 0,
        "appearance_text": "White/platinum blonde hair with braids and gold accessories, pale yellow/gold eyes, gold jewelry (earrings, necklaces, forehead ornament), orange/amber Calishite clothing.",
        "backstory_text": "Born of genie father Bakallah al-Sadoof and aasimar mother Tamara who died in childbirth. Raised by Seraphine as her own kin. Devoted absolutely to Seraphine. Cursed and imprisoned her own father in a lamp when he tried to abduct her and Sahlila. Always the elder sister despite being a twin. Since Naelia and Seraphine became one, serves as handmaid alongside Sahlila.",
        "personality_text": "Projects an aura of calm. Devoted absolutely to Seraphine. Will bring immense power against anyone showing inadequate deference to her mistress. Often found playing wistful tunes on her enchanted Lyre.",
        "voice_notes": "Measured, dignified. Calishite-influenced speech. Protective, fiercely loyal.",
    })

    # ---- CRITICAL: Sahlila ----
    chars.append({
        "id": 6, "name": "Sahlila",
        "type": "critical", "race": "Half Genie", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Chaotic Evil", "age": 521, "cr": None,
        "class_levels": j({"Cleric": 20}), "talent_tier": 3,
        "background": "Trickery Domain",
        "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10,
        "hp_max": 100, "hp_current": 100, "ac": 15,
        "speed": "30 ft.", "proficiency_bonus": 6,
        "current_location_id": 400,
        "status": "alive",
        "importance": 2, "is_public": 0,
        "appearance_text": "Identical twin to Amirah. White/platinum hair, pale yellow/gold eyes, gold jewelry and headpieces, Calishite-style clothing in orange, gold, white, and purple tones.",
        "backstory_text": "Twin sister of Amirah. Always the chaotic force, using innate magic to play tricks. Inherits the sadistic tendencies of her archfey surrogate mother Seraphine. Takes great pleasure in eliminating threats. Resents her sister for merely cursing their father, considering his attempt to take them from Seraphine an offence only righted by death. Unmatched culinary talent, enhances meals with magic (not always beneficial).",
        "personality_text": "Chaotic, sadistic, playful in a dangerous way. Yang to Amirah's yin. Loves cooking and poisoning in equal measure. Devoted to Seraphine as both mistress and mother.",
        "voice_notes": "Quick, sharp, laughing. Switches from sweet to threatening in a heartbeat. Calishite expressions.",
    })

    # ---- CRITICAL: Zorathar the Eternal ----
    chars.append({
        "id": 7, "name": "Zorathar the Eternal",
        "type": "critical", "race": "Half-Elf", "creature_type": "undead",
        "sex": "Male", "alignment": "Lawful Evil", "age": 452, "cr": 25,
        "class_levels": j({"Wizard": 20}), "talent_tier": 3,
        "str": 14, "dex": 14, "con": 17, "int": 24, "wis": 19, "cha": 20,
        "hp_max": 187, "hp_current": 187, "ac": 17,
        "speed": "30 ft.", "proficiency_bonus": 8,
        "saves_proficient": j(["con", "int", "wis", "cha"]),
        "skills": j({"Arcana": {"bonus": 22}, "History": {"bonus": 15}, "Insight": {"bonus": 12}, "Religion": {"bonus": 15}}),
        "damage_resistances": j(["cold", "lightning", "necrotic"]),
        "damage_immunities": j(["necrotic", "non-magical bludgeoning", "non-magical piercing", "non-magical slashing"]),
        "condition_immunities": j(["charmed", "frightened", "paralyzed", "poisoned", "stunned", "exhaustion"]),
        "senses": j({"truesight": 60, "passive_perception": 14}),
        "spellcasting_ability": "int", "spell_save_dc": 23, "spell_attack_mod": 15,
        "spells_known": j({
            "cantrips": ["Mage Hand", "Prestidigitation", "Ray of Frost"],
            "1": ["Charm Person", "Magic Missile", "Shield", "Thunderwave"],
            "2": ["Detect Thoughts", "Invisibility", "Mirror Image", "Darkness"],
            "3": ["Animate Dead", "Counterspell", "Dispel Magic", "Fireball", "Fly", "Slow"],
            "4": ["Blight", "Dimension Door", "Phantasmal Killer"],
            "5": ["Cloudkill", "Scrying", "Telekinesis", "Dominate Person", "Cone of Cold"],
            "6": ["Chain Lightning", "Disintegrate", "Globe of Invulnerability"],
            "7": ["Finger of Death", "Delayed Blast Fireball", "Teleport"],
            "8": ["Dominate Monster", "Power Word Stun"],
            "9": ["Time Stop", "Power Word Kill", "Wish"]
        }),
        "actions": j([
            {"name": "Paralyzing Touch", "type": "melee", "to_hit": 15, "damage": "4d6+7 cold", "extra": "DC 23 CON or paralyzed 1 min"}
        ]),
        "legendary_actions": j({"per_round": 3, "actions": [
            {"name": "Paralyzing Touch", "cost": 2},
            {"name": "Cast Spell", "cost": 1, "description": "5th level and below"},
            {"name": "Disrupt Life", "cost": 2, "description": "Each non-undead in 20 ft: DC 23 CON, 6d6+7 necrotic or half"},
            {"name": "Frightening Gaze", "cost": 1, "description": "One creature in 10 ft: DC 23 WIS or frightened 1 min"}
        ]}),
        "current_location_id": 100,
        "status": "alive",
        "importance": 2, "is_public": 0,
        "appearance_text": "Decayed face with glowing red eyes, sparse gray beard, golden elven half-crown, magnificent purple robes with faintly glowing arcane symbols, holding a black orb.",
        "backstory_text": "Once a respected half-elven arch wizard who sought immortality through forbidden necromantic rituals. Commands legions of undead. Believed to be a major lieutenant in the new Cult of Vecna, reborn centuries after being believed disbanded.",
    })

    # ---- CRITICAL: Ommell Siobarek ----
    chars.append({
        "id": 8, "name": "Ommell Siobarek",
        "type": "critical", "race": "Human", "creature_type": "undead",
        "sex": "Female", "alignment": "Chaotic Evil", "age": 226, "cr": 21,
        "class_levels": j({"Wizard": 18}), "talent_tier": 3,
        "str": 11, "dex": 16, "con": 16, "int": 20, "wis": 14, "cha": 16,
        "hp_max": 124, "hp_current": 124, "ac": 17,
        "speed": "30 ft.", "proficiency_bonus": 7,
        "saves_proficient": j(["con", "int", "wis"]),
        "skills": j({"Arcana": {"bonus": 19}, "History": {"bonus": 12}, "Insight": {"bonus": 9}, "Perception": {"bonus": 9}}),
        "senses": j({"truesight": 120, "passive_perception": 19}),
        "spellcasting_ability": "int", "spell_save_dc": 20, "spell_attack_mod": 12,
        "current_location_id": 402,
        "status": "undead",
        "importance": 2, "is_public": 0,
        "appearance_text": "Undead queen with platinum crown, white hair, dead white eyes, dried/decayed skin, long white tattered gown, jewelry and necklaces.",
        "backstory_text": "Lich of the Crypt of the Forgotten. Naelia receives 50% of the revenue from the Crypt as tribute, in exchange for fending off assaults.",
    })

    # ---- MAJOR: The Beast / Razaaz ----
    chars.append({
        "id": 9, "name": "Razaaz",
        "aliases": j(["The Beast", "Pirate King", "King Razaaz", "Scourge of the Sword Coast"]),
        "type": "major", "race": "Human", "subrace": "Rakshasa", "creature_type": "fiend",
        "sex": "Male", "alignment": "Lawful Evil", "age": 471, "cr": 16,
        "str": 14, "dex": 17, "con": 18, "int": 13, "wis": 16, "cha": 20,
        "hp_max": 121, "hp_current": 121, "ac": 16,
        "speed": "40 ft.", "proficiency_bonus": 6,
        "skills": j({"Deception": {"bonus": 10}, "Insight": {"bonus": 8}}),
        "damage_vulnerabilities": j(["piercing from magic weapons wielded by good creatures"]),
        "damage_immunities": j(["non-magical bludgeoning", "non-magical piercing", "non-magical slashing"]),
        "senses": j({"darkvision": 60, "passive_perception": 13}),
        "languages": j(["Common", "Infernal", "Elvish", "Sylvan"]),
        "innate_spells": j({
            "at_will": ["detect thoughts", "disguise self", "mage hand", "minor illusion"],
            "3/day": ["charm person", "detect magic", "invisibility", "major image", "suggestion"],
            "1/day": ["dominate person", "fly", "plane shift", "true seeing"]
        }),
        "special_abilities": j([
            {"name": "Limited Magic Immunity", "description": "Cannot be affected or detected by spells of 6th level or lower unless he wishes. Advantage on saves vs all other spells."},
            {"name": "Claw Curse", "description": "Claw attacks curse the target, preventing benefit from short or long rest, filling thoughts with horrible images. Removed by remove curse."}
        ]),
        "actions": j([
            {"name": "Claw", "type": "melee", "to_hit": 8, "damage": "2d6+2 slashing + curse"},
            {"name": "Razaaz Rapier (+2)", "type": "melee", "to_hit": 11, "damage": "2d8+3 piercing"}
        ]),
        "current_location_id": 226,
        "status": "alive",
        "importance": 2, "is_public": 0,
        "appearance_text": "Post-apocalyptic gentleman. White beard twisted into a bun, dark blue wool coat with red Celtic patterns and orange lining, prominent buttons.",
        "backstory_text": "The elusive figure at the head of the Blue Dagger. An infamous pirate who terrorised the Sword Coast for centuries. Known for incredible speed, strength, and surviving far beyond human lifespan. In his current incarnation, federated the four underground organisations of the Gate. Rarely found outside his frigate. His history with Seraphine is TBD.",
        "personality_text": "Calculating, patient, ruthless. Prefers to operate through proxies. Enjoys surprising even his own lieutenants with unexpected appearances.",
        "voice_notes": "Speaks with deliberate calm. Every word chosen carefully. Occasional predatory smile.",
    })

    # ---- MAJOR: Psyche Giannini ----
    chars.append({
        "id": 10, "name": "Psyche Giannini",
        "aliases": j(["Kingpin - Shadow of the Tower"]),
        "type": "major", "race": "Half-Elf", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Chaotic Evil", "age": 144, "cr": None,
        "class_levels": j({"Warlock": 4}), "talent_tier": 1,
        "background": "Noble", "xp": 2835,
        "str": 9, "dex": 15, "con": 14, "int": 11, "wis": 13, "cha": 18,
        "hp_max": 31, "hp_current": 31, "ac": 10,
        "speed": "30 ft.", "proficiency_bonus": 2,
        "saves_proficient": j(["wis", "cha"]),
        "skills": j({
            "Arcana": {"bonus": 2}, "History": {"bonus": 2},
            "Intimidation": {"bonus": 6}, "Persuasion": {"bonus": 6}
        }),
        "languages": j(["Common", "Elvish", "Undercommon"]),
        "spellcasting_ability": "cha", "spell_save_dc": 14, "spell_attack_mod": 6,
        "spells_known": j({
            "cantrips": ["Eldritch Blast", "Friends", "Minor Illusion"],
            "known": ["Blindness/Deafness", "Command", "Hex", "Mirror Image", "Witch Bolt"]
        }),
        "special_abilities": j([
            {"name": "Otherworldly Patron: Lolth", "description": "Fiendish pact with the Demon Queen of Spiders."},
            {"name": "Pact of the Blade", "description": "Conjure any weapon, gain proficiency."},
            {"name": "Agonizing Blast", "description": "Add CHA to Eldritch Blast damage."},
            {"name": "Mask of Many Faces", "description": "Disguise Self at will."}
        ]),
        "current_location_id": 211,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Deathly pale skin, heavy eyeliner, pale dry blonde hair, jewellery. Wears white turtleneck gowns or black hooded cloaks.",
        "backstory_text": "Blue Dagger Kingpin controlling Seatower and Manorborn districts. Also a Mother in the Coven of Webs, worshipping Lolth alongside Duchess Olivia Caldwell.",
    })

    # ---- MAJOR: Duchess Olivia Caldwell ----
    chars.append({
        "id": 11, "name": "Olivia Caldwell",
        "aliases": j(["Duchess Caldwell"]),
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Neutral Evil", "age": 64, "cr": None,
        "class_levels": j({"Warlock": 7}), "talent_tier": 2,
        "background": "Noble", "xp": 25070,
        "str": 9, "dex": 15, "con": 14, "int": 11, "wis": 13, "cha": 18,
        "hp_max": 52, "hp_current": 52, "ac": 10,
        "speed": "30 ft.", "proficiency_bonus": 3,
        "saves_proficient": j(["wis", "cha"]),
        "skills": j({
            "Arcana": {"bonus": 3}, "History": {"bonus": 3},
            "Deception": {"bonus": 10, "expertise": True}, "Persuasion": {"bonus": 7},
            "Performance": {"bonus": 7}, "Intimidation": {"bonus": 4}
        }),
        "languages": j(["Common", "Abyssal", "Elvish"]),
        "spellcasting_ability": "cha", "spell_save_dc": 15, "spell_attack_mod": 7,
        "spells_known": j({
            "cantrips": ["Eldritch Blast", "Mage Hand", "Prestidigitation"],
            "known": ["Blindness/Deafness", "Command", "Dimension Door", "Dispel Magic", "Fireball", "Hex", "Mirror Image", "Witch Bolt"]
        }),
        "special_abilities": j([
            {"name": "Alter Self Necklace", "description": "Large amethyst necklace enchanted with Alter Self, castable 1/10 minutes. Cursed: handmaids Quarra and Yasrena can teleport to her location while worn."},
            {"name": "Pact of the Chain", "description": "Quasit familiar named Yozo."},
            {"name": "Dark One's Own Luck", "description": "1/rest, add 1d10 to ability check or save."}
        ]),
        "current_location_id": 313,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Appears youthful despite age 64 thanks to her enchanted necklace. Lavender gown, blonde hair with silver threads, amethyst pendant. Real appearance: visibly aged, mostly gray/silver hair, pronounced wrinkles.",
        "backstory_text": "Head of the Patriar Caldwell Family and Duchess on the Council of Four. Powerful spell weaver trained under Lolth for over three decades. Controls a web of spies across all social layers. A Mother in the Coven of Webs. Runs the Caldwell brand of magical items/potions and 'Olivia's Secret' linen line. Infuriated by Tara's magic shop which she cannot shut down.",
    })

    # ---- MAJOR: Duchess Jade Ravenshade ----
    chars.append({
        "id": 12, "name": "Jade Ravenshade",
        "aliases": j(["Grand Duchess Ravenshade", "High Duchess"]),
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Lawful Neutral", "age": 74, "cr": None,
        "class_levels": j({"Monk": 3}), "talent_tier": 1,
        "background": "Noble", "xp": 963,
        "str": 13, "dex": 16, "con": 14, "int": 9, "wis": 15, "cha": 11,
        "hp_max": 24, "hp_current": 24, "ac": 15,
        "speed": "40 ft.", "proficiency_bonus": 2,
        "saves_proficient": j(["str", "dex"]),
        "languages": j(["Common", "Elvish", "Shou", "Waan"]),
        "current_location_id": 311,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Silver hair in smooth low bun, almond-shaped deep brown eyes, warm olive-toned skin with delicate wrinkles. Elegant jade green silk robe with golden cranes and cherry blossoms. String of lustrous pearls.",
        "backstory_text": "Matriarch of the Patriar Ravenshade Dynasty. Grand Duchess on the Council of Four. Son Yuuto assassinated in 1509. Husband Asahi died in 1521. Close friend of Alim Thunderfist who protected her during the Bloodveil Conspiracy.",
    })

    # ---- MAJOR: Duke Oriel Redlocks ----
    chars.append({
        "id": 13, "name": "Oriel Redlocks",
        "aliases": j(["Duke Redlocks", "Marshal of the Flaming Fist"]),
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Male", "alignment": "Lawful Neutral", "age": 62, "cr": None,
        "class_levels": j({"Fighter": 9}), "talent_tier": 2,
        "background": "Noble", "xp": 50880,
        "str": 20, "dex": 14, "con": 17, "int": 11, "wis": 13, "cha": 9,
        "hp_max": 85, "hp_current": 85, "ac": 19,
        "speed": "30 ft.", "proficiency_bonus": 4,
        "saves_proficient": j(["str", "con"]),
        "skills": j({"History": {"bonus": 4}, "Insight": {"bonus": 5}, "Persuasion": {"bonus": 3}, "Survival": {"bonus": 5}}),
        "languages": j(["Common", "Dwarvish", "Gnomish"]),
        "current_location_id": 314,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Completely bald, deep brown skin, striking amber eyes. Deep indigo silk robe with silver threads, platinum medallion with intricate runes.",
        "backstory_text": "Head of the Patriar Redlocks Family. Duke and Marshal of the Flaming Fist. Master of the blade, still spars with soldiers weekly. Wife Aisha assassinated by Bloodveil Syndicate in 1501.",
    })

    # ---- MAJOR: Duke Phillipe-Michael Vammas ----
    chars.append({
        "id": 14, "name": "Phillipe-Michael Vammas",
        "aliases": j(["Duke Vammas"]),
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Male", "alignment": "Neutral", "age": 71, "cr": None,
        "class_levels": j({}), "talent_tier": 0,
        "str": 10, "dex": 10, "con": 10, "int": 14, "wis": 12, "cha": 13,
        "hp_max": 20, "hp_current": 20, "ac": 10,
        "speed": "30 ft.", "proficiency_bonus": 2,
        "current_location_id": 312,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Tall, imposing. Distinguished silver hair combed back from high forehead. Silver beard, piercing blue eyes. Dark burgundy velvet robe with gold embroidery, fur-lined mantle, gold medallion.",
        "backstory_text": "Head of the Patriar Vammas Family. Duke on the Council of Four. Commissioned a True Seeing ring for his daughter Delilah from Tara in 1505.",
    })

    # ---- MAJOR: Arnalithah Ravenshade ----
    chars.append({
        "id": 15, "name": "Arnalithah Ravenshade",
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Lawful Neutral", "age": 18, "cr": None,
        "class_levels": j({"Monk": 5}), "talent_tier": 3,
        "background": "Noble", "xp": 6890,
        "str": 13, "dex": 18, "con": 14, "int": 11, "wis": 15, "cha": 9,
        "hp_max": 38, "hp_current": 38, "ac": 16,
        "speed": "40 ft.", "proficiency_bonus": 3,
        "saves_proficient": j(["str", "dex"]),
        "skills": j({"Acrobatics": {"bonus": 7}, "History": {"bonus": 3}, "Persuasion": {"bonus": 2}, "Stealth": {"bonus": 7}}),
        "languages": j(["Common", "Elvish", "Halfling", "Shou", "Waan"]),
        "current_location_id": 311,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Young East Asian woman with jet-black hair in a tight bun, almond-shaped brown eyes. Luxurious gold silk yukata with red accents.",
        "backstory_text": "Only granddaughter of Jade Ravenshade. Heir of the Ravenshade Estate in Baldur's Gate. Parents killed in 1509 by unknown assassins. Trained by Alim Thunderfist in Way of the Open Hand since age 6. Considers Thunderfist a mentor and father figure. Coming of age for marriage, noble families have sent contenders.",
    })

    # ---- MAJOR: Delilah Vammas ----
    chars.append({
        "id": 16, "name": "Delilah Vammas",
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Lawful Neutral", "age": 28, "cr": None,
        "class_levels": j({"Wizard": 6}), "talent_tier": 3,
        "background": "Noble", "xp": 15120,
        "str": 11, "dex": 14, "con": 15, "int": 18, "wis": 13, "cha": 9,
        "hp_max": 38, "hp_current": 38, "ac": 12,
        "speed": "30 ft.", "proficiency_bonus": 3,
        "saves_proficient": j(["int", "wis"]),
        "skills": j({"Arcana": {"bonus": 7}, "History": {"bonus": 7}, "Insight": {"bonus": 4}, "Persuasion": {"bonus": 2}}),
        "languages": j(["Common", "Elvish", "Halfling"]),
        "spellcasting_ability": "int", "spell_save_dc": 15, "spell_attack_mod": 7,
        "spells_known": j({
            "cantrips": ["Blade Ward", "Minor Illusion", "Prestidigitation", "Ray of Frost"],
            "1": ["Mage Armor", "Detect Magic", "Identify", "Charm Person"],
            "2": ["Locate Object", "Detect Thoughts", "Phantasmal Force"],
            "3": ["Clairvoyance", "Fly", "Hypnotic Pattern"]
        }),
        "special_abilities": j([
            {"name": "True Seeing Ring", "description": "Golden ring with amethyst. Cursed, cannot be removed. Grants True Sight 40ft radius at random moments for random duration. +2 INT (already included). Commissioned by her father from Tara in 1505."},
            {"name": "Portent", "description": "Roll two d20s at dawn, use as replacement results."},
            {"name": "Expert Divination", "description": "Casting divination spells regains a lesser spell slot."}
        ]),
        "current_location_id": 312,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Regal figure, luxurious teal gown with golden accents. Platinum blonde hair in an elegant knot. Always wears a white ornate masquerade mask in public. Glass of red wine often in hand.",
        "backstory_text": "Eldest daughter and heir to the Vammas Estate. Dulls her sharp mind with wine, trying to escape the haunting reality of her cursed True Seeing ring. Enjoys games of chance, worships Tymora. Rarely seen outside the Upper City. Prefers study and gambling over courtly intrigue.",
        "quest_tags": j(["FightClub"]),
    })

    # ---- MAJOR: Daisuke Ravenshade ----
    chars.append({
        "id": 17, "name": "Daisuke Ravenshade",
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Male", "alignment": "Lawful Neutral", "age": 42, "cr": None,
        "class_levels": j({"Monk": 10}), "talent_tier": 3,
        "background": "Noble", "xp": 66560,
        "str": 13, "dex": 20, "con": 14, "int": 9, "wis": 15, "cha": 11,
        "hp_max": 73, "hp_current": 73, "ac": 17,
        "speed": "50 ft.", "proficiency_bonus": 4,
        "saves_proficient": j(["str", "dex"]),
        "languages": j(["Common", "Elvish", "Shou", "Waan"]),
        "current_location_id": 104,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Japanese man in gray sleeveless kimono, middle aged, bare arms crossed, muscular, serious, serene.",
        "backstory_text": "Second son of Jade Ravenshade. Heir to the Ravenshade Dynasty. Head of the leading Way of the Four Elements school in Suzail. Considered a prodigy in the ancestral martial arts of the Waan-Shou. Forced to assume leadership after his brother Yuuto's assassination.",
    })

    # ---- MAJOR: Hargul Ulkrunnar ----
    chars.append({
        "id": 18, "name": "Hargul Ulkrunnar",
        "aliases": j(["Kingpin - Guardian of the Docks"]),
        "type": "major", "race": "Half-Orc", "creature_type": "humanoid",
        "sex": "Male", "alignment": "Lawful Evil", "age": 45, "cr": None,
        "class_levels": j({"Warlock": 10}), "talent_tier": 3,
        "background": "Urchin", "xp": 69760,
        "str": 12, "dex": 14, "con": 14, "int": 8, "wis": 12, "cha": 19,
        "hp_max": 73, "hp_current": 73, "ac": 13,
        "speed": "30 ft.", "proficiency_bonus": 4,
        "saves_proficient": j(["wis", "cha"]),
        "skills": j({
            "Deception": {"bonus": 8}, "Intimidation": {"bonus": 8},
            "Sleight of Hand": {"bonus": 6}, "Stealth": {"bonus": 6}, "Religion": {"bonus": 3}
        }),
        "languages": j(["Common", "Orc"]),
        "spellcasting_ability": "cha", "spell_save_dc": 16, "spell_attack_mod": 8,
        "current_location_id": 220,
        "status": "alive",
        "importance": 3, "is_public": 0,
        "appearance_text": "Half-Orc, greyish skin, tusk teeth, calm, dark hooded warlock robes, muscular.",
        "backstory_text": "Blue Dagger Kingpin controlling Bloomridge, The Steeps, and Gray Harbor. Former Gilded Gauntlet member. Brother of Arenvald Ulkrunnar.",
    })

    # ---- MAJOR: Arenvald Ulkrunnar ----
    chars.append({
        "id": 19, "name": "Arenvald Ulkrunnar",
        "aliases": j(["Master of the Colosseum"]),
        "type": "major", "race": "Half-Orc", "creature_type": "humanoid",
        "sex": "Male", "alignment": "Chaotic Evil", "age": 56, "cr": None,
        "class_levels": j({"Barbarian": 9}), "talent_tier": 2,
        "background": "Urchin", "xp": 51840,
        "str": 20, "dex": 13, "con": 16, "int": 8, "wis": 12, "cha": 10,
        "hp_max": 95, "hp_current": 95, "ac": 14,
        "speed": "40 ft.", "proficiency_bonus": 4,
        "saves_proficient": j(["str", "con"]),
        "skills": j({"Athletics": {"bonus": 9}, "Intimidation": {"bonus": 4}, "Sleight of Hand": {"bonus": 5}, "Stealth": {"bonus": 5}, "Survival": {"bonus": 5}}),
        "languages": j(["Common", "Orc"]),
        "current_location_id": 307,
        "status": "alive",
        "importance": 3, "is_public": 0,
        "appearance_text": "7 feet tall. Greyish skin, tusk teeth, fierce, full body armor, bald, black leather, muscular.",
        "backstory_text": "First Lieutenant of the Docks in the Blue Dagger and Master of the Colosseum. Elder brother of Kingpin Hargul Ulkrunnar.",
    })

    # ---- MAJOR: Bakallah al-Sadoof ----
    chars.append({
        "id": 20, "name": "Bakallah al-Sadoof",
        "aliases": j(["Sultan Bakallah Shahih Arhim al-Sadoof"]),
        "type": "major", "race": "Djinni", "creature_type": "elemental",
        "sex": "Male", "alignment": "Chaotic Good", "age": 1877, "cr": 11,
        "str": 21, "dex": 15, "con": 22, "int": 15, "wis": 16, "cha": 20,
        "hp_max": 161, "hp_current": 161, "ac": 17,
        "speed": "30 ft., fly 90 ft.", "proficiency_bonus": 4,
        "saves_proficient": j(["dex", "wis", "cha"]),
        "damage_immunities": j(["lightning", "thunder"]),
        "senses": j({"darkvision": 120, "passive_perception": 13}),
        "languages": j(["Auran"]),
        "current_location_id": None,
        "status": "imprisoned",
        "importance": 3, "is_public": 0,
        "backstory_text": "Djinni Lord, father of Amirah and Sahlila. Imprisoned in a golden lamp by his daughter Amirah when he tried taking them from Seraphine. Inside the lamp is a pocket dimension with a palace. Followers from the elemental plane of air have been searching for him for three centuries.",
    })

    # ---- MAJOR: Quarra Jusztiirn (Yochlol) ----
    chars.append({
        "id": 21, "name": "Quarra Jusztiirn",
        "type": "major", "race": "Drow", "subrace": "Yochlol", "creature_type": "fiend",
        "sex": "Female", "alignment": "Chaotic Evil", "age": 346, "cr": 10,
        "str": 15, "dex": 14, "con": 18, "int": 13, "wis": 15, "cha": 15,
        "hp_max": 126, "hp_current": 126, "ac": 15,
        "speed": "30 ft., climb 30 ft.", "proficiency_bonus": 4,
        "saves_proficient": j(["dex", "int", "wis", "cha"]),
        "skills": j({"Deception": {"bonus": 10}, "Insight": {"bonus": 6}}),
        "current_location_id": 313,
        "status": "alive",
        "importance": 3, "is_public": 0,
        "backstory_text": "Duchess Olivia Caldwell's handmaid. Actually a Yochlol — a fiend servant of Lolth. The drow disguise has held for almost 20 years. Duty: protect Lolth's investment in Olivia and ensure loyalty.",
    })

    # ---- MAJOR: Yasrena Khalazza (Yochlol) ----
    chars.append({
        "id": 22, "name": "Yasrena Khalazza",
        "type": "major", "race": "Drow", "subrace": "Yochlol", "creature_type": "fiend",
        "sex": "Female", "alignment": "Chaotic Evil", "age": 434, "cr": 10,
        "str": 15, "dex": 14, "con": 18, "int": 13, "wis": 15, "cha": 15,
        "hp_max": 130, "hp_current": 130, "ac": 15,
        "speed": "30 ft., climb 30 ft.", "proficiency_bonus": 4,
        "saves_proficient": j(["dex", "int", "wis", "cha"]),
        "skills": j({"Deception": {"bonus": 10}, "Insight": {"bonus": 6}}),
        "current_location_id": 313,
        "status": "alive",
        "importance": 3, "is_public": 0,
        "backstory_text": "Duchess Olivia Caldwell's second handmaid. Also a Yochlol serving Lolth. Disguise held for almost 20 years.",
    })

    # ---- MAJOR: Mad Lula Soilmind ----
    chars.append({
        "id": 23, "name": "Mad Lula Soilmind",
        "type": "major", "race": "Green Hag", "creature_type": "fey",
        "sex": "Female", "alignment": "Chaotic Evil", "age": 432, "cr": 5,
        "str": 20, "dex": 18, "con": 18, "int": 13, "wis": 14, "cha": 20,
        "hp_max": 102, "hp_current": 102, "ac": 20,
        "speed": "30 ft.", "proficiency_bonus": 3,
        "skills": j({"Arcana": {"bonus": 4}, "Deception": {"bonus": 8}, "Perception": {"bonus": 5}, "Stealth": {"bonus": 7}}),
        "senses": j({"darkvision": 60, "passive_perception": 15}),
        "languages": j(["Common", "Draconic", "Sylvan"]),
        "current_location_id": 501,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "backstory_text": "A hag who lures lost adventurers. Betrayed and captured the two other members of her coven, wearing enchanted jewelry containing their souls. Shape-shifts to appear as an attractive young woman. Has a deal with the Coven of Webs which suppresses contracts against her.",
    })

    # ---- MAJOR: Mendiete ----
    chars.append({
        "id": 24, "name": "Mendiete",
        "type": "major", "race": "Tiefling", "subrace": "Mammon", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Neutral", "age": 78, "cr": None,
        "class_levels": j({"Rogue": 13}), "talent_tier": 3,
        "background": "Charlatan",
        "str": 8, "dex": 20, "con": 15, "int": 14, "wis": 10, "cha": 14,
        "hp_max": 94, "hp_current": 94, "ac": 16,
        "speed": "30 ft.", "proficiency_bonus": 5,
        "saves_proficient": j(["dex", "int"]),
        "skills": j({
            "Acrobatics": {"bonus": 10}, "Sleight of Hand": {"bonus": 15, "expertise": True},
            "Stealth": {"bonus": 15, "expertise": True}, "Investigation": {"bonus": 12, "expertise": True},
            "Deception": {"bonus": 12, "expertise": True}, "Intimidation": {"bonus": 7}
        }),
        "languages": j(["Common", "Thieves' Cant", "Infernal"]),
        "current_location_id": 203,
        "status": "alive",
        "importance": 3, "is_public": 0,
        "appearance_text": "Crimson skin, sharp dark horns curling back. Long silver hair. Sleek leather armor, high-heeled black leather boots. Ornate dagger at belt.",
        "backstory_text": "Senior enforcer for the Blue Dagger. Former Bronze-ranked adventurer who lost her Token bearer on a failed assignment. Routinely coats weapons in poisons. Loyal to her purse, not the cause.",
        "quest_tags": j(["FightClub"]),
    })

    # ---- MAJOR: Hilton Rooso ----
    chars.append({
        "id": 25, "name": "Hilton Rooso",
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Male", "alignment": "Lawful Neutral", "age": 34, "cr": None,
        "class_levels": j({"Rogue": 6}), "talent_tier": 2,
        "background": "Soldier",
        "str": 9, "dex": 18, "con": 14, "int": 13, "wis": 11, "cha": 15,
        "hp_max": 45, "hp_current": 34, "ac": 15,
        "speed": "30 ft.", "proficiency_bonus": 3,
        "saves_proficient": j(["dex", "int"]),
        "skills": j({
            "Athletics": {"bonus": 2, "expertise": True}, "Sleight of Hand": {"bonus": 10, "expertise": True},
            "Stealth": {"bonus": 10, "expertise": True}, "Persuasion": {"bonus": 8, "expertise": True},
            "Investigation": {"bonus": 4}, "Perception": {"bonus": 3}, "Intimidation": {"bonus": 5}
        }),
        "languages": j(["Common", "Thieves' Cant", "Sylvan"]),
        "current_location_id": 305,
        "status": "alive",
        "importance": 4, "is_public": 1,
        "appearance_text": "Dashing swashbuckler, lean athletic frame, dark hair, well-groomed goatee. Dark leather vest over loose white shirt.",
        "backstory_text": "Blue Dagger member, personal henchman of Gilas Benthey since boyhood. Completely loyal to Benthey, considers him a father.",
        "quest_tags": j(["FightClub"]),
    })

    # ---- MAJOR: Euphemia Vammas ----
    chars.append({
        "id": 26, "name": "Euphemia Vammas",
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Chaotic Good", "age": 24,
        "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 14,
        "hp_max": 10, "hp_current": 10, "ac": 10,
        "speed": "30 ft.", "proficiency_bonus": 2,
        "current_location_id": 312,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Smiling, elegant young woman. Luxurious purple gown with golden accents, golden hair with ornate golden tiara.",
        "backstory_text": "Youngest daughter of Duke Phillipe-Michael Vammas. Close friend of Arnalithah Ravenshade.",
    })

    # ---- MAJOR: Anna-Lise Vammas ----
    chars.append({
        "id": 27, "name": "Anna-Lise Vammas",
        "type": "major", "race": "Human", "creature_type": "humanoid",
        "sex": "Female", "alignment": "Neutral", "age": 62,
        "str": 10, "dex": 10, "con": 10, "int": 12, "wis": 12, "cha": 12,
        "hp_max": 10, "hp_current": 10, "ac": 10,
        "speed": "30 ft.", "proficiency_bonus": 2,
        "current_location_id": 312,
        "status": "alive",
        "importance": 3, "is_public": 1,
        "appearance_text": "Regal figure. White gown with golden accents, puffed sleeves, ruffles. Face hidden behind a sheer white veil from a golden ornate headdress resembling a crown.",
        "backstory_text": "Wife of Duke Phillipe-Michael Vammas. Mother of Delilah and Euphemia.",
    })

    # ---- Blue Dagger officers (stubs with TBD details) ----
    stub_chars = [
        (28, "Hicetaon Dutari", "major", "Human", "Male", None, 84, "Operations Officer in the Blue Dagger", 203),
        (29, "Melissa", "major", "Human", "Female", None, 37, "Mistress of Melissa's Cove, the famed pleasure house in the Silver Quarter.", 308),
        (30, "Tjalde Gimelstob", "major", "Human", "Female", None, 65, "Trademaster in the Blue Dagger", 203),
        (31, "Quaeth Nharimlur", "major", "Half-Elf", "Male", None, 57, "Trademaster in the Blue Dagger", 203),
        (32, "Thekkin Mountainfall", "major", "Dwarf", "Male", None, 132, "First Lieutenant in the Blue Dagger", 203),
        (33, "Richenda Evangelista", "major", "Human", "Female", None, 46, "First Lieutenant in the Blue Dagger", 203),
        (34, "Kingpin Photius Delnatte", "major", "Human", "Male", None, 55, "Blue Dagger Kingpin - Master of the Blackgate. Controls Blackgate, The Wide, Temples.", 230),
        (35, "Kingpin Menandros Kiestra", "major", "Human", "Male", None, 67, "Blue Dagger Kingpin - Gatekeeper in the East. Controls Outer City except Blackgate.", 202),
        (36, "Valxikas Raeburn", "major", "Tiefling", "Male", None, 72, "Operations Officer in the Blue Dagger", 203),
        (37, "Alavara Finwe", "major", "Elf", "Female", None, 198, "First Lieutenant in the Blue Dagger", 203),
        (38, "Isamaya Touchet", "major", "Half-Elf", "Female", None, 78, "Trademaster in the Blue Dagger", 203),
        (39, "Nindr Hadirsyr", "major", "Human", "Male", None, 59, "Operations Officer in the Blue Dagger", 203),
        (40, "Zenbis Narnajir", "major", "Dragonborn", "Female", None, 50, "Operations Officer in the Blue Dagger", 203),
        (41, "Lidda Highhill", "major", "Halfling", "Female", None, 190, "Trademaster in the Blue Dagger", 203),
    ]
    for sid, name, ctype, race, sex, alignment, age, backstory, loc_id in stub_chars:
        chars.append({
            "id": sid, "name": name, "type": ctype, "race": race,
            "sex": sex, "alignment": alignment, "age": age,
            "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10,
            "hp_max": 20, "hp_current": 20, "ac": 10,
            "speed": "30 ft.", "proficiency_bonus": 2,
            "current_location_id": loc_id,
            "status": "alive", "importance": 3, "is_public": 0,
            "backstory_text": backstory,
        })

    # ---- MINOR characters ----
    minor_chars = [
        (50, "Tomas Benedict", "minor", "Human", "Male", "Lawful Good", 68, "High priest of Lady's Hall (Temple of Tymora).", 304, 4),
        (51, "Amelia Fenwick", "minor", "Human", "Female", "Lawful Neutral", 33, "Master of Commerce in Baldur's Gate.", 301, 4),
        (52, "Earow Baker", "minor", "Human", "Male", "Lawful Evil", 31, "Flaming Fist guard at Basilisk Gate. Facilitates smuggling for the underworld. Pressured by the Dagger to smuggle a mysterious package.", 222, 5),
        (53, "Edwas", "minor", "Human", "Male", "Chaotic Good", 26, "Copper ranked adventurer from Neverwinter. In love with Tima. Pet mouse Scurry.", 222, 5),
        (54, "Tima", "minor", "Human", "Female", "Lawful Good", 21, "Waitress at the Elfsong Tavern. From Beregost. Sick mother Yrina in Whitkeep. Works 16-hour days.", 309, 5),
        (55, "Keenan McAllister", "minor", "Human", "Male", "Lawful Neutral", 59, "Second-most senior member of House Vammas Guard. Delilah's bodyguard since her 13th birthday.", 312, 4),
        (56, "Gilas Benthey", "minor", "Human", "Male", "Lawful Evil", 63, "Owner of the Low Lantern Tavern. Low-ranking Blue Dagger officer under Trademaster Lidda Highhill.", 305, 4),
        (57, "Aliwade", "minor", "Human", "Male", "Lawful Neutral", 32, "Melissa's little brother. Level 8 Fighter.", 308, 4),
        (58, "Maiathah", "minor", "Half-Elf", "Female", "Lawful Good", 41, "Level 6 Cleric (Light). Party with Delre Torunn and Hardo Midgee. Lost Bronze Rank after a failed assignment.", 300, 4),
        (59, "Hardo Midgee", "minor", "Halfling", "Male", "Chaotic Neutral", 64, "Level 9 Rogue (Thief). Rescued by Naelia from necromancers and a Lich.", 300, 4),
        (60, "Delre Torunn", "minor", "Hill Dwarf", "Female", "Chaotic Good", 64, "Level 6 Paladin (Devotion). Token bearer of her party. Inherited Bronze Coin from hero grandfather. Demoted to Copper.", 300, 4),
    ]
    for mid, name, ctype, race, sex, alignment, age, backstory, loc_id, importance in minor_chars:
        chars.append({
            "id": mid, "name": name, "type": ctype, "race": race,
            "sex": sex, "alignment": alignment, "age": age,
            "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10,
            "hp_max": 15, "hp_current": 15, "ac": 10,
            "speed": "30 ft.", "proficiency_bonus": 2,
            "current_location_id": loc_id,
            "status": "alive", "importance": importance, "is_public": 1,
            "backstory_text": backstory,
            "quest_tags": j(["FightClub"]) if mid in (52, 53, 54, 55, 56) else j([]),
        })

    # ---- LEGEND characters ----
    legend_chars = [
        (70, "Lolth", "legend", "Demon Queen of Spiders", "Female", "Chaotic Evil", None,
         "Queen of Spiders, Queen of the Demonweb Pits. Most influential goddess of the drow. Object of worship of the Coven of Webs.", 403),
        (71, "Vecna", "legend", "Archlich", "Male", "Lawful Evil", None,
         "The Archlich. CR 26. Master of lies and destruction. The Cult of Vecna seeks to bring him back.", None),
        (72, "Vlaakith CLVII", "legend", "Githyanki Lich Queen", "Female", "Chaotic Evil", None,
         "Undying ruler of the githyanki. CR 23. Actively seeking a mysterious artefact stolen from her.", None),
        (73, "Elminster Aumar", "legend", "Human", "Male", "Chaotic Good", 1000,
         "The Sage of Shadowdale. Level 30 Wizard. Chosen of Mystra. One of the most powerful mortals on Toril.", None),
        (74, "Archdevil Yalas", "legend", "Devil", "Male", "Lawful Evil", None,
         "Ruler of Avernus, killed Zariel for his seat. CR 35+. Killed the legendary hero Lahmana Firebreath.", 5),
        (75, "Lahmana Firebreath", "legend", "Tiefling", "Male", None, None,
         "Only person ever awarded the Platinum Coin by the Gilded Gauntlet. Killed by Archdevil Yalas in a duel on Yalas's home plane. Early wielder of Dawnbringer. Rumors persist about the fate of his Platinum Coin.", None),
        (76, "Guildmaster Aalinjun", "legend", "Aasimar", "Female", "Lawful Good", None,
         "Second guildmaster and cofounder of the Gilded Gauntlet. Level 20 Cleric. Founded Aalinjun's Trust. Longest-standing guildmaster (over a century).", None),
    ]
    for lid, name, ctype, race, sex, alignment, age, backstory, loc_id in legend_chars:
        chars.append({
            "id": lid, "name": name, "type": ctype, "race": race,
            "sex": sex, "alignment": alignment, "age": age,
            "str": 10, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10,
            "hp_max": 200, "hp_current": 200, "ac": 20,
            "speed": "30 ft.", "proficiency_bonus": 6,
            "current_location_id": loc_id,
            "status": "alive" if lid not in (75, 76) else "dead",
            "importance": 1, "is_public": 1,
            "backstory_text": backstory,
        })

    # ---- GILDED GAUNTLET GOLD MEMBERS ----
    gauntlet_gold = [
        (80, "Mavier", "critical", "Aasimar", "Male", "Lawful Good", 153, j({"Wizard": 20}), 3, "Sage",
         8, 16, 18, 20, 13, 10, 162, 13, 6, "Gold Rank. First Lieutenant of the Purple Hand company. Abjurer specialist."),
        (81, "Dimlies", "critical", "Tiefling", "Female", "Neutral", 144, j({"Bard": 20}), 3, "Entertainer",
         8, 16, 18, 13, 10, 20, 183, 14, 6, "Gold Rank. Captain and founder of the Purple Hand. World-class celebrity. Notoriously refused Caldwell brand deals."),
        (82, "Reltrana", "critical", "Half-Elf", "Female", "Lawful Neutral", 128, j({"Paladin": 11, "Rogue": 7}), 3, "Knight",
         20, 14, 14, 8, 12, 16, 103, 20, 4, "Gold Rank. High Inquisitor of the Other Hand (secret). Paladin of Vengeance / Assassin dual class."),
        (83, "Eilinoa Taalnabis", "critical", "Rock Gnome", "Female", "Chaotic Neutral", 134, j({"Barbarian": 19}), 3, "Outlander",
         20, 15, 18, 12, 12, 8, 214, 16, 6, "Gold Rank. Lieutenant of the Iron Grip. Bear Totem Warrior. Resists all damage but psychic while raging."),
        (84, "Kelpetor Boldwalker", "critical", "High Elf", "Male", "Chaotic Good", 330, j({"Sorcerer": 17}), 3, "Hermit",
         10, 16, 16, 9, 12, 20, 121, 13, 6, "Gold Rank. Lieutenant of the Iron Grip. Divine Soul Sorcerer with access to Cleric spell list."),
        (85, "Aura", "critical", "Water Genasi", "Male", "Lawful Neutral", 122, j({"Fighter": 18}), 3, "Soldier",
         20, 16, 18, 8, 14, 11, 184, 19, 6, "Gold Rank. Lieutenant of the Iron Grip. Battle Master with d12 superiority dice."),
        (86, "Brilleris Gakigum", "critical", "Hill Dwarf", "Female", "Lawful Neutral", 188, j({"Fighter": 20}), 3, "Knight",
         20, 16, 18, 8, 15, 12, 224, 16, 6, "Gold Rank. Captain of the Iron Grip. Champion Fighter. Crits on 18-20. 4 attacks per action."),
        (87, "Wolzenya", "critical", "Half-Elf", "Female", "Lawful Evil", 119, j({"Ranger": 18}), 3, "Outlander",
         12, 20, 17, 10, 15, 10, 166, 16, 6, "Gold Rank. Lieutenant of the Purple Hand. Hunter Ranger specialized in Aberrations, Oozes, and Fiends."),
        (88, "Reakas", "critical", "Tiefling", "Male", "Chaotic Neutral", 146, j({"Sorcerer": 20}), 3, "Hermit",
         10, 16, 18, 9, 12, 20, 162, 13, 6, "Gold Rank. Lieutenant of the Purple Hand. Aberrant Mind Sorcerer with telepathic abilities."),
        (89, "Kiris", "critical", "Satyr", "Male", "Neutral", 353, j({"Wizard": 17}), 3, "Sage",
         10, 16, 17, 20, 12, 8, 121, 13, 6, "Gold Rank. Lieutenant of the Purple Hand. Diviner with Greater Portent (3 d20s). Fey creature with Magic Resistance."),
        (90, "Ridrey Barleymouse", "critical", "Lightfoot Halfling", "Female", "Chaotic Good", 130, j({"Barbarian": 19}), 3, "Outlander",
         20, 16, 18, 8, 12, 11, 214, 17, 6, "Gold Rank. Lieutenant of the Purple Hand. Eagle Totem Warrior with flight capability while raging."),
        (91, "Beirin", "critical", "Aasimar", "Male", "Chaotic Neutral", 140, j({"Cleric": 18}), 3, "Spy",
         8, 15, 18, 10, 20, 12, 165, 15, 6, "Gold Rank. First Seeker of the Other Hand (secret). Trickery Cleric with Gauntlet-specific divine powers against oathbreakers."),
        (92, "Urmdor Stoutboots", "critical", "Mountain Dwarf", "Male", "Neutral Good", 197, j({"Paladin": 18}), 3, "Noble",
         20, 8, 19, 10, 12, 16, 184, 20, 6, "Gold Rank. Member of the Right Hand. Oath of Glory Paladin. 45 ft speed. 30 ft aura."),
        (93, "Qirora", "critical", "Half-Elf", "Female", "Chaotic Good", 121, j({"Paladin": 17}), 3, "Noble",
         20, 8, 18, 12, 13, 16, 174, 21, 6, "Gold Rank. Member of the Right Hand. Oath of Devotion. Purity of Spirit (Protection from Evil and Good always active)."),
        (94, "Minkini Tuffunedog", "critical", "Rock Gnome", "Female", "Chaotic Good", 203, j({"Paladin": 20}), 3, "Noble",
         20, 8, 18, 11, 12, 16, 204, 22, 6, "Gold Rank. Great Shield of the Right Hand. Oath of Glory. White Dragon Scale Mail (+1, cold resistance, advantage vs dragon breath)."),
        (95, "Bryllewyn Strongkith", "critical", "Mountain Dwarf", "Female", "Lawful Good", 155, j({"Paladin": 19}), 3, "Noble",
         20, 10, 18, 10, 13, 19, 194, 21, 6, "Gold Rank. Member of the Right Hand. Oath of Devotion. CHA 19 gives +4 aura saves in 30 ft."),
    ]
    for gid, name, ctype, race, sex, alignment, age, class_levels, talent, bg, s, d, co, i, w, ch, hp, ac, pb, backstory in gauntlet_gold:
        chars.append({
            "id": gid, "name": name, "type": ctype, "race": race,
            "sex": sex, "alignment": alignment, "age": age,
            "class_levels": class_levels, "talent_tier": talent, "background": bg,
            "str": s, "dex": d, "con": co, "int": i, "wis": w, "cha": ch,
            "hp_max": hp, "hp_current": hp, "ac": ac,
            "speed": "30 ft.", "proficiency_bonus": pb,
            "current_location_id": 300,
            "status": "alive", "guild_rank": "gold",
            "importance": 2, "is_public": 1,
            "backstory_text": backstory,
        })

    return chars


# ============================================================================
# ORGANIZATION MEMBERSHIPS
# ============================================================================

def seed_org_memberships(db: sqlite3.Connection):
    """Seed organization memberships."""
    c = db.cursor()
    memberships = [
        # Gilded Gauntlet
        (4, 1, "Guildmaster / High Priest", "Gold", 1),
        (80, 1, "Member", "Gold", 1), (80, 6, "First Lieutenant", None, 1),
        (81, 1, "Member", "Gold", 1), (81, 6, "Captain", None, 1),
        (82, 1, "Member", "Gold", 1), (82, 4, "High Inquisitor", None, 0),
        (83, 1, "Member", "Gold", 1), (83, 5, "Lieutenant", None, 1),
        (84, 1, "Member", "Gold", 1), (84, 5, "Lieutenant", None, 1),
        (85, 1, "Member", "Gold", 1), (85, 5, "Lieutenant", None, 1),
        (86, 1, "Member", "Gold", 1), (86, 5, "Captain", None, 1),
        (87, 1, "Member", "Gold", 1), (87, 6, "Lieutenant", None, 1),
        (88, 1, "Member", "Gold", 1), (88, 6, "Lieutenant", None, 1),
        (89, 1, "Member", "Gold", 1), (89, 6, "Lieutenant", None, 1),
        (90, 1, "Member", "Gold", 1), (90, 6, "Lieutenant", None, 1),
        (91, 1, "Member", "Gold", 1), (91, 4, "First Seeker", None, 0),
        (92, 1, "Member", "Gold", 1), (92, 3, "Member", None, 1),
        (93, 1, "Member", "Gold", 1), (93, 3, "Member", None, 1),
        (94, 1, "Member", "Gold", 1), (94, 3, "Great Shield", None, 1),
        (95, 1, "Member", "Gold", 1), (95, 3, "Member", None, 1),

        # Gauntlet registered members (non-Gold)
        (58, 1, "Member", "Copper", 1),  # Maiathah
        (59, 1, "Member", "Copper", 1),  # Hardo
        (60, 1, "Member", "Copper", 1),  # Delre
        (53, 1, "Member", "Copper", 1),  # Edwas

        # Blue Dagger
        (9, 10, "The Beast / Head", None, 0),
        (10, 10, "Kingpin - Shadow of the Tower", None, 0),
        (34, 10, "Kingpin - Master of the Blackgate", None, 0),
        (35, 10, "Kingpin - Gatekeeper in the East", None, 0),
        (18, 10, "Kingpin - Guardian of the Docks", None, 0),
        (19, 10, "First Lieutenant - Docks", None, 0),
        (28, 10, "Operations Officer", None, 0),
        (30, 10, "Trademaster", None, 0),
        (31, 10, "Trademaster", None, 0),
        (32, 10, "First Lieutenant", None, 0),
        (33, 10, "First Lieutenant", None, 0),
        (36, 10, "Operations Officer", None, 0),
        (37, 10, "First Lieutenant", None, 0),
        (38, 10, "Trademaster", None, 0),
        (39, 10, "Operations Officer", None, 0),
        (40, 10, "Operations Officer", None, 0),
        (41, 10, "Trademaster", None, 0),
        (56, 10, "Low-ranking Officer", None, 0),
        (24, 10, "Senior Enforcer", None, 0),
        (25, 10, "Henchman", None, 0),
        (52, 10, "Asset", None, 0),  # Earow Baker

        # Coven of Webs
        (10, 11, "Mother", None, 0),  # Psyche
        (11, 11, "Mother", None, 0),  # Olivia
        (23, 11, "Associate", None, 0),  # Mad Lula

        # Cult of Vecna
        (7, 12, "Lieutenant", None, 0),  # Zorathar

        # Council of Four
        (12, 13, "Grand Duchess", None, 1),
        (11, 13, "Duchess", None, 1),
        (13, 13, "Duke / Marshal of the Flaming Fist", None, 1),
        (14, 13, "Duke", None, 1),

        # Noble Houses
        (12, 21, "Matriarch", None, 1),
        (15, 21, "Heir (Baldur's Gate)", None, 1),
        (17, 21, "Heir (Dynasty)", None, 1),
        (14, 22, "Patriarch", None, 1),
        (16, 22, "Heir", None, 1),
        (26, 22, "Member", None, 1),
        (27, 22, "Member", None, 1),
        (11, 20, "Head", None, 1),
        (13, 23, "Head", None, 1),

        # Flaming Fist
        (13, 15, "Marshal", None, 1),
        (52, 15, "Guard", None, 1),

        # Lady's Hall
        (50, 1, "High Priest", None, 1),  # Actually Lady's Hall, but no org for it yet
    ]

    c.executemany(
        "INSERT INTO org_memberships (character_id, org_id, role, rank, is_public) VALUES (?, ?, ?, ?, ?)",
        memberships
    )
    print(f"  Seeded {len(memberships)} organization memberships")


# ============================================================================
# CHARACTER RELATIONSHIPS
# ============================================================================

def seed_character_relationships(db: sqlite3.Connection):
    """Seed character relationships."""
    c = db.cursor()
    rels = [
        # Naelia & Seraphine
        (1, 2, "friend", "Childhood friends, now bonded via Gowns of Power as two faces of the same being.", 10, 0),
        (2, 1, "friend", "Childhood friends, bonded via Gowns of Power. Calls Naelia 'Nili'.", 10, 0),

        # Seraphine's household
        (5, 2, "servant", "Devoted handmaid. Regards Seraphine as both mistress and mother.", 10, 0),
        (6, 2, "servant", "Devoted handmaid. Regards Seraphine as both mistress and mother.", 10, 0),
        (5, 6, "family", "Twin sister. Amirah is the calmer elder twin.", 7, 0),
        (6, 5, "family", "Twin sister. Sahlila is the chaotic yang.", 6, 0),
        (5, 20, "family", "Father. Amirah imprisoned him in a lamp.", -3, 0),
        (6, 20, "family", "Father. Sahlila wants him dead for trying to take them from Seraphine.", -10, 0),
        (20, 5, "family", "Daughter who imprisoned him.", -5, 0),
        (20, 6, "family", "Daughter who wants him dead.", -8, 0),
        (3, 2, "servant", "Patron and Mistress. Absolute devotion.", 10, 0),
        (2, 3, "patron", "Warlock patron. Tara is her agent in the mortal world.", 8, 0),

        # Alim Thunderfist
        (4, 12, "friend", "Deep friendship forged during Bloodveil Conspiracy protection.", 9, 0),
        (12, 4, "friend", "Regards Alim as close friend and family member.", 9, 0),
        (4, 15, "mentor", "Trained Arnalithah in Way of the Open Hand since she was 6. Father figure.", 9, 0),
        (15, 4, "student", "Looks up to Alim as both mentor and father figure.", 9, 0),

        # Ravenshade family
        (12, 17, "family", "Mother. Daisuke is heir to the dynasty.", 8, 0),
        (17, 12, "family", "Mother is Grand Duchess.", 8, 0),
        (12, 15, "family", "Grandmother. Arnalithah is heir in Baldur's Gate.", 9, 0),
        (15, 12, "family", "Grandmother and Grand Duchess.", 9, 0),
        (15, 17, "family", "Uncle. Daisuke is dynasty heir.", 6, 0),
        (17, 15, "family", "Niece. Heir in Baldur's Gate.", 6, 0),

        # Vammas family
        (14, 16, "family", "Father-daughter. Commissioned her True Seeing ring.", 7, 0),
        (14, 26, "family", "Father-daughter.", 7, 0),
        (14, 27, "family", "Husband-wife.", 6, 0),
        (16, 26, "family", "Elder sister.", 7, 0),
        (16, 15, "friend", "Friend.", 5, 0),
        (26, 15, "friend", "Close friend.", 7, 0),

        # Coven connections
        (10, 11, "ally", "Fellow Mothers in the Coven of Webs.", 6, 1),
        (11, 10, "ally", "Fellow Mothers in the Coven of Webs.", 6, 1),
        (21, 11, "servant", "Yochlol handmaid. Protects Lolth's investment.", 7, 1),
        (22, 11, "servant", "Yochlol handmaid. Protects Lolth's investment.", 7, 1),

        # Blue Dagger hierarchy
        (18, 19, "family", "Younger brother to Arenvald.", 7, 0),
        (19, 18, "family", "Elder brother to Hargul.", 7, 0),
        (25, 56, "employee", "Completely loyal henchman. Benthey raised him.", 9, 0),
        (56, 25, "employer", "Raised Rooso from the streets.", 8, 0),

        # Keenan McAllister
        (55, 16, "protector", "Personal bodyguard since her 13th birthday.", 8, 0),
        (55, 14, "employee", "Employer.", 6, 0),

        # Ommell tribute
        (8, 1, "ally", "Ommell pays tribute to Naelia from the Crypt of the Forgotten.", 3, 1),

        # Tara vs Caldwell
        (3, 11, "rival", "Olivia has tried to shut down Tara's shop for over a decade. All attempts failed.", -5, 0),
        (11, 3, "enemy", "Infuriated by Tara's illegal shop that she cannot shut down.", -7, 0),
    ]

    c.executemany(
        """INSERT INTO character_relationships
           (character_id, target_id, relationship_type, description, sentiment, is_secret)
           VALUES (?, ?, ?, ?, ?, ?)""",
        rels
    )
    print(f"  Seeded {len(rels)} character relationships")


# ============================================================================
# ORGANIZATION RELATIONSHIPS
# ============================================================================

def seed_org_relationships(db: sqlite3.Connection):
    """Seed inter-organization relationships."""
    c = db.cursor()
    org_rels = [
        (1, 10, "neutral", "Uneasy coexistence. Cooperated during Bloodveil Conspiracy.", 0),
        (1, 19, "hostile", "Gauntlet hunted Bloodveil Syndicate 1501-1507.", 0),
        (10, 15, "infiltrated", "Blue Dagger has agents in the Flaming Fist.", 1),
        (10, 16, "infiltrated", "Blue Dagger has agents in The Watch.", 1),
        (10, 14, "infiltrated", "Blue Dagger has agents in the Parliament of Peers.", 1),
        (11, 10, "infiltrated", "Psyche Giannini is both Kingpin and Coven Mother.", 1),
        (11, 13, "infiltrated", "Duchess Caldwell is both Duchess and Coven Mother.", 1),
        (1, 24, "allied", "Golden Alliance sister guild (Waterdeep).", 0),
        (1, 25, "allied", "Golden Alliance sister guild (Suzail).", 0),
        (1, 26, "allied", "Golden Alliance sister guild (Calimport).", 0),
        (11, 23, "cooperative", "Mad Lula helps Coven in magical matters in exchange for protection.", 1),
        (18, 12, "hostile", "Third Lotus may be connected to Ravenshade murders.", 1),
    ]

    c.executemany(
        """INSERT INTO org_relationships (org_a_id, org_b_id, relationship_type, description, is_secret)
           VALUES (?, ?, ?, ?, ?)""",
        org_rels
    )
    print(f"  Seeded {len(org_rels)} org relationships")


# ============================================================================
# ITEMS
# ============================================================================

def seed_items(db: sqlite3.Connection):
    """Seed notable items."""
    c = db.cursor()
    items = [
        ("Seraphine's Mirror", "wondrous", None, j({"description": "Small finely crafted elven mirror, given by her mother at age 7. Used for scrying."}), 0, None, 2, None, 0, None, 0, 1, "A small, finely crafted but mundane mirror.", 0),
        ("Seraphine's Ring of Seeming", "ring", "uncommon", j({"spell": "Seeming", "enchanted_by": "Naelia at age 9"}), 0, None, 2, None, 1, "ring1", 0, 1, "Beautiful golden ring enchanted with Seeming.", 500),
        ("Seraphine's Harp", "wondrous", "legendary", j({"commission_age": 34, "material": "Oldest tree in a Feywild forest", "enchanted_by": "Seraphine and Naelia over decades"}), 0, None, 2, None, 1, None, 0, 1, "Ornately carved harp grown from the oldest tree in a Feywild forest.", 0),
        ("Seraphine's Wand of Gate", "wand", "legendary", j({"spell": "Gate", "charges": "3/hour", "base_material": "Seraphine's childhood tree", "enchanted_by": "Naelia", "diamond_base": True}), 0, None, 2, None, 1, None, 0, 1, "Wand grown from Seraphine's childhood tree. Base has a large diamond. Casts Gate 3/hour.", 0),
        ("Razaaz Rapier (+2)", "weapon", "rare", j({"type": "rapier", "bonus": 2, "damage": "2d8+3 piercing", "to_hit_bonus": 11}), 0, None, 9, None, 1, "mainhand", 0, 1, "A finely crafted +2 rapier.", 5000),
        ("Delilah's True Seeing Ring", "ring", "very_rare", j({"spell": "True Seeing", "range": 40, "trigger": "random", "cursed": True, "int_bonus": 2}), 0, None, 16, None, 1, "ring1", 1, 1, "Golden ring with amethyst. Grants True Sight 40ft at random. Cannot be removed. +2 INT.", 0),
        ("Olivia's Amethyst Necklace", "wondrous", "rare", j({"spell": "Alter Self", "uses": "1/10min", "cursed": True, "curse_effect": "Handmaids Quarra and Yasrena can teleport to wearer"}), 0, None, 11, None, 1, "neck", 1, 1, "Large amethyst necklace. Casts Alter Self. Cursed: fiendish handmaids can teleport to location.", 0),
        ("White Dragon Scale Mail", "armor", "very_rare", j({"ac_bonus": 1, "resistance": "cold", "advantage": "saves vs Frightful Presence and dragon breath", "detect_dragon": "nearest white dragon within 30 miles, 1/dawn"}), 1, 94, 94, None, 1, "armor", 0, 1, "Gleaming white dragon scale mail armor.", 15000),
    ]

    c.executemany(
        """INSERT INTO items (name, type, rarity, properties, requires_attunement, attuned_to,
           held_by, location_id, equipped, slot, is_cursed, is_identified, description, value_gp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        items
    )
    print(f"  Seeded {len(items)} items")


# ============================================================================
# CUSTOM MECHANICS
# ============================================================================

def seed_custom_mechanics(db: sqlite3.Connection):
    """Seed all custom homebrew mechanics."""
    c = db.cursor()

    mechanics = [
        ("oracle_burden", "oracle", j({
            "vision_count_table": [
                {"d100_min": 0, "d100_max": 94, "visions": 1},
                {"d100_min": 95, "d100_max": 98, "visions": 2},
                {"d100_min": 99, "d100_max": 99, "visions": "1d4+1"}
            ],
            "vision_importance_table": [
                {"d20_min": 1, "d20_max": 5, "importance": "minor", "description": "Random minor crime or inconsequential encounter"},
                {"d20_min": 6, "d20_max": 18, "importance": "major", "description": "Important event related to Naelia's current preoccupation"},
                {"d20_min": 19, "d20_max": 20, "importance": "critical", "description": "Major scene: powerful enemy in hidden lair, past historical event revealing secrets"}
            ],
            "effects": "Naelia enters the mind of a mortal creature for the vision's duration. She gains first-hand familiarity with places explored (free teleportation). Her own motivations do not apply during the vision."
        }), "Naelia's nightly vision mechanic during long rest."),

        ("talent_system", "talent", j({
            "tiers": {
                "0": {"name": "Normal", "symbol": "", "level_formula": "n*(n+1)/2", "max_level_human": 8},
                "1": {"name": "Talented", "symbol": "*", "level_formula": "n*(n+1)/2 * 0.75"},
                "2": {"name": "Exceptional", "symbol": "**", "level_formula": "n*(n+1)/2 * 0.5"},
                "3": {"name": "Prodigious", "symbol": "***", "level_formula": "n*(n+1)/3"}
            },
            "population_density": {
                "over_93_percent": "Can never exceed 8th level",
                "most_humans_bronze_or_below": True,
                "youngest_silver_holder": 69,
                "youngest_gold_holder": 112,
                "no_human_gold_in_century": True
            }
        }), "Talent tier system affecting leveling speed and population demographics."),

        ("intoxication", "intoxication", j({
            "threshold_formula": "min(7 + racial_modifier + (con_modifier * 3), 1)",
            "racial_modifiers": {
                "Dwarf": 2, "Half-Orc": 1, "Goliath": 2, "Warforged": 5,
                "Elf": -1, "Halfling": -1, "Gnome": -1, "Tabaxi": -2,
                "Human": 0, "Half-Elf": 0, "Tiefling": 0, "Dragonborn": 0
            },
            "drink_strength": {
                "Non-Alcoholic": 0, "Light": 1, "Moderate": 2,
                "Strong": 3, "Very Strong": 4, "Deadly": 5
            },
            "deadly_con_save_dc": 10,
            "effects_by_threshold": {
                "0.5x": {"cha": 1, "str": 0, "attacks": "normal"},
                "0.75x": {"cha": 2, "str": 1, "attacks": "normal"},
                "1.0x": {"cha": 0, "str": 2, "attacks": "disadvantage"},
                "1.5x": {"cha": -2, "str": 3, "attacks": "disadvantage"},
                "2.0x": "Blackout: death saving throws required"
            },
            "detox_rate": "1 point per 30 minutes or cure poison",
            "hangover": {"con_checks": -3, "int_checks": -2, "duration": "until long rest"}
        }), "Custom intoxication mechanics with racial modifiers and progressive effects."),

        ("guild_token_economy", "guild", j({
            "rank_thresholds": {
                "copper": {"gt": 100, "cr_max": 4, "coin_value_gp": 10},
                "brass": {"gt": 10000, "cr_max": 6, "coin_value_gp": 500},
                "bronze": {"gt": 100000, "cr_max": 14, "coin_value_gp": 30000, "unlocks": ["Guild Store"]},
                "silver": {"gt": 10000000, "cr_max": 17, "coin_value_gp": 350000, "unlocks": ["Upper City access", "Patrician contracts", "Watch Token authority"]},
                "gold": {"gt": 1000000000, "cr_max": 20, "coin_value_gp": "priceless", "unlocks": ["Free Patrician Gates", "Personal noble requests"]},
                "platinum": {"gt": 100000000000, "cr_any": True, "coin_value_gp": "priceless", "unlocks": ["Favour of the Guild 1/year"]}
            },
            "contract_examples": {
                "CR1": {"stake": 50, "reward_gt": 20, "reward_gp": 100},
                "CR10": {"stake": 30000, "reward_gt": 1000, "reward_gp": 2000},
                "CR15": {"stake": 2000000, "reward_gt": 25000, "reward_gp": 30000},
                "CR20": {"stake": 250000000, "reward_gt": 1000000, "reward_gp": 500000},
                "world": {"stake": 25000000000, "reward_gt": 200000000, "reward_gp": 1000000}
            },
            "laws": {
                "ledger_is_absolute": "Names crossed off at 0 GT = permanent removal. Protected by Epic Magic DC31 CON save or 200+40d12 force.",
                "law_of_the_dozen": "Oathbreakers have 12 days to yield. After 12 days: kill on sight. Must ask if they submit before killing.",
                "law_of_free_transfer": "Can give/sell stake to another member. Requires 3 priests + 12 days isolation.",
                "law_of_limited_exclusivity": "First applicant gets 12 days exclusivity on high-level contracts.",
                "law_of_sacred_ground": "No blood on consecrated ground except to defend its sanctity."
            }
        }), "Gilded Gauntlet token economy, rank system, and foundational laws."),
    ]

    c.executemany(
        "INSERT INTO custom_mechanics (name, category, rule_data, description) VALUES (?, ?, ?, ?)",
        mechanics
    )
    print(f"  Seeded {len(mechanics)} custom mechanics")


# ============================================================================
# WEATHER TABLES
# ============================================================================

def seed_weather_tables(db: sqlite3.Connection):
    """Seed seasonal weather reference tables."""
    c = db.cursor()

    weather_data = []
    # Winter
    for wtype, lo, hi, effects, desc in [
        ("Clear Skies", 1, 15, j({"modifiers": "none"}), "No modifiers."),
        ("Heavy Clouds", 16, 30, j({"aerial_cover": True, "no_sunlight": True}), "Aerial cover, no sunlight."),
        ("Freezing Cold", 31, 50, j({"con_save_dc": 15, "cold_damage_bonus": 2}), "DC 15 CON save. Cold damage +2."),
        ("Snow", 51, 70, j({"travel_halved": True, "difficult_terrain": True}), "Travel halved. Difficult terrain."),
        ("High Winds", 71, 80, j({"flying_speed_mod": 10, "ranged_penalty": -2}), "Flying +/-10 speed. Ranged -2."),
        ("Heavy Rain", 81, 88, j({"con_save_dc": 16, "fire_penalty": -4, "lightning_cold_bonus": 2}), "DC 16 CON. Fire -4."),
        ("Blizzard", 89, 95, j({"con_save_dc": 12, "cold_damage": "3d4", "heavy_obscurement": True}), "DC 12 CON hourly, 3d4 cold."),
        ("Thunderstorm", 96, 99, j({"partial_obscurement": True, "lightning_strike_d20": True}), "Partial obscurement. d20 lightning."),
        ("Strange Phenomenon", 100, 100, j({"roll_d6": True}), "Roll d6: Ashfall, Eclipse, Strange Lights, Meteor Shower, Malevolent Storm, Wild Magic Storm."),
    ]:
        weather_data.append(("winter", wtype, lo, hi, effects, desc))

    # Spring
    for wtype, lo, hi, effects, desc in [
        ("Clear Skies", 1, 25, j({"modifiers": "none"}), "No modifiers."),
        ("Heavy Clouds", 26, 40, j({"aerial_cover": True, "no_sunlight": True}), "Aerial cover, no sunlight."),
        ("Rain", 41, 60, j({"wagon_travel_halved": True, "fire_penalty": -2, "con_save_dc": 12}), "Wagon travel halved. Fire -2."),
        ("Heavy Rain", 61, 75, j({"con_save_dc": 16, "fire_penalty": -4, "lightning_cold_bonus": 2}), "DC 16 CON. Fire -4."),
        ("High Winds", 76, 85, j({"flying_speed_mod": 10, "ranged_penalty": -2}), "Flying +/-10 speed. Ranged -2."),
        ("Thunderstorm", 86, 95, j({"partial_obscurement": True, "lightning_strike_d20": True}), "Partial obscurement."),
        ("Strange Phenomenon", 96, 100, j({"roll_d6": True}), "Roll d6 for phenomenon type."),
    ]:
        weather_data.append(("spring", wtype, lo, hi, effects, desc))

    # Summer
    for wtype, lo, hi, effects, desc in [
        ("Clear Skies", 1, 30, j({"modifiers": "none"}), "No modifiers."),
        ("Scorching Heat", 31, 55, j({"double_water": True, "fire_bonus": 2, "cold_penalty": -2}), "Double water. Fire +2, Cold -2."),
        ("Heavy Clouds", 56, 65, j({"aerial_cover": True, "no_sunlight": True}), "Aerial cover, no sunlight."),
        ("Rain", 66, 80, j({"wagon_travel_halved": True, "fire_penalty": -2, "con_save_dc": 12}), "Wagon travel halved. Fire -2."),
        ("Thunderstorm", 81, 92, j({"partial_obscurement": True, "lightning_strike_d20": True}), "Partial obscurement."),
        ("High Winds", 93, 97, j({"flying_speed_mod": 10, "ranged_penalty": -2}), "Flying +/-10 speed. Ranged -2."),
        ("Strange Phenomenon", 98, 100, j({"roll_d6": True}), "Roll d6 for phenomenon type."),
    ]:
        weather_data.append(("summer", wtype, lo, hi, effects, desc))

    # Fall
    for wtype, lo, hi, effects, desc in [
        ("Clear Skies", 1, 20, j({"modifiers": "none"}), "No modifiers."),
        ("Heavy Clouds", 21, 40, j({"aerial_cover": True, "no_sunlight": True}), "Aerial cover, no sunlight."),
        ("Rain", 41, 60, j({"wagon_travel_halved": True, "fire_penalty": -2, "con_save_dc": 12}), "Wagon travel halved. Fire -2."),
        ("Heavy Rain", 61, 75, j({"con_save_dc": 16, "fire_penalty": -4, "lightning_cold_bonus": 2}), "DC 16 CON. Fire -4."),
        ("High Winds", 76, 85, j({"flying_speed_mod": 10, "ranged_penalty": -2}), "Flying +/-10 speed."),
        ("Freezing Cold", 86, 92, j({"con_save_dc": 15, "cold_damage_bonus": 2}), "DC 15 CON save. Cold +2."),
        ("Thunderstorm", 93, 97, j({"partial_obscurement": True, "lightning_strike_d20": True}), "Partial obscurement."),
        ("Strange Phenomenon", 98, 100, j({"roll_d6": True}), "Roll d6 for phenomenon type."),
    ]:
        weather_data.append(("fall", wtype, lo, hi, effects, desc))

    c.executemany(
        "INSERT INTO weather_tables (season, weather_type, d100_min, d100_max, effects, description) VALUES (?, ?, ?, ?, ?, ?)",
        weather_data
    )
    print(f"  Seeded {len(weather_data)} weather table entries")


# ============================================================================
# WORLD HISTORY
# ============================================================================

def seed_world_history(db: sqlite3.Connection):
    """Seed key historical events."""
    c = db.cursor()
    events = [
        (560, "Founding of Baldur's Gate Council", "Sea captains stormed the walled city and mockingly named themselves 'Dukes'.", j([]), "critical", 1),
        (1324, "Rise of the Bloodveil Syndicate", "The Bloodveil Syndicate came to prominence in Neverwinter, training the deadliest assassins in Faerun.", j([]), "major", 1),
        (1440, "Aalinjun's Colosseum Policy", "Guildmaster Aalinjun established that Gauntlet contracts are priced at 12x sponsor's expected revenue, effectively pricing the Gauntlet out of Colosseum events.", j([76]), "major", 1),
        (1482, "Bhaalspawn Crisis", "Grand Duke Abdel Adrian died. Council reduced to 3 members. His seat left empty.", j([]), "critical", 1),
        (1494, "Fourth Council Seat Reinstated", "Thalamara Vanthampur elected to the fourth seat on the Council of Four.", j([]), "major", 1),
        (1497, "Duke Portyr Assassinated", "Duke Dillard Portyr assassinated on orders of Duke Vanthampur, who was herself killed. Grand Duke Ravengard sent to Avernus.", j([]), "critical", 1),
        (1498, "Ravengard Returns", "Grand Duke Ravengard returned from Avernus and stabilized the Council.", j([]), "major", 1),
        (1501, "Bloodveil Conspiracy Begins", "The Bloodveil Syndicate systematically targeted Baldur's Gate ruling class with assassination attempts. Aisha Redlocks murdered. Duke Oriel Redlocks's wife.", j([13]), "critical", 1),
        (1501, "Gauntlet Commissioned for Protection", "Four dukes commissioned the Gilded Gauntlet to protect the Upper City and hunt the Bloodveil Syndicate.", j([4, 12, 13, 14]), "critical", 1),
        (1507, "Bloodveil Conspiracy Ends", "The Bloodveil Syndicate believed completely rooted out of Baldur's Gate through Gilded Gauntlet and Blue Dagger efforts.", j([4]), "critical", 1),
        (1509, "Ravenshade Assassinations", "Yuuto Ravenshade and his wife Sibyll assassinated by unknown forces. Alim Thunderfist swore to protect the family. Open Gold rank contract: 1,000,000gp for actionable intel.", j([4, 12, 15]), "critical", 1),
        (1509, "Thunderfist Guards Arnalithah", "Alim Thunderfist personally guarded the orphaned Arnalithah Ravenshade for three years, then trained her in the Way of the Open Hand.", j([4, 15]), "major", 0),
        (1521, "Asahi Ravenshade Dies", "Asahi Ravenshade, husband of Duchess Jade, died of natural causes.", j([12]), "minor", 1),
    ]

    c.executemany(
        """INSERT INTO world_history (year_dr, event_title, event_description, characters_involved, significance, is_public)
           VALUES (?, ?, ?, ?, ?, ?)""",
        events
    )
    print(f"  Seeded {len(events)} world history events")


# ============================================================================
# PLOT THREADS
# ============================================================================

def seed_plot_threads(db: sqlite3.Connection):
    """Seed initial plot threads."""
    c = db.cursor()

    plots = [
        (1, "The Ravenshade Murders", "active", 1,
         "Yuuto Ravenshade and wife Sibyll were assassinated in 1509 by unknown forces. Open Gold rank Gauntlet contract worth 1,000,000gp for actionable intel. Whispers connect the Third Lotus monk-assassins. Contract still active and unsolved."),
        (2, "The Coven of Webs", "dormant", 2,
         "Duchess Olivia Caldwell and Kingpin Psyche Giannini are secretly Mothers in the Coven of Webs, worshipping Lolth. They've infiltrated both the Council of Four and the Blue Dagger. Their Yochlol handmaids guard their secret."),
        (3, "The Cult of Vecna Returns", "dormant", 2,
         "Zorathar the Eternal, an Elder Lich (CR 25), is believed to be a major lieutenant in a reborn Cult of Vecna seeking to bring back the Archlich."),
        (4, "Naelia's Arrival", "active", 1,
         "Naelia An'Ohren has arrived in Baldur's Gate as the Avatar of the Lady / Silver Queen. Her coronation and the revelation of her divine nature will reshape the power dynamics of the entire city."),
        (5, "The Beast's Past", "dormant", 3,
         "Razaaz (The Beast) is a Rakshasa leading the Blue Dagger. His history with Seraphine is undefined and potentially campaign-shaping."),
        (6, "The Lost Platinum Coin", "dormant", 4,
         "Lahmana Firebreath's Platinum Coin — the only one ever minted — was lost when he died fighting Archdevil Yalas in the Hells. Rumors persist about its fate."),
        (7, "Bakallah's Imprisonment", "dormant", 4,
         "Sultan Bakallah al-Sadoof is imprisoned in a golden lamp by his daughter Amirah. His followers from the elemental plane of air have searched for three centuries. Sahlila wants him dead."),
    ]

    c.executemany(
        "INSERT INTO plot_threads (id, title, status, priority, description) VALUES (?, ?, ?, ?, ?)",
        plots
    )

    # Plot characters
    plot_chars = [
        (1, 12, "victim"), (1, 15, "victim"), (1, 4, "protagonist"),
        (2, 11, "antagonist"), (2, 10, "antagonist"), (2, 21, "antagonist"), (2, 22, "antagonist"), (2, 70, "antagonist"),
        (3, 7, "antagonist"), (3, 71, "antagonist"),
        (4, 1, "protagonist"), (4, 2, "protagonist"),
        (5, 9, "protagonist"), (5, 2, "protagonist"),
        (6, 75, "protagonist"), (6, 74, "antagonist"),
        (7, 20, "victim"), (7, 5, "protagonist"), (7, 6, "antagonist"),
    ]
    c.executemany(
        "INSERT INTO plot_characters (plot_thread_id, character_id, role_in_plot) VALUES (?, ?, ?)",
        plot_chars
    )

    # Initial clues
    clues = [
        (1, "A whisper exists that Yuuto Ravenshade earned the ire of the Third Lotus.", 0, None, None, "Underworld rumors"),
        (1, "Alim Thunderfist posted an open Gold rank contract: 1,000,000gp for actionable intel. He waived the 30,000,000gp commission from his own stake.", 1, None, None, "Public knowledge"),
        (2, "Duchess Caldwell's youthful appearance despite age 64 fuels city rumors.", 1, None, None, "Common gossip"),
        (2, "Olivia's handmaids are actually Yochlol — fiend servants of Lolth.", 0, None, None, "Known only to the Coven"),
    ]
    c.executemany(
        "INSERT INTO plot_clues (plot_thread_id, description, is_discovered, discovered_session_id, discovered_by_character_id, source_description) VALUES (?, ?, ?, ?, ?, ?)",
        clues
    )

    print(f"  Seeded {len(plots)} plot threads, {len(plot_chars)} plot characters, {len(clues)} clues")


# ============================================================================
# GUILD CONTRACTS
# ============================================================================

def seed_guild_contracts(db: sqlite3.Connection):
    """Seed the open Ravenshade contract."""
    c = db.cursor()
    c.execute(
        """INSERT INTO guild_contracts (title, description, cr_tier, rank_required,
           stake_gt, reward_gt, reward_gp, status, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        ("Ravenshade Investigation", "Actionable intel on the assassination of Yuuto Ravenshade and wife in 1509. Thunderfist waived the 30,000,000gt commission from his own stake.",
         20, "gold", 0, 0, 1000000, "available", "Open contract. No stake required. Special rules: posted by Guildmaster.")
    )
    print("  Seeded 1 guild contract")


# ============================================================================
# NPC SCHEDULES
# ============================================================================

def seed_npc_schedules(db: sqlite3.Connection):
    """Seed basic NPC schedules."""
    c = db.cursor()
    schedules = [
        # Tara - almost never leaves her shop
        (3, None, 0, 23, "In her magic shop", 306),
        # Alim Thunderfist - at the guildhall
        (4, None, 6, 22, "At the Gilded Gauntlet guildhall", 300),
        (4, None, 22, 6, "Meditating in private quarters above guildhall", 300),
        # Tomas Benedict - at Lady's Hall
        (50, None, 6, 20, "Conducting services and counseling at Lady's Hall", 304),
        # Gilas Benthey - at the Low Lantern
        (56, None, 14, 2, "Managing the Low Lantern", 305),
        # Earow Baker - at Basilisk Gate
        (52, None, 6, 18, "On guard duty at Basilisk Gate", 222),
        # Tima - at Elfsong Tavern
        (54, None, 6, 22, "Working at the Elfsong Tavern", 309),
    ]

    c.executemany(
        "INSERT INTO npc_schedules (character_id, day_of_tenday, hour_start, hour_end, activity, location_id) VALUES (?, ?, ?, ?, ?, ?)",
        schedules
    )
    print(f"  Seeded {len(schedules)} NPC schedule entries")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("Seeding Naelia's Chronicles database...")
    seed_database()

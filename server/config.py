"""Server configuration — loads game_config.json and provides paths."""

import json
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SERVER_DIR = Path(__file__).parent
CONFIG_PATH = PROJECT_ROOT / "game_config.json"
DB_PATH = PROJECT_ROOT / "server" / "world.db"
SCHEMA_PATH = SERVER_DIR / "database" / "schema.sql"
BACKUP_DIR = PROJECT_ROOT / "backups"


def load_config() -> dict:
    """Load game configuration from game_config.json."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


# Load once at import time
CONFIG = load_config()

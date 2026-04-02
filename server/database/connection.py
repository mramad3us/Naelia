"""Database connection management and helpers for SQLite."""

import aiosqlite
import sqlite3
import json
from pathlib import Path
from typing import Any, Optional

from server.config import DB_PATH, SCHEMA_PATH


async def get_db() -> aiosqlite.Connection:
    """Get an async database connection with proper settings."""
    db = await aiosqlite.connect(str(DB_PATH))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode = WAL")
    await db.execute("PRAGMA foreign_keys = ON")
    return db


def get_db_sync() -> sqlite3.Connection:
    """Get a synchronous database connection (for seeding and admin ops)."""
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("PRAGMA foreign_keys = ON")
    return db


async def init_db():
    """Initialize the database from schema.sql if it doesn't exist."""
    if DB_PATH.exists():
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text()

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.executescript(schema_sql)
        await db.commit()


def init_db_sync():
    """Initialize the database synchronously (for scripts)."""
    if DB_PATH.exists():
        return

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text()

    db = sqlite3.connect(str(DB_PATH))
    db.executescript(schema_sql)
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

async def fetch_one(query: str, params: tuple = ()) -> Optional[dict]:
    """Execute a query and return the first row as a dict."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(query, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)


async def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    """Execute a query and return all rows as a list of dicts."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def execute(query: str, params: tuple = ()) -> int:
    """Execute a write query and return the last row ID."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid


async def execute_many(query: str, params_list: list[tuple]):
    """Execute a write query for multiple parameter sets."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executemany(query, params_list)
        await db.commit()


def to_json(obj: Any) -> str:
    """Serialize a Python object to a JSON string for DB storage."""
    return json.dumps(obj, ensure_ascii=False)


def from_json(s: str) -> Any:
    """Deserialize a JSON string from the DB."""
    if s is None:
        return None
    return json.loads(s)


def parse_row_json(row: dict, *json_fields: str) -> dict:
    """Parse specified JSON fields in a row dict."""
    result = dict(row)
    for field in json_fields:
        if field in result and result[field] is not None:
            result[field] = from_json(result[field])
    return result

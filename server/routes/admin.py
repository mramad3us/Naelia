"""Admin routes — backup, restore, health, archival, stats."""

from fastapi import APIRouter

from server.database.backup import create_backup, list_backups, restore_backup
from server.database.connection import fetch_all, fetch_one, execute
from server.config import DB_PATH, CONFIG

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Backup & Restore
# ---------------------------------------------------------------------------

@router.post("/backup")
async def backup_db(label: str = None):
    """Create a timestamped database backup."""
    return create_backup(label)


@router.get("/backups")
async def get_backups():
    """List all available backups."""
    return list_backups()


@router.post("/restore/{filename}")
async def restore_db(filename: str):
    """Restore database from a named backup file."""
    return restore_backup(filename)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def db_stats():
    """Database size, row counts, last backup info."""
    size_kb = DB_PATH.stat().st_size / 1024 if DB_PATH.exists() else 0

    # Row counts for key tables
    tables = [
        "characters", "organizations", "locations", "plot_threads",
        "sessions", "session_events", "dice_rolls", "combat_encounters",
        "era_summaries", "items", "guild_contracts",
    ]
    counts = {}
    for table in tables:
        row = await fetch_one(f"SELECT COUNT(*) as cnt FROM {table}")
        counts[table] = row["cnt"] if row else 0

    # Last backup
    backups = list_backups()
    last_backup = backups[0] if backups else None

    # Schema version
    sv = await fetch_one("SELECT version, applied_at FROM schema_version ORDER BY version DESC LIMIT 1")

    return {
        "db_size_kb": round(size_kb, 1),
        "row_counts": counts,
        "last_backup": last_backup,
        "schema_version": sv,
    }


# ---------------------------------------------------------------------------
# Archival
# ---------------------------------------------------------------------------

@router.post("/archive")
async def trigger_archive():
    """Trigger an archival pass: summarize old sessions and prune stale data."""
    trigger_count = CONFIG.get("session", {}).get("archival_trigger_sessions", 10)
    max_dice = CONFIG.get("session", {}).get("max_dice_rolls_kept", 500)

    # Find sessions eligible for archival
    sessions = await fetch_all(
        "SELECT * FROM sessions WHERE is_archived = 0 AND ended_at IS NOT NULL ORDER BY session_number"
    )

    if len(sessions) < trigger_count:
        return {
            "archived": False,
            "reason": f"Only {len(sessions)} completed sessions (need {trigger_count})",
        }

    # Archive the oldest batch
    to_archive = sessions[:trigger_count]
    session_ids = [s["id"] for s in to_archive]
    first_num = to_archive[0]["session_number"]
    last_num = to_archive[-1]["session_number"]

    # Gather events for era summary
    placeholders = ",".join("?" * len(session_ids))
    events = await fetch_all(
        f"SELECT * FROM session_events WHERE session_id IN ({placeholders}) ORDER BY created_at",
        tuple(session_ids),
    )

    # Build era summary text
    event_descriptions = [e["description"] for e in events if e["description"]]
    summary_text = (
        f"Era covering sessions {first_num}-{last_num}. "
        f"{len(events)} events across {len(session_ids)} sessions.\n\n"
        + "\n".join(f"- {d}" for d in event_descriptions[:100])
    )

    # Get date range
    in_game_start = to_archive[0].get("in_game_start_date", "unknown")
    in_game_end = to_archive[-1].get("in_game_end_date", "unknown")

    # Create era summary
    era_id = await execute(
        """INSERT INTO era_summaries
           (session_range_start, session_range_end, in_game_date_start, in_game_date_end,
            summary, key_events, character_states, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (
            first_num, last_num, in_game_start, in_game_end,
            summary_text, "[]", "[]",
        ),
    )

    # Mark sessions as archived
    await execute(
        f"UPDATE sessions SET is_archived = 1 WHERE id IN ({placeholders})",
        tuple(session_ids),
    )

    # Prune old dice rolls (keep only max_dice most recent)
    dice_count_row = await fetch_one("SELECT COUNT(*) as cnt FROM dice_rolls")
    dice_count = dice_count_row["cnt"] if dice_count_row else 0
    if dice_count > max_dice:
        await execute(
            f"""DELETE FROM dice_rolls WHERE id IN (
                SELECT id FROM dice_rolls ORDER BY created_at ASC LIMIT ?
            )""",
            (dice_count - max_dice,),
        )

    # Prune archived session events
    await execute(
        f"DELETE FROM session_events WHERE session_id IN ({placeholders})",
        tuple(session_ids),
    )

    return {
        "archived": True,
        "era_id": era_id,
        "sessions_archived": len(session_ids),
        "session_range": f"{first_num}-{last_num}",
        "events_summarized": len(events),
        "dice_rolls_pruned": max(0, dice_count - max_dice),
    }

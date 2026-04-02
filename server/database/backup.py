"""Database backup and restore operations."""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from server.config import DB_PATH, BACKUP_DIR, CONFIG


def create_backup(label: str = None) -> dict:
    """Create a timestamped backup of the database."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = f"_{label}" if label else ""
    filename = f"world_{timestamp}{suffix}.db"
    backup_path = BACKUP_DIR / filename

    # Use SQLite backup API for consistency
    source = sqlite3.connect(str(DB_PATH))
    dest = sqlite3.connect(str(backup_path))
    source.backup(dest)
    dest.close()
    source.close()

    size_kb = backup_path.stat().st_size / 1024

    # Log in backups table
    db = sqlite3.connect(str(DB_PATH))
    db.execute(
        "INSERT INTO backups (file_path, size_bytes, notes) VALUES (?, ?, ?)",
        (str(backup_path), backup_path.stat().st_size, filename),
    )
    db.commit()
    db.close()

    # Prune old backups
    max_kept = CONFIG.get("backup", {}).get("max_backups_kept", 100)
    _prune_backups(max_kept)

    return {
        "filename": filename,
        "path": str(backup_path),
        "size_kb": round(size_kb, 1),
        "created_at": datetime.now().isoformat(),
    }


def list_backups() -> list[dict]:
    """List all backup files."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = sorted(BACKUP_DIR.glob("world_*.db"), key=lambda p: p.name, reverse=True)
    return [
        {
            "filename": p.name,
            "path": str(p),
            "size_kb": round(p.stat().st_size / 1024, 1),
            "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        }
        for p in backups
    ]


def restore_backup(filename: str) -> dict:
    """Restore from a backup file. Returns info about the restored backup."""
    backup_path = BACKUP_DIR / filename
    if not backup_path.exists():
        return {"error": f"Backup not found: {filename}"}

    # Create a safety backup before restoring
    safety = create_backup(label="pre_restore")

    # Replace current DB
    shutil.copy2(str(backup_path), str(DB_PATH))

    return {
        "restored_from": filename,
        "safety_backup": safety["filename"],
        "size_kb": round(backup_path.stat().st_size / 1024, 1),
    }


def _prune_backups(max_kept: int):
    """Remove oldest backups if over the limit."""
    backups = sorted(BACKUP_DIR.glob("world_*.db"), key=lambda p: p.name)
    while len(backups) > max_kept:
        oldest = backups.pop(0)
        oldest.unlink()

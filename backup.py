"""Database backup utilities for Finance Tracker.

Backups are stored in <project_root>/backups/ as timestamped SQLite files.
Up to MAX_BACKUPS recent backups are kept; older ones are pruned automatically.

This module is used both by the automatic scheduler inside app.py and by the
standalone backup_db.py script for on-demand use.
"""

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Directory where backups are stored
BACKUP_DIR: Path = Path(__file__).parent / 'backups'

# Maximum number of backups to keep (older ones are pruned)
MAX_BACKUPS: int = 7

_TIMESTAMP_FMT = '%Y-%m-%d_%H-%M-%S'
_BACKUP_PREFIX = 'finance_tracker_'


def get_db_path() -> Path:
    """Resolve the SQLite database file path from the environment or config."""
    uri = os.environ.get('DATABASE_URL') or 'sqlite:///finance_tracker.db'
    if not uri.startswith('sqlite:///'):
        scheme = uri.split(':')[0]
        raise ValueError(
            f"Backup only supports SQLite databases; found scheme '{scheme}'. "
            "Run backup_db.py only when DATABASE_URL points to a SQLite file."
        )
    # sqlite:///relative.db  → <project>/instance/relative.db
    # sqlite:////absolute.db → /absolute.db
    rel = uri[len('sqlite:///'):]
    if os.path.isabs(rel):
        return Path(rel)
    return Path(__file__).parent / 'instance' / rel


def backup_database() -> Path:
    """Create a timestamped backup of the SQLite database.

    Uses sqlite3's online backup API so the database can be backed up safely
    even while the Flask app is running and writing to it.

    Returns:
        Path to the newly created backup file.

    Raises:
        FileNotFoundError: If the source database does not exist.
        ValueError: If the configured DATABASE_URL is not a SQLite URI.
    """
    db_path = get_db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime(_TIMESTAMP_FMT)
    backup_path = BACKUP_DIR / f'{_BACKUP_PREFIX}{timestamp}.db'

    src = sqlite3.connect(str(db_path))
    try:
        dst = sqlite3.connect(str(backup_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    size_kb = backup_path.stat().st_size / 1024
    logger.info('Backup created: %s (%.1f KB)', backup_path.name, size_kb)
    _prune_old_backups()
    return backup_path


def list_backups() -> list[Path]:
    """Return all backup files sorted oldest-first."""
    if not BACKUP_DIR.exists():
        return []
    return sorted(BACKUP_DIR.glob(f'{_BACKUP_PREFIX}*.db'))


def get_last_backup_time() -> datetime | None:
    """Return the datetime of the most recent backup, or None if none exist."""
    backups = list_backups()
    if not backups:
        return None
    stem = backups[-1].stem  # e.g. finance_tracker_2024-01-15_10-30-00
    ts_str = stem[len(_BACKUP_PREFIX):]
    try:
        return datetime.strptime(ts_str, _TIMESTAMP_FMT)
    except ValueError:
        return None


def _prune_old_backups() -> None:
    """Delete the oldest backups beyond MAX_BACKUPS."""
    backups = list_backups()
    for old in backups[:-MAX_BACKUPS]:
        old.unlink()
        logger.info('Pruned old backup: %s', old.name)

"""Tests for database backup functionality (backup.py)."""

import sqlite3
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Create a minimal SQLite database for testing."""
    db = tmp_path / 'finance_tracker.db'
    conn = sqlite3.connect(str(db))
    conn.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, val TEXT)')
    conn.execute("INSERT INTO test VALUES (1, 'hello')")
    conn.commit()
    conn.close()
    return db


@pytest.fixture
def backup_env(tmp_path: Path, tmp_db: Path):
    """Patch backup module so it uses tmp_path instead of real directories."""
    import backup as bk

    backup_dir = tmp_path / 'backups'
    with (
        patch.object(bk, 'BACKUP_DIR', backup_dir),
        patch('backup.get_db_path', return_value=tmp_db),
    ):
        yield {'backup_dir': backup_dir, 'db': tmp_db}


# ---------------------------------------------------------------------------
# backup_database()
# ---------------------------------------------------------------------------

def test_backup_creates_file(backup_env: dict) -> None:
    from backup import backup_database

    path = backup_database()

    assert path.exists()
    assert path.suffix == '.db'
    assert 'finance_tracker_' in path.name


def test_backup_directory_created_automatically(backup_env: dict) -> None:
    from backup import backup_database

    assert not backup_env['backup_dir'].exists()
    backup_database()
    assert backup_env['backup_dir'].exists()


def test_backup_is_valid_sqlite(backup_env: dict) -> None:
    from backup import backup_database

    path = backup_database()
    conn = sqlite3.connect(str(path))
    rows = conn.execute('SELECT val FROM test').fetchall()
    conn.close()

    assert rows == [('hello',)]


def test_backup_name_contains_today(backup_env: dict) -> None:
    from backup import backup_database

    today = datetime.now().strftime('%Y-%m-%d')
    path = backup_database()

    assert today in path.name


def test_backup_fails_if_db_missing(tmp_path: Path) -> None:
    import backup as bk

    missing = tmp_path / 'nonexistent.db'
    backup_dir = tmp_path / 'backups'
    with (
        patch.object(bk, 'BACKUP_DIR', backup_dir),
        patch('backup.get_db_path', return_value=missing),
    ):
        with pytest.raises(FileNotFoundError):
            bk.backup_database()


# ---------------------------------------------------------------------------
# Pruning
# ---------------------------------------------------------------------------

def _seed_fake_backups(backup_dir: Path, count: int) -> list[Path]:
    """Create empty SQLite files with distinct timestamps in backup_dir."""
    backup_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(count):
        name = backup_dir / f'finance_tracker_2024-01-15_10-00-{i:02d}.db'
        sqlite3.connect(str(name)).close()
        paths.append(name)
    return paths


def test_prune_keeps_only_max_backups(backup_env: dict) -> None:
    import backup as bk

    _seed_fake_backups(backup_env['backup_dir'], 5)
    original_max = bk.MAX_BACKUPS
    bk.MAX_BACKUPS = 3
    try:
        bk._prune_old_backups()
        remaining = bk.list_backups()
        assert len(remaining) == 3
    finally:
        bk.MAX_BACKUPS = original_max


def test_prune_keeps_newest_backups(backup_env: dict) -> None:
    import backup as bk

    all_files = _seed_fake_backups(backup_env['backup_dir'], 4)
    original_max = bk.MAX_BACKUPS
    bk.MAX_BACKUPS = 2
    try:
        bk._prune_old_backups()
        kept = bk.list_backups()
        assert kept == sorted(all_files)[-2:]
    finally:
        bk.MAX_BACKUPS = original_max


# ---------------------------------------------------------------------------
# list_backups()
# ---------------------------------------------------------------------------

def test_list_backups_empty_when_no_backup_dir(backup_env: dict) -> None:
    from backup import list_backups

    assert list_backups() == []


def test_list_backups_returns_sorted_paths(backup_env: dict) -> None:
    from backup import list_backups

    seeded = _seed_fake_backups(backup_env['backup_dir'], 3)
    backups = list_backups()

    assert len(backups) == 3
    assert backups == sorted(seeded)


# ---------------------------------------------------------------------------
# get_last_backup_time()
# ---------------------------------------------------------------------------

def test_get_last_backup_time_none_when_no_backups(backup_env: dict) -> None:
    from backup import get_last_backup_time

    assert get_last_backup_time() is None


def test_get_last_backup_time_returns_recent_datetime(backup_env: dict) -> None:
    from backup import backup_database, get_last_backup_time

    backup_database()
    result = get_last_backup_time()

    assert isinstance(result, datetime)
    assert (datetime.now() - result).total_seconds() < 60


# ---------------------------------------------------------------------------
# get_db_path()
# ---------------------------------------------------------------------------

def test_get_db_path_defaults_to_instance_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('DATABASE_URL', raising=False)
    from backup import get_db_path

    path = get_db_path()

    assert path.name == 'finance_tracker.db'
    assert 'instance' in str(path)


def test_get_db_path_absolute_sqlite_uri(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # sqlite:/// + absolute_path = sqlite:////path (4 slashes total)
    # tmp_path already starts with '/', so just prefix sqlite:///
    absolute_uri = 'sqlite:///' + str(tmp_path / 'mydb.db')
    monkeypatch.setenv('DATABASE_URL', absolute_uri)
    from backup import get_db_path

    path = get_db_path()

    assert path == tmp_path / 'mydb.db'


def test_get_db_path_non_sqlite_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost/db')
    from backup import get_db_path

    with pytest.raises(ValueError, match='SQLite'):
        get_db_path()

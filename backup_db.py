#!/usr/bin/env python3
"""Finance Tracker — on-demand database backup tool.

Commands:
    python backup_db.py              Create a backup now (default)
    python backup_db.py list         List all existing backups
    python backup_db.py restore NAME Restore from a named backup file
"""

import argparse
import sqlite3
import sys
from pathlib import Path

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).parent))

from backup import BACKUP_DIR, backup_database, get_db_path, list_backups


def cmd_backup() -> None:
    print('Creating backup…')
    path = backup_database()
    size_kb = path.stat().st_size / 1024
    print(f'Done.')
    print(f'  File : {path.name}')
    print(f'  Size : {size_kb:.1f} KB')
    print(f'  Dir  : {BACKUP_DIR}')


def cmd_list() -> None:
    backups = list_backups()
    if not backups:
        print(f'No backups found in {BACKUP_DIR}')
        return
    print(f'Backups in {BACKUP_DIR}:\n')
    print(f"  {'Name':<48} {'Size':>9}")
    print(f"  {'-'*48} {'-'*9}")
    for b in backups:
        size_kb = b.stat().st_size / 1024
        print(f'  {b.name:<48} {size_kb:>8.1f} KB')
    print(f'\n{len(backups)} backup(s) total.')


def cmd_restore(filename: str) -> None:
    backup_path = BACKUP_DIR / filename
    if not backup_path.exists():
        print(f'Error: backup not found: {backup_path}', file=sys.stderr)
        sys.exit(1)

    db_path = get_db_path()
    print(f'Source  : {backup_path.name}')
    print(f'Target  : {db_path}')
    print()
    confirm = input('This will overwrite the current database. Type "yes" to confirm: ')
    if confirm.strip().lower() != 'yes':
        print('Restore cancelled.')
        return

    # Safety: back up the current DB before overwriting it
    print('\nCreating safety backup of current database first…')
    safety = backup_database()
    print(f'Safety backup: {safety.name}')

    print('Restoring…')
    src = sqlite3.connect(str(backup_path))
    try:
        dst = sqlite3.connect(str(db_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    print(f'Restored successfully from: {filename}')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Finance Tracker database backup tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest='cmd')
    sub.add_parser('list', help='List existing backups')
    restore_p = sub.add_parser('restore', help='Restore from a backup')
    restore_p.add_argument(
        'filename',
        help='Backup filename, e.g. finance_tracker_2024-01-15_10-30-00.db',
    )

    args = parser.parse_args()

    try:
        if args.cmd == 'list':
            cmd_list()
        elif args.cmd == 'restore':
            cmd_restore(args.filename)
        else:
            cmd_backup()
    except KeyboardInterrupt:
        print('\nAborted.')
        sys.exit(1)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

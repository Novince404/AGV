from __future__ import annotations

import argparse

from app.database.maintenance import (
    backup_database,
    database_status,
    print_result,
    restore_database,
    upgrade_database,
    verify_database,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agv", description="AGV enterprise maintenance CLI")
    groups = parser.add_subparsers(dest="group", required=True)
    database = groups.add_parser("database", help="Database maintenance")
    commands = database.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Show connection and schema version")
    backup = commands.add_parser("backup", help="Create a verified SQLite backup")
    backup.add_argument("--destination")
    upgrade = commands.add_parser("upgrade", help="Back up and migrate to the current schema")
    upgrade.add_argument("--backup-confirmed", action="store_true", help="Confirm an external MySQL backup exists")
    commands.add_parser("verify", help="Verify the enterprise schema")
    restore = commands.add_parser("restore", help="Restore a SQLite backup")
    restore.add_argument("backup_path")
    restore.add_argument("--sha256")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "check":
        result = database_status()
    elif args.command == "backup":
        result = backup_database(args.destination)
    elif args.command == "upgrade":
        result = upgrade_database(mysql_backup_confirmed=args.backup_confirmed)
    elif args.command == "verify":
        result = verify_database()
    elif args.command == "restore":
        result = restore_database(args.backup_path, expected_sha256=args.sha256)
    else:
        raise AssertionError(f"Unsupported command: {args.command}")
    print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

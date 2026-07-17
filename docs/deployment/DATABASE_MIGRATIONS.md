# Database migration, backup, and recovery

The v3 schema is versioned with Alembic. The repository-root `VERSION` names
the application release; the database revision is reported separately by the
maintenance command. Treat them as related but different pieces of state.

## Maintenance commands

Run these from `backend/` with the same `AGV_*` environment used by the
application:

```powershell
python agv.py database check
python agv.py database backup
python agv.py database upgrade
python agv.py database verify
python agv.py database restore <backup_path> --sha256 <expected_sha256>
```

`check` reports the connection, recognised predecessor shape, known tables,
and Alembic revision. `verify` checks the required v3 core/foundation tables,
key expanded columns, expected revision, and SQLite integrity. These commands
do not erase application rows.

For an actual upgrade, the JSON result also records counts for accounts,
enterprise applications, AGVs, tasks, maps, topology records, feedback, and
audit events before and after the migration. Keep that output with the release
record and investigate any unexpected count difference before serving traffic.

## SQLite procedure

SQLite is appropriate for a single-machine demo or packaged trial, not the
multi-container deployment in `docker-compose.yml`.

1. Stop the application and scheduler.
2. Set `AGV_DATA_BACKEND=sqlite` and the exact `AGV_DATABASE_URL`.
3. Run `python agv.py database check` and save its output with the release
   record.
4. Run `python agv.py database upgrade`. The tool automatically creates a
   transactionally consistent SQLite snapshot (including committed WAL data)
   and prints its SHA-256 checksum before a schema change.
5. Run `python agv.py database verify`, start the service, and validate
   accounts, organizations, maps, AGVs, tasks, and audit/event counts.
6. If validation fails, stop the service and use `database restore` with the
   generated backup path and checksum. Restore verifies the backup before it
   replaces the target database and clears stale SQLite journal sidecars. The Alembic downgrade path is
   deliberately non-destructive; a verified backup is the rollback mechanism.

## MySQL procedure

MySQL is the Docker trial default. The tool refuses a MySQL upgrade until the
operator explicitly passes `--backup-confirmed`.

1. Create a consistent MySQL backup with your managed-backup system or
   `mysqldump`, and verify that it can be read or restored in an isolated
   environment.
2. Record the current `database check` output and the backup location/checksum
   outside the repository.
3. Stop the API and scheduler, or schedule a maintenance window so no new
   commands are accepted.
4. Run:

   ```powershell
   python agv.py database upgrade --backup-confirmed
   python agv.py database verify
   ```

5. Start the scheduler, API, and a representative role-based smoke test. Check
   data counts and key records before returning to normal use.

In Docker Compose, the one-shot `migrate` service follows the same rule. It
requires `AGV_MYSQL_BACKUP_CONFIRMED=yes`; this value is an explicit operator
acknowledgement, not a substitute for the backup itself.

## Legacy database recognition

For a known unversioned v2/beta schema, the maintenance command identifies the
expected legacy tables, stamps the baseline revision, and applies forward
migrations. It refuses to stamp an unknown unversioned schema. In that case,
do not force an upgrade: preserve a copy, compare it with a supported sample,
and prepare a dedicated migration after review.

v3 migrations use an expand/contract strategy: add new tables/columns first
and avoid destructive removal within the trial line. This minimizes rollback
risk but still requires a backup before every material upgrade.

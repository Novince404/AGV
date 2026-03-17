# v2.0.0-beta.1 - Database Integration Beta and A3 Persistence Upgrade

This beta release marks the first major database-backed milestone of the AGV dispatch system. The project now supports validated `memory`, `sqlite`, and `mysql` workflows, while keeping the existing scheduling and map interactions compatible for daily development and demos.

## Highlights

- Introduced backend `.env` loading so runtime database mode can be switched without editing source code.
- Added dedicated SQLite and MySQL validation/startup scripts for A3 database-mode testing.
- Connected frontend point-library and task-template flows to backend APIs with local fallback and legacy migration support.
- Improved SQL persistence timing to avoid incomplete task snapshots during assignment.
- Upgraded the project to a beta release line to reflect the significance of real database integration.

## Added

- `backend/scripts/sqlite_smoke_check.py`
- `backend/scripts/mysql_config_check.py`
- `run_sqlite_smoke.bat`
- `run_mysql_check.bat`
- `run_mysql_dev.bat`
- `frontend/agv-frontend/src/composables/usePointTemplateBackend.js`
- backend `.env` file support through `backend/app/core/settings.py`

## Improved

- `run_dev.bat` now follows `backend/.env` configuration automatically.
- Frontend point and template management now prefers backend persistence while keeping local fallback behavior available.
- Legacy localStorage custom points/templates can now be migrated into backend-backed storage.
- Database documentation and environment examples are cleaner and better aligned with actual A3 workflows.

## Fixed

- Fixed MySQL startup failures caused by missing support for current MySQL authentication methods by explicitly requiring `cryptography`.
- Fixed SQL persistence timing issues that could produce partially saved assigned-task state.
- Fixed repeated map-based task creation flow while active runtime visuals are present.
- Fixed several database-mode preparation gaps across startup, validation, and persistence tooling.

## Validation

- Frontend lint passed.
- Backend Python compile checks passed for key updated modules.
- SQLite smoke check passed with:
  - point persistence
  - template persistence
  - map / blocked-cell persistence
- MySQL configuration check passed with:
  - driver available
  - connection successful
  - auto-create completed

## Notes

- This is a **beta** release, not the final `2.0.0` stable release.
- The project still supports `memory` mode as the safest daily development path.
- `sqlite` and `mysql` are now available as validated persistence modes for A3.
- No desktop release asset is attached in this version.

## Suggested GitHub Release Fields

- **Tag**: `v2.0.0-beta.1`
- **Target**: `main`
- **Release title**: `v2.0.0-beta.1 - Database Integration Beta and A3 Persistence Upgrade`

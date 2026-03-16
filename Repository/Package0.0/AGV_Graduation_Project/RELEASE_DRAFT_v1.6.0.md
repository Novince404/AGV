# v1.6.0 - A3 Persistence Foundation and SQLite Validation Update

This release extends the A3 backend restructuring work by moving more runtime data toward repository-backed persistence while keeping the current in-memory workflow stable for daily development and demos. It also adds a practical SQLite validation path so the database-backed direction can be tested locally before full MySQL rollout.

## Highlights

- Added real persistence scaffolding for map layout, blocked cells, point library, and task templates.
- Expanded SQL-backed repository support beyond AGV/task/fault into map, point, and template data flows.
- Added backend APIs for point-library and task-template management.
- Added one-click SQLite development startup support for local database-mode validation.
- Kept default `memory` mode behavior compatible so current scheduling demos continue to run as before.

## Added

- `backend/app/models/point_library.py`
- `backend/app/models/task_template.py`
- `backend/app/models/tracked_model.py`
- `backend/app/repositories/map_repository.py`
- `backend/app/repositories/point_repository.py`
- `backend/app/repositories/template_repository.py`
- `backend/app/repositories/memory/map_store.py`
- `backend/app/repositories/memory/point_store.py`
- `backend/app/repositories/memory/template_store.py`
- `backend/app/repositories/sql/map_store.py`
- `backend/app/repositories/sql/point_store.py`
- `backend/app/repositories/sql/template_store.py`
- `backend/app/services/point_service.py`
- `backend/app/services/template_service.py`
- `backend/app/schemas/point.py`
- `backend/app/schemas/template.py`
- `backend/app/api/point_api.py`
- `backend/app/api/template_api.py`
- `run_sqlite_dev.bat`

## Improved

- Upgraded SQL repository adapters from temporary proxy-style stubs to ORM-backed cache/persist logic for AGV, task, fault, map, point, and template domains.
- Improved warehouse-map runtime state handling so layout and blocked-cell changes now flow through repository facades instead of only module-level globals.
- Improved backend seed data so point-library and task-template structures are ready for future frontend integration.
- Improved database documentation and environment templates for switching between `memory`, `sqlite`, and `mysql`.

## Fixed

- Fixed SQL-mode persistence gaps where runtime object mutations could be lost without a tracked save path.
- Fixed map-layout persistence preparation so blocked-cell updates and reset flows can be validated under SQLite-backed execution.
- Fixed A3 backend integration gaps by wiring point/template routes into `backend/main.py` while preserving default memory-mode compatibility.

## New API Endpoints

- `GET /point/list`
- `POST /point/upsert`
- `DELETE /point/{point_id}`
- `GET /template/list`
- `POST /template/upsert`
- `DELETE /template/{template_id}`

## Validation

- Frontend lint passed.
- Backend Python compile checks passed for key modules.
- SQLite smoke checks passed for:
  - AGV/task persistence flow
  - map layout and blocked-cell persistence
  - point/template repository and API persistence flow

## Notes

- The system still uses the in-memory runtime by default.
- SQLite is now prepared as a practical intermediate validation mode before full MySQL migration.
- No desktop release asset is attached in this version.

## Suggested GitHub Release Fields

- **Tag**: `v1.6.0`
- **Target**: `main`
- **Release title**: `v1.6.0 - A3 Persistence Foundation and SQLite Validation Update`

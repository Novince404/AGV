# Changelog

## Unreleased

### Added
- Added root-level implementation plan sources `PROJECT_IMPLEMENTATION_PLAN_v2.0.md` and `PROJECT_IMPLEMENTATION_PLAN_v2.0.docx` for the next graduation-project delivery stage.
- Added backend UI settings persistence with `GET /status/ui-settings` and `PUT /status/ui-settings`.
- Added frontend `useUiSettingsBackend.js` so map display settings can be synchronized to backend storage with local fallback kept in place.
- Added Windows packaging skeleton files: `build_frontend_dist.bat`, `run_packaged_dev.bat`, `build_windows_package.bat`, `start_agv.bat`, `backend/package_entry.py`, `backend/packaging/backend.spec`, and `backend/requirements-package.txt`.
- Added `PACKAGING_WINDOWS.md` to document the lowest-deliverable Windows packaging flow.
- Added minimum-delivery documentation set:
  - `QUICKSTART_MINIMUM_DELIVERY.md`
  - `SQLITE_DEMO_GUIDE.md`
  - `DEMO_SCRIPT_MINIMUM_DELIVERY.md`
  - `TEST_CHECKLIST_MINIMUM_DELIVERY.md`
  - `TROUBLESHOOTING_MINIMUM_DELIVERY.md`
  - `RELEASE_STRATEGY.md`

### Improved
- Improved the map settings panel by grouping map information, obstacle layout actions, and persisted display settings into a clearer MVP structure.
- Improved obstacle-layout, JSON-template, and task-management related UI wording/layout while keeping the current workflow intact.
- Improved map layout refresh handling so current grid information and active preset information are reflected in the settings panel.
- Improved frontend API base resolution so the app can run both under Vite (`5173 -> 8000`) and under backend-hosted packaged mode (`8000 -> 8000`).
- Improved backend settings loading so packaged runtime can locate `.env`, bundled frontend dist, and a default SQLite database path more reliably.
- Improved packaging verification flow by adding a buildable one-folder package and validating both packaged-dev mode and packaged `backend.exe` startup smoke tests.

### Fixed
- Fixed multilingual gaps for recently added task-management and map-setting labels across Chinese, English, and Japanese locale files.
- Fixed backend/frontend mismatch for map display settings by storing legend layout, opacity, minimap visibility, marker visibility, path arrows, compare mode, and sidebar section state in one shared payload.
- Fixed packaged-mode readiness gaps by allowing FastAPI to serve frontend `dist` directly when enabled.

## v2.0.0-beta.1 - 2026-03-17

### Added
- Added backend `.env` loading support so database mode and connection settings can be managed from `backend/.env`.
- Added `run_mysql_check.bat` and `run_mysql_dev.bat` for one-click MySQL validation and startup.
- Added `backend/scripts/mysql_config_check.py` and `backend/scripts/sqlite_smoke_check.py` for database-mode self-checks.
- Added `frontend/agv-frontend/src/composables/usePointTemplateBackend.js` to connect point-library and template flows to backend APIs.

### Improved
- Improved frontend point/template persistence so backend APIs are preferred while local fallback and legacy localStorage migration remain available.
- Improved developer startup scripts so `run_dev.bat` follows `backend/.env`, while dedicated SQLite/MySQL launchers are available for A3 testing.
- Improved database documentation and environment examples for `memory`, `sqlite`, and `mysql` workflows.

### Fixed
- Fixed MySQL mode startup preparation by documenting and requiring `cryptography` for current authentication methods.
- Fixed SQL persistence timing so assigned tasks and AGV bindings are written as one complete state instead of partial snapshots.
- Fixed automatic draft-marker display conditions while preparing repeated map-based task creation during active runtime.

## v1.6.0 - 2026-03-16

### Added
- Added tracked backend models so SQL-backed AGV, task, task-stage, and fault-event objects can persist mutation-heavy runtime changes during the A3 transition.
- Added map-layout repository facade plus `memory/sql` map stores for blocked-cell and grid-size persistence preparation.
- Added point-library and task-template backend models, repositories, services, schemas, and API endpoints:
  - `GET /point/list`
  - `POST /point/upsert`
  - `DELETE /point/{point_id}`
  - `GET /template/list`
  - `POST /template/upsert`
  - `DELETE /template/{template_id}`
- Added `run_sqlite_dev.bat` for one-click local SQLite validation alongside the normal dev startup flow.

### Improved
- Improved SQL repository adapters so AGV, task, fault, map, point, and template storage now use real ORM-backed cache/persist logic instead of temporary pure-memory proxy stubs.
- Improved warehouse-map runtime handling so layout state now flows through repository facades instead of only module-level blocked-cell globals.
- Improved database documentation and environment templates for switching between `memory`, `sqlite`, and `mysql` modes during A3 validation.
- Improved default backend seed data so point-library and task-template structures are ready for later frontend-to-backend migration.

### Fixed
- Fixed SQL-mode persistence gaps where runtime object field mutations could be lost without an explicit save path.
- Fixed map-layout persistence preparation so blocked-cell updates and resets can be validated under SQLite-backed execution.
- Fixed A3 backend extension gaps by wiring point/template routes into `backend/main.py` and keeping default memory behavior compatible.

## v1.5.0 - 2026-03-15

### Added
- Added A3 backend layering groundwork, including repository facades, `memory/` and `sql/` store entry points, startup lifecycle initialization, and database environment templates.
- Added SQL-side ORM models and mapper helpers for AGV, task, task-stage, and fault-event persistence preparation.
- Added extracted frontend task-display and task-preview composables to reduce `App.vue` coupling.
- Added direct path-algorithm switching from the right-side dispatch-control panel.

### Improved
- Improved backend service structure so task, schedule, AGV, fault, status, and movement flows now rely on repository helpers instead of scattered direct list access.
- Improved database bootstrap flow and documentation for future MySQL integration while keeping the current in-memory behavior compatible.
- Improved auto/manual scheduling consistency by passing explicit `schedule_mode` through the frontend-backend scheduling chain.

### Fixed
- Fixed automatic map-created tasks being misclassified as manual tasks after scheduling.
- Fixed maintenance/offline AGV occupancy inconsistencies between frontend visibility and backend movement blocking.
- Fixed several task-marker and preview sync issues while continuing the `App.vue` display-layer cleanup.

## v1.4.0 - 2026-03-11

### Added
- Added AGV emergency-stop, resume, fault report, fault list, and fault resolve support.
- Added a fault-event panel and AGV control actions in the frontend sidebar.
- Added AGV status legend layout and opacity settings.
- Added locale modules under `src/locales/` to externalize frontend multilingual text.
- Added a minimal AGV cell-occupancy guard to avoid multiple AGVs entering the same grid cell at the same time.

### Improved
- Improved manual-dispatch cleanup so selected AGV, markers, and preview paths clear automatically after task completion.
- Improved auto-dispatch task creation flow to avoid false “task not schedulable” conflicts caused by scheduling race conditions.
- Improved frontend selection controls and retained fault/emergency controls on the selected AGV card.
- Improved dispatch-reason localization, including AGV fault stop, emergency stop, and occupied-cell interruption reasons.

### Fixed
- Fixed repeated mojibake and broken inline multilingual strings in `App.vue`.
- Fixed map-interaction edge cases where auto mode and manual mode states could interfere with each other.
- Fixed AGV overlap cases where multiple vehicles could previously occupy the same cell while moving or stopping.

## v1.3.0 - 2026-03-10

### Added
- Added obstacle-map support with editable blocked cells, preset warehouse scenes, and obstacle import/export.
- Added drag-paint obstacle editing on the main map.
- Added algorithm comparison for `simple` and `A*`, including panel mode and floating-window mode.
- Added blocked-task retry support so individual unreachable tasks can switch to `A*`.
- Added backend obstacle-layout and blocked-task retry endpoints.

### Improved
- Improved scheduling behavior under obstacle maps and further aligned backend path planning with frontend rendering.
- Improved algorithm switching in the task-creation area and compare-entry behavior from the top toolbar.
- Improved settings panel usability and compare display options.
- Improved blocked-task handling so tasks can wait for an idle AGV after switching to `A*`.

### Fixed
- Fixed out-of-grid coordinates entering task creation or scheduling flows.
- Fixed `simple` unreachable tasks remaining unclear in the pending queue.
- Fixed missing feedback for unreachable routes during map-based point selection.
- Fixed compare-entry expansion and detailed-view opening behavior.

## v1.2.0 - 2026-03-03

### Added
- Added richer stage-task interactions, including map-based point picking with configurable planned stage count.
- Added task JSON example generation and downloadable sample files for single-stage and multi-stage tasks.
- Added direct dispatch-mode switching from the control panel.

### Improved
- Improved chained-task template, JSON, and queue workflows for multi-stage transport scenarios.
- Improved map interaction details, including transfer-point markers, task creation controls, and task-builder flow.
- Improved right-side control panel usability, task grouping, and queue/card fold interactions.

### Fixed
- Fixed stage-task point-picking behavior so planned stage count is decoupled from the editable stage form.
- Fixed several task-creation prompts, marker-display issues, and interaction inconsistencies in the frontend.

## v1.1.0 - 2026-03-02

### Added
- Added unified map interaction support: wheel zoom, left-drag panning, minimap navigation, and view reset.
- Added display settings for auto paths, start/end markers, path arrows, minimap, and AGV status hints.
- Added task template import/export, custom point management, panel search, collapsible sections, and summary modes.
- Added stage-task support for chained workflows such as `A -> B -> C`.
- Added browser auto-open support to `run_dev.bat`.

### Improved
- Unified backend and frontend path display behavior.
- Improved automatic scheduling and manual dispatch interaction flow.
- Improved task queue visibility with dispatch reason, progress, and richer status presentation.
- Improved page layout, right-side panel usability, and map workspace ratio.

### Fixed
- Fixed several path display sync issues between scheduling state and UI rendering.
- Fixed multiple settings persistence issues after refresh.
- Fixed several task/path clearing and interaction edge cases during repeated scheduling.

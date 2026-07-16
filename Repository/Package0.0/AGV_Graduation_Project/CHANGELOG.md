# Changelog

## Unreleased

### Added
- Added the PolyForm Noncommercial License 1.0.0 with clear Chinese and English terms for free noncommercial learning and research use; commercial use requires prior written permission.
- Added the module-5 auth mainline foundation with seeded `personal / enterprise / admin` demo accounts plus backend `POST /auth/login`, `POST /auth/logout`, and `GET /auth/me` endpoints.
- Added auth session models, repositories, schemas, security helpers, and frontend `useAuthSession.js` so login state can be restored from local storage and shown in the top toolbar.
- Added `PROJECT_IMPLEMENTATION_PLAN_v3.md` and `PROJECT_IMPLEMENTATION_PLAN_v3.docx` to lock the new three-end split, platform-admin approval, `ComfyUI` bridge, and enterprise roadmap.
- Added platform-admin enterprise approval flow with `POST /auth/register-enterprise`, `GET /auth/enterprise-applications`, detail lookup, approve, and reject endpoints.
- Added enterprise-application storage models/repositories for both memory and SQL backends so phase-1 approvals can be exercised without waiting for the enterprise re-architecture stage.
- Added the `ComfyUI` phase-one bridge with enterprise material generation jobs, shared workflow templates, built-in prompt/workflow presets, preview overlays, and template persistence across the main dashboard plus enterprise settings.
- Added the enterprise three-role workspace shell with a dedicated enterprise settings dialog, six role-aware tabs, enterprise quick actions, enterprise application follow-up cards, and platform-admin approval follow-up cards.

### Improved
- Improved the top toolbar with a compact identity badge, sign-in panel, demo-account quick fill, and localized auth messages across Chinese, English, and Japanese.
- Improved auth resilience under mixed database setups by falling back to the in-memory auth store when the SQL auth store is unavailable, so the login mainline can still be exercised during this phase.
- Improved the auth role model by normalizing legacy `enterprise` -> `enterprise_admin` and `admin` -> `platform_admin`, while extending `/auth/me` with `account_status`, `organization_id`, and `organization_name`.
- Improved the central auth dialog with enterprise registration entry, richer role labels, account-status feedback, and platform-approval capability display.
- Improved the frontend with a dedicated platform-admin enterprise-approval modal that stays separate from enterprise settings and preserves the existing map/dashboard layout.
- Improved the enterprise registration -> approval -> console onboarding chain with draft persistence, approval-note drafts, recent-review snapshots, status-progress cards, copy helpers, reapply shortcuts, and synchronized prompts across auth, enterprise settings, and platform approval dialogs.
- Improved frontend packaging and runtime loading by splitting heavy dashboard panels into async components and adding stable Vite chunking for Vue, locale bundles, and `ComfyUI` templates so the previous `chunk > 500kB` warning no longer blocks release validation.

### Fixed
- Restricted scoped string-ID capacity migration DDL to MySQL so SQLite startup no longer enters a dialect-specific schema path.
- Made scoped and legacy map-layout reads tolerate duplicate historical rows while still reporting a clear error when no layout exists.
- Expanded frontend API-base detection to the alternate Vite development and preview ports `5174` and `4174`.
- Updated the topology trunk-lane smoke actor and AGV creation path to follow current enterprise scope and point-placement rules.
- Removed a task-completion observation race by returning the AGV to idle before publishing the task's finished state.

### Security
- Masked database passwords in the MySQL configuration diagnostic output.
- Added ignore rules for backend logs and repository-root personal thesis, defense, database, environment, dependency, and build materials.
- Added public-facing Chinese and English README files using only reviewed, non-personal screenshots.

### Verified
- Verified locale parity for `en / zh / ja` against the current phase-three enterprise/onboarding surface with no missing keys remaining.
- Verified the current frontend phase-three baseline with `cmd /c npm run lint` and `cmd /c npm run build` after the latest enterprise follow-up consistency pass.

## v2.0.0 - 2026-03-19

### Added
- Added root-level implementation plan sources `PROJECT_IMPLEMENTATION_PLAN_v2.0.md` and `PROJECT_IMPLEMENTATION_PLAN_v2.0.docx` for the next graduation-project delivery stage.
- Added backend UI settings persistence with `GET /status/ui-settings` and `PUT /status/ui-settings`.
- Added `GET /status/map/profiles` plus read-only map profile metadata so module 4 has a low-risk starting point before true dynamic size editing.
- Added `GET /status/map/resize-precheck` so target map sizes can be dry-checked against active tasks, AGVs, points, templates, and blocked cells before real resizing is enabled.
- Added `POST /status/map/resize` plus guarded frontend save flow so map size can now be updated after a successful precheck.
- Added `POST /status/map/profile/{profile_key}` plus guarded frontend map-profile switching for built-in warehouse schemes.
- Added custom map-profile persistence so current map size and obstacle layout can be saved, deleted, and re-applied as reusable profiles.
- Added map-profile import/export so saved and built-in profile layouts can now be archived as JSON and restored back into the profile list.
- Added a guarded map-profile force-apply path for AGV/obstacle-only overflow cases, including automatic AGV relocation, obstacle trimming, and clearer blocker-to-map highlighting.
- Added profile-linked resize precheck so each map profile can now be dry-checked directly before applying.
- Updated the main map canvas, minimap, task preview, scheduler payloads, and point/template validation to follow the current runtime grid size instead of only the original hardcoded size.
- Added draft-state clamping after map resize so single-task forms, chain-task forms, custom point drafts, and in-progress chain map picks do not remain out of bounds after the size changes.
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
- Added `MINIMUM_DELIVERY_BASELINE_v2.0.md` to record the current answer-defense regression baseline.
- Added `MANUAL_VERIFICATION_RUNBOOK_v2.0.md` and `MANUAL_VERIFICATION_RECORD_v2.0.md` so module 3 has dedicated human-verification execution and record assets.

### Improved
- Improved the map settings panel by grouping map information, obstacle layout actions, and persisted display settings into a clearer MVP structure.
- Improved the map settings panel again by showing current map profile, available profiles, and whether runtime state is ready for future size editing.
- Improved the map settings panel further with a read-only resize precheck area that previews blockers and out-of-bounds counts before any real map-size editing is introduced.
- Improved the map settings panel again by turning built-in map profiles into directly applicable guarded actions instead of metadata-only cards.
- Improved the map settings panel once more with custom profile save/delete actions so module 4 can keep evolving without forcing users back to runtime-only map schemes.
- Improved the map profile cards with direct precheck actions and clearer ready/blocked feedback before switching profiles.
- Improved the map profile workflow again by linking profile precheck targets to the resize-precheck area and restoring a real Japanese locale layer instead of the temporary English fallback.
- Improved blocked profile prechecks once more by surfacing the top blocker reasons directly on each previewed map-profile card.
- Improved map-profile blocker feedback again so repeated clicks retrigger highlights, same-type overflow reasons highlight all affected targets, and force-apply results now show before/after summary details.
- Improved force-apply review flow by adding a downloadable JSON diff for the before/after map-profile summary card.
- Improved obstacle-layout, JSON-template, and task-management related UI wording/layout while keeping the current workflow intact.
- Improved map layout refresh handling so current grid information and active preset information are reflected in the settings panel.
- Improved frontend API base resolution so the app can run both under Vite (`5173 -> 8000`) and under backend-hosted packaged mode (`8000 -> 8000`).
- Improved backend settings loading so packaged runtime can locate `.env`, bundled frontend dist, and a default SQLite database path more reliably.
- Improved packaging verification flow by adding a buildable one-folder package and validating both packaged-dev mode and packaged `backend.exe` startup smoke tests.

### Fixed
- Fixed multilingual gaps for recently added task-management and map-setting labels across Chinese, English, and Japanese locale files.
- Fixed backend/frontend mismatch for map display settings by storing legend layout, opacity, minimap visibility, marker visibility, path arrows, compare mode, and sidebar section state in one shared payload.
- Fixed packaged-mode readiness gaps by allowing FastAPI to serve frontend `dist` directly when enabled.
- Fixed `run_mysql_check.bat` so it respects the real `backend/.env` database configuration instead of forcing the old root/password placeholder.
- Fixed `start_agv.bat` so packaged startup waits for backend readiness before opening the browser.

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

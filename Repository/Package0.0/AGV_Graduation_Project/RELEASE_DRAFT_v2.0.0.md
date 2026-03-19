# v2.0.0 - Minimum Deliverable Stable Release

This release marks the first stable `2.0.0` line of the AGV dispatch graduation project. The system now delivers a minimum shippable version with validated database modes, Windows packaging support, map settings MVP, guarded map resizing, reusable map profiles, and a stronger answer-defense baseline for demos and reviews.

## Highlights

- Promoted the previous `v2.0.0-beta.1` database-integration milestone into a stable `v2.0.0` release.
- Completed the minimum-deliverable packaging flow with Windows one-folder packaging and packaged startup scripts.
- Delivered the map settings MVP with persisted UI settings, map information panels, obstacle-layout tools, and backend-backed storage.
- Added guarded map resizing, built-in/custom map profile workflows, profile precheck, blocker visualization, and safe force-apply handling for AGV/obstacle-only overflow cases.
- Consolidated minimum-delivery docs, verification assets, and answer-defense baseline material for the graduation project.

## Added

- `PROJECT_IMPLEMENTATION_PLAN_v2.0.md`
- `PROJECT_IMPLEMENTATION_PLAN_v2.0.docx`
- `backend/package_entry.py`
- `backend/packaging/backend.spec`
- `backend/requirements-package.txt`
- `build_frontend_dist.bat`
- `run_packaged_dev.bat`
- `build_windows_package.bat`
- `start_agv.bat`
- `PACKAGING_WINDOWS.md`
- `QUICKSTART_MINIMUM_DELIVERY.md`
- `SQLITE_DEMO_GUIDE.md`
- `DEMO_SCRIPT_MINIMUM_DELIVERY.md`
- `TEST_CHECKLIST_MINIMUM_DELIVERY.md`
- `TROUBLESHOOTING_MINIMUM_DELIVERY.md`
- `RELEASE_STRATEGY.md`
- `MINIMUM_DELIVERY_BASELINE_v2.0.md`
- `MANUAL_VERIFICATION_RUNBOOK_v2.0.md`
- `MANUAL_VERIFICATION_RECORD_v2.0.md`
- `GET /status/ui-settings`
- `PUT /status/ui-settings`
- `GET /status/map/profiles`
- `GET /status/map/resize-precheck`
- `POST /status/map/resize`
- `POST /status/map/profile/{profile_key}`
- `GET /status/map/profile/{profile_key}`
- custom map profile persistence, import/export, and force-apply summary diff export

## Improved

- Improved packaged-mode startup so the backend can host frontend `dist` directly and packaged startup waits for readiness before opening the browser.
- Improved map settings into a clearer MVP panel with map information, persisted display settings, obstacle-layout actions, and profile management.
- Improved runtime grid-size support across the main map, minimap, task preview, scheduler payloads, and point/template validation.
- Improved map profile workflows with direct precheck, blocker summaries, blocker-to-map highlighting, import/export, duplicate-name handling, and safer force-apply flows.
- Improved minimum-delivery documentation so demo, troubleshooting, release, and manual verification workflows are easier to execute.

## Fixed

- Fixed `.env` loading and MySQL check flow so real database configuration is respected during validation and startup.
- Fixed packaged startup behavior so the browser opens only after backend readiness.
- Fixed multilingual gaps across recent task-management and map-setting features.
- Fixed repeated blocker highlighting and same-type overflow feedback so affected cells can be reviewed more clearly.
- Fixed map resize flow issues around runtime grid-size validation, draft-state clamping, and guarded force-apply handling.

## Validation

- Frontend `npm run lint` passed.
- Frontend `npm run build` passed.
- Backend Python compile checks passed.
- SQLite smoke check passed.
- MySQL configuration check passed.
- Packaged dev smoke passed.
- Windows one-folder packaging build passed.
- Packaged `backend.exe` smoke passed.

## Notes

- `v2.0.0-beta.1` remains the historical beta milestone for the first database-backed release line.
- `v2.0.0` is the first stable release intended for minimum-deliverable graduation-project demos.
- SQLite remains the recommended default mode for packaged demos, while MySQL remains available for more formal deployment validation.

## Suggested GitHub Release Fields

- **Tag**: `v2.0.0`
- **Target**: `main`
- **Release title**: `v2.0.0 - Minimum Deliverable Stable Release`

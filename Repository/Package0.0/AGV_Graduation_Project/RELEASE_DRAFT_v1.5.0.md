# v1.5.0 - A3 Backend Layering and Scheduling Consistency Update

This release focuses on stabilizing the current AGV scheduling workflow while laying the groundwork for the next A3 milestone. The backend now has a clearer layered structure for future MySQL integration, and the scheduling chain is more explicit and reliable across frontend and backend boundaries.

## Highlights

- Built the A3 backend layering foundation with repository facades, `memory/` and `sql/` store entry points, startup lifecycle initialization, and database environment templates.
- Added SQL ORM preparation, including expanded SQL models and mapper helpers for AGV, task, task-stage, and fault-event conversion.
- Reduced frontend coupling by extracting task display and task preview logic out of `App.vue`.
- Made scheduling mode explicit across the create -> schedule chain so automatic map-created tasks remain automatic after dispatch.
- Added direct path-algorithm switching from the right-side dispatch control panel.

## Added

- A3 interface freeze baseline and related backend structure
- `backend/.env.example`
- `backend/app/core/lifecycle.py`
- repository facade split with `memory` and `sql` store directories
- SQL mapper helpers for future persistence migration
- `frontend/agv-frontend/src/composables/useTaskDisplayState.js`
- `frontend/agv-frontend/src/composables/useTaskPreview.js`
- `GITHUB_WORKFLOW.md`

## Improved

- Backend services now rely more consistently on repository helpers instead of scattered direct list access.
- Startup flow is cleaner and easier to extend for future database-backed deployment.
- Auto/manual scheduling behavior is more explicit and easier to reason about.
- Right-side dispatch control interaction is more direct and compact.

## Fixed

- Fixed automatic map-created tasks being treated as manual tasks after scheduling.
- Fixed maintenance/offline AGV occupancy inconsistencies between frontend visibility and backend movement blocking.
- Fixed several task-marker and preview synchronization issues during display-layer cleanup.

## Validation

- Frontend lint passed.
- Backend Python compile checks passed for key modules.
- Existing AGV scheduling flow remains compatible with current endpoints.

## Notes

- This release still uses the in-memory runtime by default.
- SQL repository files are prepared as the next step toward real MySQL persistence.
- No desktop release asset is attached in this version.

## Suggested GitHub Release Fields

- **Tag**: `v1.5.0`
- **Target**: `main`
- **Release title**: `v1.5.0 - A3 Backend Layering and Scheduling Consistency Update`

# v1.5.0 Release Draft

## Release Title

`v1.5.0 - A3 Backend Layering and Scheduling Consistency Update`

## Summary

This release focuses on two main directions:

- advancing the A3 backend layering work without breaking the current demo workflow
- improving scheduling consistency between frontend display state and backend dispatch mode

The project now has a clearer repository structure for future MySQL integration, while preserving the current in-memory runtime behavior.

## Highlights

- Added A3 backend layering groundwork:
  - repository facades
  - `memory/` and `sql/` repository entry points
  - lifecycle-based startup initialization
  - database environment templates and database notes
- Added SQL ORM preparation:
  - expanded SQL models
  - mapper helpers for AGV, task, task-stage, and fault-event conversion
- Improved frontend structure:
  - extracted task display state logic
  - extracted task preview logic
  - kept `App.vue` behavior compatible while reducing coupling
- Improved scheduling correctness:
  - explicit `schedule_mode` is now passed through the scheduling chain
  - automatic map-created tasks no longer fall into manual mode after scheduling
- Improved control panel usability:
  - path algorithm can now be toggled directly from the right-side dispatch control area

## Added

- A3 interface freeze baseline and supporting backend structure
- `backend/.env.example`
- `backend/app/core/lifecycle.py`
- repository facade split with `memory` and `sql` store directories
- SQL mapper helpers for future persistence migration
- `useTaskDisplayState.js`
- `useTaskPreview.js`
- `GITHUB_WORKFLOW.md`

## Improved

- backend service code now relies more consistently on repository helpers
- startup structure is cleaner and easier to extend for database-backed deployments
- auto/manual scheduling flow is more explicit and easier to reason about
- right-side dispatch control interaction is more direct

## Fixed

- fixed automatic map-created tasks being treated as manual tasks after scheduling
- fixed maintenance/offline AGV occupancy inconsistencies between frontend visibility and backend movement blocking
- fixed several task marker and preview synchronization issues during display-layer cleanup

## Validation

The following checks were completed during this release preparation:

- frontend lint passed
- backend Python compile checks passed for key modules
- current AGV scheduling workflow kept compatible with existing endpoints

## Notes

- This release is still based on the current in-memory runtime by default
- SQL repository files are prepared as the next step toward real MySQL persistence
- No desktop release asset is attached yet in this version

## Suggested GitHub Release Fields

- **Tag**: `v1.5.0`
- **Release title**: `v1.5.0 - A3 Backend Layering and Scheduling Consistency Update`
- **Target**: `main`


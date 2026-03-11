# Changelog

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

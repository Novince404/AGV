# Database Notes

This project currently supports three backend data modes:

- `memory`
- `sqlite`
- `mysql`

The default daily-development path is still `memory`, while `sqlite` and `mysql` are now available for persistence validation during A3.

## Current Status

The backend already has:

- unified database settings in `backend/app/core/settings.py`
- unified engine/session management in `backend/app/core/database.py`
- startup initialization in `backend/app/core/lifecycle.py`
- repository facades for AGV, task, fault, map, point, and template data
- separate `memory/` and `sql/` store implementations

The SQL-side ORM models already cover:

- AGV
- Task
- TaskStage
- FaultEvent
- MapLayout
- MapBlockedCell
- PointLibrary
- TaskTemplate
- TaskTemplateStage

## Recommended Modes

### 1. Memory mode

Use this when you want the safest day-to-day demo flow:

- no external database dependency
- fastest startup
- easiest way to validate scheduling features

Example:

```env
AGV_DATA_BACKEND=memory
```

### 2. SQLite mode

Use this for local persistence validation:

- no separate database service required
- data stored in a local `.db` file
- useful for smoke checks and single-machine persistence verification

Example:

```env
AGV_DATA_BACKEND=sqlite
AGV_DATABASE_URL=sqlite:///./agv_dispatch.db
AGV_DATABASE_AUTO_CREATE=true
```

Convenience scripts:

- `run_sqlite_dev.bat`
- `run_sqlite_smoke.bat`

Expected smoke result:

```text
SQLITE_SMOKE_OK point/template/map
```

### 3. MySQL mode

Use this when validating real database connectivity:

- suitable for multi-session persistence preparation
- closer to the planned later-stage deployment model

Example:

```env
AGV_DATA_BACKEND=mysql
AGV_DATABASE_URL=mysql+pymysql://agv_user:your_password@127.0.0.1:3306/agv_dispatch?charset=utf8mb4
AGV_DATABASE_AUTO_CREATE=true
AGV_DATABASE_ECHO=false
```

Convenience scripts:

- `run_mysql_check.bat`
- `run_mysql_dev.bat`

Expected config-check result:

```text
MYSQL_CONFIG_OK
```

## Point and Template Persistence

The frontend now prefers backend APIs for:

- point library
- task templates

If backend APIs are available, the frontend will:

- load `/point/list` and `/template/list`
- save custom points/templates to backend first
- keep local fallback behavior if backend is unavailable
- migrate legacy localStorage custom points/templates to backend when possible

## Practical Recommendation

For current development:

1. use `memory` for the safest daily feature work
2. use `sqlite` for local persistence smoke checks
3. use `mysql` when validating the full A3 persistence direction

This keeps the project stable while gradually moving from prototype-style runtime storage to real database-backed persistence.

# v3.0.0-beta.2 — Enterprise-trial engineering baseline

`v3.0.0-beta.2` is the next public prerelease of the AGV graduation project.
It turns the beta.1 product preview into a reviewable enterprise-trial
engineering baseline: versioned APIs, migrations, secure sessions, a durable
scheduler boundary, Docker/Windows delivery paths, and automated checks.

> This is a simulation and trial release. It is not an industrial control
> system, a functional-safety product, or a deployment for real vehicles.

## Highlights

- Direct repository entry points and one canonical `VERSION` file.
- `/api/v1`, health/readiness/version/metrics endpoints, structured errors,
  request IDs, SSE events, compatibility headers for legacy endpoints.
- Alembic migrations plus `agv database check|backup|upgrade|verify|restore`.
- Argon2id passwords, per-user salts, opaque HttpOnly sessions, CSRF, login
  throttling, recovery-admin bootstrap, mandatory first-login password changes,
  and OIDC/Keycloak approval flow.
- Deterministic scheduler time steps, durable command/event records, database
  leadership lease, idempotency keys, and `SimulationDeviceAdapter`.
- Router/Pinia/TypeScript frontend foundation with a cookie-aware API client,
  role-aware navigation, and a secure password-change journey.
- Docker Compose trial stack (MySQL, API, scheduler, optional Keycloak) and
  Windows launch/package scripts that run API and scheduler as separate roles.
- CI covering backend lint/tests, SQLite and MySQL migrations, frontend type
  checks/tests/build, dependency audit, and secret scan.

## Validation performed

- Python compilation, Ruff, 17 pytest tests, and SQLite repository smoke
  validation.
- Frontend `typecheck`, ESLint, Vitest, Vite production build, and enterprise
  avoidance demo smoke validation.
- Dependency lock resolution, `pip check`, `pip-audit`, migration maintenance
  command validation, Markdown-link review, and a sensitive-information scan.

## Known limitations

- Only the simulation device adapter is included. Real AGV, PLC, MQTT, serial,
  sensor, and emergency-stop integrations are deliberately out of scope.
- The beta.1 baseline migration must be made a fully static schema snapshot
  before a stable `v3.0.0` release. Back up and verify existing SQLite/MySQL
  data before any upgrade.
- Legacy backend modules still have typing debt, so a full mypy gate is not yet
  enabled; runtime/API tests and Ruff are the current enforced backend checks.
- No prebuilt Windows executable is attached to this source prerelease. Build
  it following [the Windows packaging guide](PACKAGING_WINDOWS.md).

## Compatibility and use boundary

- `v2.0.0` remains the historical stable graduation-project baseline.
- Legacy API paths remain available for the v3 compatibility window and emit
  deprecation headers; their removal is reserved for v4.0.0.
- The source is available under the [PolyForm Noncommercial License 1.0.0](../../LICENSE):
  learning, research, testing, modification, and sharing are permitted only on
  a noncommercial basis under its full terms. Commercial use needs prior
  written permission.

## Suggested GitHub release fields

- **Tag:** `v3.0.0-beta.2`
- **Title:** `v3.0.0-beta.2 — Enterprise-trial engineering baseline`
- **Release type:** prerelease
- **Target:** the merge commit on `main`

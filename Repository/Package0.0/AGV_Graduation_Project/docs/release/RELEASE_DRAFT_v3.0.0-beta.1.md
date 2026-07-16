# v3.0.0-beta.1 - Productization and Enterprise Architecture Preview

`v3.0.0-beta.1` is the first public prerelease of the AGV project's 3.x productization line. It preserves `v2.0.0` as the minimum-deliverable stable graduation-project baseline while previewing the expanded identity, enterprise, topology, autonomy, and packaging architecture.

> This is a Beta release for learning, research, demonstrations, and continued integration. It is not certified for production warehouses or safety-critical equipment.

## Highlights

- Identity and platform governance now cover personal registration, enterprise applications, role-aware sessions, account lifecycle actions, and governance audit summaries.
- Enterprise users receive role-specific workspaces, member management, tenant-scoped data, internal feedback, and platform bug-reporting flows.
- Enterprise maps now support explicit route topology, continuous edge-based movement, conflict handling, dynamic avoidance, and runtime routing cues.
- Battery autonomy, charging thresholds, station capacity, and automatic charge/release behavior extend the simulation beyond fixed task playback.
- The standalone enterprise client, Windows packaging flow, ComfyUI material-generation bridge, and public bilingual documentation make the project easier to demonstrate and study.

## Added

- Personal account registration and platform account governance.
- Enterprise registration, approval, reapplication, member management, and role-specific workspaces.
- Tenant-scoped repositories and account-aware runtime isolation.
- Enterprise topology nodes, edges, stations, parking/charging nodes, editing, import, and pure-topology view.
- Continuous AGV motion, topology corridor claims, conflict handling, and trunk-lane routing.
- Personal-grid and enterprise-topology dynamic avoidance with yield, replan, and demo guidance.
- Battery drain, charging thresholds, station capacity, autonomy settings, and automatic charging behavior.
- Enterprise internal requests and platform bug-feedback workflows.
- Enterprise standalone client delivery and governance-first demo packaging.
- ComfyUI material-generation jobs, workflow templates, presets, previews, and persisted template settings.
- Repository-root Chinese and English README files, reviewed screenshots, publication ignore rules, and the PolyForm Noncommercial License 1.0.0.

## Improved

- Role-aware navigation, enterprise settings, approval follow-up, registration drafts, and governance layouts.
- Irregular enterprise map editing, profile import, topology placement, runtime overlays, and route feedback.
- Frontend chunking and async dashboard loading for a clean production build.
- Enterprise packaged runtime startup, scoped data reuse, launcher behavior, and task-path validation.
- Chinese, English, and Japanese locale coverage across the expanded productization surface.

## Fixed and secured

- Hardened account switching and tenant scope propagation across map data, movement threads, SQL identifiers, and imported tasks.
- Stabilized topology deadlock resolution, mid-corridor access, rerouting, route weights, station capacity, and continuous-motion edge cases.
- Fixed battery reset, packaged-enterprise paths, feedback visibility, enterprise login, and task startup regressions.
- Limited MySQL-only schema migration paths, tolerated duplicate historical map rows, and masked database passwords in diagnostics.
- Excluded local credentials, databases, logs, dependencies, build output, and personal academic materials from public Git history.

## Validation

- Python backend compilation.
- Full SQLite smoke suite, including persistence, data scope, special-node capacity, battery runtime, autonomy motion, task lifecycle, topology trunk lanes, and conflict rules.
- Frontend ESLint validation.
- Vite production build.
- Enterprise avoidance demo smoke test.
- README link and release-version consistency checks.
- Reviewed license text and publication boundary checks.

## Version and compatibility notes

- `v2.0.0` remains the stable minimum-deliverable baseline.
- `v3.0.0-beta.1` is intentionally a major-version Beta because the login, role, enterprise tenancy, topology, and runtime architecture represent a product-stage change.
- Existing memory, SQLite, and MySQL modes remain part of the project, but databases should be backed up before testing the new Beta line.
- Seeded demo accounts and default settings are for local demonstrations only.
- ComfyUI remains optional and does not participate in core dispatch decisions.
- No prebuilt binary is required for this source prerelease; Windows packages can be rebuilt using the repository packaging documentation.

## License

The source is available under the [PolyForm Noncommercial License 1.0.0](../../../../../LICENSE). Noncommercial learning, research, experimentation, testing, modification, and sharing are permitted under its terms. Commercial use requires prior written permission from the author.

## Suggested GitHub Release fields

- **Tag**: `v3.0.0-beta.1`
- **Target**: the final release commit on `main`
- **Title**: `v3.0.0-beta.1 - Productization and Enterprise Architecture Preview`
- **Release type**: Prerelease
- **Previous stable release**: `v2.0.0`

# Docker trial deployment

This deployment is for a bounded enterprise trial or reproducible acceptance
environment. It serves the compiled UI and API from one origin, runs the
deterministic scheduler as a separate process, and uses MySQL for persistence.
It is not a production high-availability or industrial-control deployment.

The image always contains the repository-root `VERSION` file. Set the
`AGV_VERSION` build argument from that same file so image metadata agrees with
the running `/version` endpoint.

## Before starting

- Install a current Docker Desktop / Docker Compose installation.
- Use a private, backed-up Docker host for the MySQL volume.
- Do not expose MySQL directly; the provided Compose file keeps it on an
  internal network.
- Place an HTTPS reverse proxy in front of the API before making it reachable
  outside a local trial network. Set `AGV_AUTH_COOKIE_SECURE=true`, use an
  exact `AGV_CORS_ALLOW_ORIGINS` value, and set `AGV_FRONTEND_BASE_URL` to the
  public HTTPS URL.

## First deployment

From the repository root, create a private environment file and generate
unique values for every `CHANGE_ME` entry:

```powershell
Copy-Item deploy\compose.env.example deploy\compose.env
```

All Compose commands below use `tools\docker\run-compose.ps1`. It reads the
canonical root `VERSION` on every invocation and passes it as the image build
argument, so `deploy/compose.env` never becomes a second version source.

For an empty new database, set `AGV_MYSQL_BACKUP_CONFIRMED=yes` in
`deploy/compose.env`. For an existing database, set it only after completing a
verified backup; the migration service intentionally refuses to start without
that acknowledgement.

Build and start the trial stack:

```powershell
.\tools\docker\run-compose.ps1 build
.\tools\docker\run-compose.ps1 up -d
.\tools\docker\run-compose.ps1 ps
```

Open `http://localhost:8000`, then verify health and version:

```powershell
Invoke-RestMethod http://localhost:8000/health/ready
Invoke-RestMethod http://localhost:8000/version
```

The `migrate` service is a one-shot container. `api` and `scheduler` wait for
it to complete successfully. The API never owns the v3 scheduler loop;
`scheduler` is the only service with `AGV_SCHEDULER_V3_ENABLED=true`.

## Optional Keycloak acceptance profile

The repository includes a local realm import with no users. It exists to
exercise standard Authorization Code + PKCE and the system's local approval
flow; it is not a shared identity provider configuration.

1. Set `AGV_OIDC_ENABLED=true` and provide a long random
   `AGV_OIDC_STATE_SECRET` in `deploy/compose.env`.
2. Set a unique `AGV_KEYCLOAK_ADMIN_PASSWORD`.
3. Start the optional profile:

   ```powershell
   .\tools\docker\run-compose.ps1 --profile oidc up -d
   ```

4. Visit `http://localhost:8080`, create an ordinary Keycloak user in realm
   `agv`, and assign the optional `agv-user` role if desired.
5. Sign in through `/api/v1/auth/oidc/login`. The first login creates a
   pending local-link request; a local platform administrator must approve it
   and choose the local user, organization, and role before access is granted.

`agv-keycloak.localhost` is used so browsers resolve it to the local host while
the API container reaches it through Docker's host gateway. This is intended
for Docker Desktop acceptance testing. For a server deployment, configure a
real HTTPS issuer hostname, its discovery URL, and redirect URI instead. The
included client is public and relies on PKCE, so it intentionally has no
client secret. If an external provider requires a confidential client, supply
its secret only through the deployment environment and never commit it.

## Operations and recovery

Useful commands:

```powershell
.\tools\docker\run-compose.ps1 logs -f api scheduler
.\tools\docker\run-compose.ps1 exec api python agv.py database check
.\tools\docker\run-compose.ps1 exec api python agv.py database verify
.\tools\docker\run-compose.ps1 down
```

`docker compose down` retains named volumes. Do **not** use `down -v` for an
existing trial database unless the MySQL and Keycloak data are intentionally
being discarded. For a database upgrade, follow
[Database migrations](DATABASE_MIGRATIONS.md) first.

## Image-only build

The same root Dockerfile can be built without Compose:

```powershell
$env:AGV_VERSION = (Get-Content VERSION -Raw).Trim()
docker build --build-arg AGV_VERSION=$env:AGV_VERSION -t agv-trial:$env:AGV_VERSION .
```

Run this image only with an explicit trial configuration and a reachable MySQL
database. It intentionally does not embed a database password, administrator
password, OIDC state secret, or external provider credential.

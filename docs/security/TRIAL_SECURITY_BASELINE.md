# Enterprise trial security baseline

This checklist complements the repository [security policy](../../SECURITY.md).
It describes the minimum configuration for a bounded v3 enterprise trial; it
does not certify the system for real AGV or safety-critical operation.

## Required before external access

- Use MySQL with a tested backup/restore process. Do not use memory mode for a
  trial deployment.
- Set `AGV_APP_ENV=trial` or `production`, keep
  `AGV_AUTH_DEMO_USERS_ENABLED=false`, and create one unique local recovery
  administrator with a password of at least 12 characters.
- Use HTTPS at the reverse proxy, set `AGV_AUTH_COOKIE_SECURE=true`, and set
  `AGV_CSRF_ENABLED=true`.
- Replace permissive development CORS values with exact allowed origins. Do
  not use a wildcard origin with credentialed cookies.
- Keep database credentials, bootstrap passwords, OIDC state secrets, backup
  archives, logs, and local `.env` files outside Git. The supplied environment
  examples contain only placeholders or local fixtures.
- Review `/health/ready`, `/version`, migration verification, and backup
  evidence before opening access to trial users.

## Identity and authorization

- Local passwords use Argon2id; legacy password hashes are upgraded after a
  successful local login.
- Browser sessions are opaque HttpOnly cookies. Only their hashes are stored;
  do not reintroduce persistent browser session tokens in `localStorage`.
- Login failures are rate-limited and recorded without plaintext passwords.
- OIDC uses Authorization Code + PKCE. An unknown `(issuer, subject)` creates
  only a pending link request. Local platform/enterprise approval determines
  user, tenant, and role.
- Retain a local recovery administrator so an unavailable OIDC provider does
  not remove all administrative access.

## Operational boundaries

- The only v3 device adapter is simulation. Never connect this trial stack to
  a real AGV, PLC, serial device, MQTT broker, or emergency-stop chain.
- The scheduler lease prevents concurrent simulation leaders in one database;
  it is not a substitute for database high availability or disaster recovery.
- Review audit records after role changes, OIDC link decisions, exports, and
  dangerous commands. Do not silently delete supporting evidence during a
  trial investigation.

Report vulnerabilities privately as described in [SECURITY.md](../../SECURITY.md).

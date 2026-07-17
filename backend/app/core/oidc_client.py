from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import Request

from app.core.settings import get_settings
from app.utils.api_error import raise_api_error


oauth = OAuth()
_registration_key: tuple[str, str] | None = None


def oidc_configuration_status() -> dict:
    settings = get_settings()
    missing = []
    if not settings.oidc_issuer_url:
        missing.append("AGV_OIDC_ISSUER_URL")
    if not settings.oidc_client_id:
        missing.append("AGV_OIDC_CLIENT_ID")
    if not settings.oidc_state_secret:
        missing.append("AGV_OIDC_STATE_SECRET")
    return {
        "enabled": settings.oidc_enabled,
        "configured": settings.oidc_enabled and not missing,
        "issuer": settings.oidc_issuer_url,
        "missing": missing,
    }


def get_oidc_client():
    global _registration_key
    settings = get_settings()
    status = oidc_configuration_status()
    if not status["enabled"]:
        raise_api_error(503, "oidc_disabled")
    if not status["configured"]:
        raise_api_error(503, "oidc_not_configured", missing=status["missing"])
    key = (str(settings.oidc_issuer_url), str(settings.oidc_client_id))
    if _registration_key != key:
        oauth.register(
            name="agv_oidc",
            server_metadata_url=f"{settings.oidc_issuer_url}/.well-known/openid-configuration",
            client_id=settings.oidc_client_id,
            # A confidential client can provide a secret, while the bundled
            # Keycloak example deliberately uses a public Authorization Code
            # + PKCE client so the public repository never carries a secret.
            client_secret=settings.oidc_client_secret or None,
            client_kwargs={
                "scope": "openid profile email",
                "code_challenge_method": "S256",
            },
            overwrite=True,
        )
        _registration_key = key
    return oauth.create_client("agv_oidc")


async def begin_oidc_login(request: Request):
    client = get_oidc_client()
    redirect_uri = str(request.url_for("oidc_callback"))
    return await client.authorize_redirect(request, redirect_uri)


async def exchange_oidc_callback(request: Request) -> dict:
    client = get_oidc_client()
    token = await client.authorize_access_token(request)
    claims = token.get("userinfo")
    if not claims and token.get("id_token"):
        claims = await client.parse_id_token(request, token)
    if not claims or not claims.get("sub"):
        raise_api_error(401, "oidc_claims_invalid")
    settings = get_settings()
    return {
        "issuer": str(claims.get("iss") or settings.oidc_issuer_url),
        "subject": str(claims["sub"]),
        "email": str(claims.get("email") or "") or None,
        "email_verified": bool(claims.get("email_verified", False)),
        "display_name": str(claims.get("name") or claims.get("preferred_username") or "") or None,
    }

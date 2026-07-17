from __future__ import annotations

from app.services import oidc_service


def test_unknown_oidc_identity_requires_approval_then_can_login(admin_client):
    claims = {
        "issuer": "https://identity.example.test/realms/agv",
        "subject": "external-user-1",
        "email": "operator@example.test",
        "display_name": "External Operator",
    }
    pending = oidc_service.complete_external_login(claims)
    assert pending["status"] == "pending"
    request_id = pending["request"]["id"]

    approval = admin_client.post(
        f"/api/v1/auth/oidc/link-requests/{request_id}/approve",
        json={"user_id": "enterprise_operator_demo"},
    )
    assert approval.status_code == 200, approval.text
    assert approval.json()["item"]["status"] == "approved"

    authenticated = oidc_service.complete_external_login(claims)
    assert authenticated["status"] == "authenticated"
    assert authenticated["auth"]["user"]["id"] == "enterprise_operator_demo"

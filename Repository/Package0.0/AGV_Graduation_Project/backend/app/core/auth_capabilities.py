from __future__ import annotations


LEGACY_ROLE_ALIASES: dict[str, str] = {
    "enterprise": "enterprise_admin",
    "admin": "platform_admin",
}


ROLE_CAPABILITIES: dict[str, set[str]] = {
    "guest": {"dashboard.view"},
    "personal": {
        "dashboard.view",
        "dispatch.write",
        "fault.write",
        "map.write",
        "map.force_apply",
        "template.write",
        "point.write",
        "json.write",
        "experiment.write",
        "audit.view",
    },
    "enterprise_operator": {
        "dashboard.view",
        "dispatch.write",
        "fault.write",
        "ai.render",
    },
    "enterprise_logistics": {
        "dashboard.view",
        "map.write",
        "template.write",
        "point.write",
        "json.write",
        "experiment.write",
        "ai.render",
    },
    "enterprise_admin": {
        "dashboard.view",
        "dispatch.write",
        "fault.write",
        "map.write",
        "map.force_apply",
        "template.write",
        "point.write",
        "json.write",
        "experiment.write",
        "audit.view",
        "ai.render",
    },
    "platform_admin": {
        "dashboard.view",
        "dispatch.write",
        "fault.write",
        "map.write",
        "map.force_apply",
        "template.write",
        "point.write",
        "json.write",
        "experiment.write",
        "audit.view",
        "enterprise.approve",
        "system.manage",
        "ai.render",
    },
}


CAPABILITY_GROUPS: dict[str, list[str]] = {
    "dispatch": ["dispatch.write"],
    "fault": ["fault.write"],
    "map": ["map.write"],
    "data": ["template.write", "point.write", "json.write", "experiment.write"],
    "audit": ["audit.view"],
    "ai": ["ai.render"],
    "platform": ["enterprise.approve"],
}


def normalize_role(role: str | None) -> str:
    normalized = str(role or "guest").strip().lower()
    if not normalized:
        return "guest"
    return LEGACY_ROLE_ALIASES.get(normalized, normalized)


def normalize_account_status(account_status: str | None) -> str:
    normalized = str(account_status or "").strip().lower()
    return normalized or "approved"


def get_role_capabilities(role: str | None, account_status: str | None = "approved") -> set[str]:
    normalized_role = normalize_role(role)
    normalized_status = normalize_account_status(account_status)
    capabilities = set(ROLE_CAPABILITIES.get(normalized_role, ROLE_CAPABILITIES["guest"]))
    if normalized_role.startswith("enterprise_") and normalized_status != "approved":
        return {"dashboard.view"}
    return capabilities


def build_capability_groups(role: str | None, account_status: str | None = "approved") -> dict[str, bool]:
    capabilities = get_role_capabilities(role, account_status=account_status)
    return {
        group: all(capability in capabilities for capability in required_capabilities)
        for group, required_capabilities in CAPABILITY_GROUPS.items()
    }


def has_capability(role: str | None, capability: str, account_status: str | None = "approved") -> bool:
    return str(capability or "") in get_role_capabilities(role, account_status=account_status)

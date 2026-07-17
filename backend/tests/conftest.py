from __future__ import annotations

import copy
import os

import pytest
from fastapi.testclient import TestClient


os.environ["AGV_APP_ENV"] = "test"
os.environ["AGV_DATA_BACKEND"] = "memory"
os.environ["AGV_AUTH_DEMO_USERS_ENABLED"] = "true"
os.environ["AGV_SCHEDULER_V3_ENABLED"] = "false"
os.environ["AGV_CSRF_ENABLED"] = "false"

from app.core.auth_rate_limit import login_rate_limiter
from app.core.settings import get_settings
from app.factory import create_app
from app.repositories import runtime_repository
from app.repositories.memory import auth_store
from app.repositories.oidc_repository import reset_memory_oidc


_BASE_USERS = copy.deepcopy(auth_store.users)


@pytest.fixture(autouse=True)
def reset_memory_state():
    get_settings.cache_clear()
    auth_store.users[:] = copy.deepcopy(_BASE_USERS)
    auth_store.sessions.clear()
    login_rate_limiter.reset()
    runtime_repository.reset_memory_runtime()
    reset_memory_oidc()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def operator_client(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "enterprise_operator_demo", "password": "operator123"},
    )
    assert response.status_code == 200
    return client


@pytest.fixture
def admin_client(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "platform_admin_demo", "password": "platform123"},
    )
    assert response.status_code == 200
    return client

from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.auth_repository import AuthRepository


def auth_headers_for_permissions(client: TestClient, permission_codes: list[str] | tuple[str, ...]) -> dict[str, str]:
    username = f"test.{uuid4().hex[:16]}"
    password = "test-password"
    register_response = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "display_name": "API Test User"},
    )
    if register_response.status_code != 200:
        raise AssertionError(f"Failed to register auth test user: {register_response.status_code} {register_response.text}")

    user = AuthRepository.get_user_by_username(username)
    if user is None:
        raise AssertionError("Auth test user was not created")

    for permission_code in permission_codes:
        AuthRepository.upsert_user_permission_override(
            user_id=user["id"],
            permission_code=permission_code,
            effect="allow",
            reason="api test permission",
        )

    login_response = client.post("/api/auth/login", json={"username": username, "password": password})
    if login_response.status_code != 200:
        raise AssertionError(f"Failed to login auth test user: {login_response.status_code} {login_response.text}")

    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.database import SessionLocal
from app.models.role import Role
from app.services.api_keys import create_api_key
from app.services.users import get_user_by_username_or_email


def unique(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def register(client: TestClient, username: str, email: str, password: str = "super-secret-password"):
    return client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "display_name": "Test User",
        },
    )


def login(client: TestClient, username: str, password: str = "super-secret-password") -> dict[str, str]:
    response = client.post(
        "/auth/login",
        json={"username_or_email": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def auth_headers(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def create_service_key() -> str:
    with SessionLocal() as db:
        _, secret = create_api_key(db, f"test-service-{uuid4().hex[:8]}")
        return secret


def grant_admin(username: str) -> None:
    with SessionLocal() as db:
        user = get_user_by_username_or_email(db, username)
        admin_role = db.scalar(select(Role).where(Role.name == "Administrator"))
        assert user is not None
        assert admin_role is not None
        user.roles = [admin_role]
        db.add(user)
        db.commit()


def test_register_duplicate_login_invalid_login_refresh_logout_and_me():
    username = unique("user")
    email = f"{username}@example.com"

    with TestClient(app) as client:
        response = register(client, username, email)
        assert response.status_code == 201

        duplicate_response = register(client, username, email)
        assert duplicate_response.status_code == 409

        invalid_login = client.post(
            "/auth/login",
            json={"username_or_email": username, "password": "wrong-password"},
        )
        assert invalid_login.status_code == 401

        tokens = login(client, username)
        me_response = client.get("/auth/me", headers=auth_headers(tokens))
        assert me_response.status_code == 200
        assert me_response.json()["email"] == email

        sessions_response = client.get("/auth/sessions", headers=auth_headers(tokens))
        assert sessions_response.status_code == 200
        assert len(sessions_response.json()) >= 1

        refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert refresh_response.status_code == 200
        rotated_tokens = refresh_response.json()
        assert rotated_tokens["refresh_token"] != tokens["refresh_token"]

        old_refresh_response = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert old_refresh_response.status_code == 401

        logout_response = client.post(
            "/auth/logout",
            json={"refresh_token": rotated_tokens["refresh_token"]},
        )
        assert logout_response.status_code == 200

        logged_out_refresh = client.post(
            "/auth/refresh",
            json={"refresh_token": rotated_tokens["refresh_token"]},
        )
        assert logged_out_refresh.status_code == 401


def test_permissions_discord_link_and_service_key_lookup():
    username = unique("discord")
    email = f"{username}@example.com"
    discord_user_id = str(int(uuid4().hex[:12], 16))

    with TestClient(app) as client:
        assert register(client, username, email).status_code == 201
        tokens = login(client, username)

        permissions_response = client.get("/permissions/me", headers=auth_headers(tokens))
        assert permissions_response.status_code == 200
        assert "User" in permissions_response.json()["roles"]
        assert "auth.me" in permissions_response.json()["permissions"]

        start_response = client.get(
            "/auth/discord/start",
            params={
                "discord_id": discord_user_id,
                "discord_username": "orven_user",
                "discord_avatar": "https://cdn.example.com/avatar.png",
            },
        )
        assert start_response.status_code == 200
        link_token = start_response.json()["link_token"]

        callback_response = client.get("/auth/discord/callback", params={"token": link_token})
        assert callback_response.status_code == 200
        assert callback_response.json()["discord_user_id"] == discord_user_id

        discord_response = client.put(
            "/discord/me",
            headers=auth_headers(tokens),
            json={"link_token": link_token},
        )
        assert discord_response.status_code == 200

        unauthenticated_lookup = client.get(f"/discord/users/{discord_user_id}")
        assert unauthenticated_lookup.status_code == 401

        service_key = create_service_key()
        lookup_response = client.get(
            f"/discord/users/{discord_user_id}",
            headers={"X-OrvenCore-Service-Key": service_key},
        )
        assert lookup_response.status_code == 200
        assert lookup_response.json()["username"] == username


def test_admin_permission_denial_and_success():
    normal_username = unique("normal")
    admin_username = unique("admin")

    with TestClient(app) as client:
        assert register(client, normal_username, f"{normal_username}@example.com").status_code == 201
        assert register(client, admin_username, f"{admin_username}@example.com").status_code == 201

        normal_tokens = login(client, normal_username)
        denied_response = client.get("/admin/users", headers=auth_headers(normal_tokens))
        assert denied_response.status_code == 403

        grant_admin(admin_username)
        admin_tokens = login(client, admin_username)

        users_response = client.get("/admin/users", headers=auth_headers(admin_tokens))
        assert users_response.status_code == 200
        assert any(user["username"] == normal_username for user in users_response.json())

        key_response = client.post(
            "/admin/api-keys",
            headers=auth_headers(admin_tokens),
            json={"name": "Discord Bot Test Key"},
        )
        assert key_response.status_code == 201
        assert key_response.json()["key"].startswith("ocsvc_")

        keys_response = client.get("/admin/api-keys", headers=auth_headers(admin_tokens))
        assert keys_response.status_code == 200

        logout_all_response = client.post("/auth/logout-all", headers=auth_headers(admin_tokens))
        assert logout_all_response.status_code == 200


def test_frontend_and_bot_health_alias_are_served():
    with TestClient(app) as client:
        frontend_response = client.get("/?source=discord&discord_link_token=test-token")
        assert frontend_response.status_code == 200
        assert "OrvenCore Identity" in frontend_response.text
        assert "discord-form" in frontend_response.text

        health_response = client.get("/api/health")
        assert health_response.status_code == 200
        assert health_response.json() == {"status": "ok"}

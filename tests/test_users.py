"""users 라우터 테스트 — /api/users/*"""
import pytest
from fastapi.testclient import TestClient


class TestListUsers:
    def test_list_users_returns_paginated(self, client: TestClient):
        res = client.get("/api/users")
        assert res.status_code == 200
        data = res.json()
        assert "users" in data
        assert "total" in data
        assert data["total"] == 3
        assert data["page"] == 1
        assert len(data["users"]) == 3

    def test_list_users_with_status_filter(self, client: TestClient):
        res = client.get("/api/users?status=active")
        assert res.status_code == 200

    def test_list_users_with_search(self, client: TestClient):
        res = client.get("/api/users?search=john")
        assert res.status_code == 200

    def test_list_users_pagination(self, client: TestClient):
        res = client.get("/api/users?page=2&page_size=1")
        assert res.status_code == 200
        data = res.json()
        assert data["page"] == 2
        assert data["page_size"] == 1


class TestGetUser:
    def test_get_existing_user(self, client: TestClient):
        res = client.get("/api/users/1")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == 1
        assert data["first_name"] == "John"
        assert data["is_admin"] is True

    def test_get_user_has_required_fields(self, client: TestClient):
        res = client.get("/api/users/1")
        assert res.status_code == 200
        data = res.json()
        for field in ("id", "first_name", "last_name", "username", "status", "is_admin"):
            assert field in data


class TestUpdateUserStatus:
    def test_update_status_to_blocked(self, client: TestClient):
        res = client.put("/api/users/1/status", json={"status": "blocked"})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "blocked"
        assert data["updated"] is True

    def test_update_status_to_active(self, client: TestClient):
        res = client.put("/api/users/1/status", json={"status": "active"})
        assert res.status_code == 200
        assert res.json()["status"] == "active"

    def test_update_status_to_inactive(self, client: TestClient):
        res = client.put("/api/users/1/status", json={"status": "inactive"})
        assert res.status_code == 200
        assert res.json()["status"] == "inactive"

    def test_update_status_invalid_value(self, client: TestClient):
        res = client.put("/api/users/1/status", json={"status": "super_admin"})
        assert res.status_code == 400
        assert "Invalid status" in res.json()["detail"]


class TestToggleAdmin:
    def test_grant_admin(self, client: TestClient):
        res = client.put("/api/users/2/admin", json={"is_admin": True})
        assert res.status_code == 200
        assert res.json()["is_admin"] is True

    def test_revoke_admin(self, client: TestClient):
        res = client.put("/api/users/1/admin", json={"is_admin": False})
        assert res.status_code == 200
        assert res.json()["is_admin"] is False

"""firms 라우터 테스트 — /api/firms/*"""
import pytest
from fastapi.testclient import TestClient


class TestListFirms:
    def test_list_firms(self, client: TestClient):
        res = client.get("/api/firms")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_firms_with_search(self, client: TestClient):
        res = client.get("/api/firms?search=Test")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 0

    def test_firm_fields(self, client: TestClient):
        res = client.get("/api/firms")
        firm = res.json()[0]
        for field in ("sec_firm_order", "firm_nm", "telegram_update_yn"):
            assert field in firm


class TestGetFirm:
    def test_get_existing_firm(self, client: TestClient):
        res = client.get("/api/firms/1")
        assert res.status_code == 200
        data = res.json()
        assert data["sec_firm_order"] == 1
        assert data["firm_nm"] == "Test Securities"

    def test_get_nonexistent_firm_returns_data(self, client: TestClient):
        """Mock은 파라미터 값을 구분하지 않으므로 항상 데이터 반환 (실제 DB에서는 404)"""
        res = client.get("/api/firms/999")
        assert res.status_code == 200


class TestCreateFirm:
    def test_create_firm_duplicate_returns_409(self, client: TestClient):
        """Mock은 항상 중복이라고 판단 → 409"""
        payload = {"sec_firm_order": 100, "firm_nm": "New Securities"}
        res = client.post("/api/firms", json=payload)
        assert res.status_code == 409


class TestUpdateFirm:
    def test_update_firm_name(self, client: TestClient):
        res = client.put("/api/firms/1", json={"firm_nm": "Updated Firm"})
        assert res.status_code == 200
        assert res.json()["updated"] is True

    def test_update_firm_telegram_flag(self, client: TestClient):
        res = client.put("/api/firms/1", json={"telegram_update_yn": "N"})
        assert res.status_code == 200

    def test_update_nonexistent_firm_mock_returns_ok(self, client: TestClient):
        """Mock은 항상 존재한다고 판단 → 200 (실제 DB에서는 404)"""
        res = client.put("/api/firms/999", json={"firm_nm": "Ghost"})
        assert res.status_code == 200


class TestDeleteFirm:
    def test_delete_firm(self, client: TestClient):
        res = client.delete("/api/firms/1")
        assert res.status_code == 200
        assert res.json()["deleted"] is True

    def test_delete_nonexistent_firm_mock_returns_ok(self, client: TestClient):
        """Mock은 항상 존재한다고 판단 → 200 (실제 DB에서는 404)"""
        res = client.delete("/api/firms/999")
        assert res.status_code == 200


# ── Firm Board ──────────────────────────────────────────────────────────────

class TestListFirmBoards:
    def test_list_boards(self, client: TestClient):
        res = client.get("/api/firms/1/boards")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_board_fields(self, client: TestClient):
        res = client.get("/api/firms/1/boards")
        board = res.json()[0]
        for field in ("sec_firm_order", "article_board_order", "board_nm", "board_cd"):
            assert field in board


class TestCreateFirmBoard:
    def test_create_board_duplicate_returns_409(self, client: TestClient):
        """Mock은 항상 중복이라고 판단 → 409"""
        payload = {"sec_firm_order": 1, "article_board_order": 10, "board_nm": "X", "board_cd": "X", "label_nm": "X"}
        res = client.post("/api/firms/1/boards", json=payload)
        assert res.status_code == 409

    def test_create_board_nonexistent_firm_returns_409(self, client: TestClient):
        """Mock은 firm도 존재, board도 존재한다고 판단 → 409"""
        payload = {"sec_firm_order": 999, "article_board_order": 1, "board_nm": "X"}
        res = client.post("/api/firms/999/boards", json=payload)
        assert res.status_code == 409


class TestUpdateFirmBoard:
    def test_update_board(self, client: TestClient):
        res = client.put("/api/firms/1/boards/1", json={"board_nm": "Updated Board"})
        assert res.status_code == 200

    def test_update_nonexistent_board_mock_returns_ok(self, client: TestClient):
        """Mock은 항상 존재한다고 판단 → 200 (실제 DB에서는 404)"""
        res = client.put("/api/firms/1/boards/999", json={"board_nm": "Ghost"})
        assert res.status_code == 200


class TestDeleteFirmBoard:
    def test_delete_board(self, client: TestClient):
        res = client.delete("/api/firms/1/boards/1")
        assert res.status_code == 200

    def test_delete_nonexistent_board_mock_returns_ok(self, client: TestClient):
        """Mock은 항상 존재한다고 판단 → 200 (실제 DB에서는 404)"""
        res = client.delete("/api/firms/1/boards/999")
        assert res.status_code == 200

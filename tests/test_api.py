#!/usr/bin/env python3
"""Tests for API routes: auth, registration, practice, trends, game endpoints."""

import importlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db


@pytest.fixture
def client(tmp_path):
    """Create a Flask test client with a fresh temporary database."""
    db_path = tmp_path / "test.db"
    os.environ["DB_PATH"] = str(db_path)
    os.environ["SECRET_KEY"] = "test-secret"

    importlib.reload(db)

    conn = db.get_db()
    db.init_db(conn)
    from werkzeug.security import generate_password_hash
    db.create_user(conn, "testuser", generate_password_hash("testpass1"))
    conn.close()

    import app as app_module
    importlib.reload(app_module)
    app_module.app.config["TESTING"] = True
    app_module.app.config["WTF_CSRF_ENABLED"] = False

    with app_module.app.test_client() as c:
        yield c


def _login(client, username="testuser", password="testpass1"):
    return client.post("/login", data={
        "username": username,
        "password": password,
    }, follow_redirects=True)


def _register(client, username, password):
    return client.post("/register", data={
        "username": username,
        "password": password,
    }, follow_redirects=True)


# --- Auth tests ---

class TestAuth:
    def test_login_wrong_password(self, client):
        res = client.post("/login", data={
            "username": "testuser", "password": "wrongpass",
        })
        assert res.status_code == 200
        assert b"Invalid" in res.data

    def test_login_nonexistent_user(self, client):
        res = client.post("/login", data={
            "username": "noone", "password": "testpass1",
        })
        assert res.status_code == 200
        assert b"Invalid" in res.data

    def test_login_success_redirects(self, client):
        res = client.post("/login", data={
            "username": "testuser", "password": "testpass1",
        })
        assert res.status_code == 302

    def test_login_already_authenticated_redirects(self, client):
        _login(client)
        res = client.get("/login")
        assert res.status_code == 302

    def test_logout(self, client):
        _login(client)
        res = client.get("/logout")
        assert res.status_code == 302
        # After logout, API should be 401
        res2 = client.get("/api/games")
        assert res2.status_code == 401


# --- Registration tests ---

class TestRegistration:
    def test_register_success(self, client):
        res = client.post("/register", data={
            "username": "newuser", "password": "longpassword",
        })
        assert res.status_code == 302  # redirect on success

    def test_register_short_password(self, client):
        res = _register(client, "newuser", "short")
        assert b"at least 8" in res.data

    def test_register_empty_fields(self, client):
        res = _register(client, "", "longpassword")
        assert b"required" in res.data

    def test_register_duplicate_username(self, client):
        res = _register(client, "testuser", "longpassword")
        assert b"already taken" in res.data

    def test_register_already_authenticated_redirects(self, client):
        _login(client)
        res = client.get("/register")
        assert res.status_code == 302


# --- API /api/me tests ---

class TestApiMe:
    def test_me_unauthenticated(self, client):
        res = client.get("/api/me")
        assert res.status_code == 401

    def test_me_authenticated(self, client):
        _login(client)
        res = client.get("/api/me")
        assert res.status_code == 200
        data = res.get_json()
        assert data["username"] == "testuser"


# --- Trends tests ---

class TestTrends:
    def test_trends_empty(self, client):
        _login(client)
        res = client.get("/api/trends")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_trends_unauthenticated(self, client):
        res = client.get("/api/trends")
        assert res.status_code == 401


# --- Practice endpoint tests ---

class TestPractice:
    def test_practice_no_problems(self, client):
        _login(client)
        res = client.get("/api/practice")
        assert res.status_code in (200, 404)  # 404 when no eligible problems

    def test_practice_stats_empty(self, client):
        _login(client)
        res = client.get("/api/practice/stats")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, dict)

    def test_practice_result_invalid_id(self, client):
        _login(client)
        res = client.post("/api/practice/result", json={
            "mistake_id": "not-an-int",
            "correct": True,
        })
        assert res.status_code == 400

    def test_practice_result_nonexistent_mistake(self, client):
        _login(client)
        res = client.post("/api/practice/result", json={
            "mistake_id": 99999,
            "correct": True,
        })
        # Should fail ownership check
        assert res.status_code in (400, 403, 404)

    def test_practice_unauthenticated(self, client):
        res = client.get("/api/practice")
        assert res.status_code == 401


# --- Game endpoints tests ---

class TestGameEndpoints:
    def test_get_nonexistent_game(self, client):
        _login(client)
        res = client.get("/api/games/99999")
        assert res.status_code == 404

    def test_delete_nonexistent_game(self, client):
        _login(client)
        res = client.delete("/api/games/99999")
        assert res.status_code == 404

    def test_games_list_empty(self, client):
        _login(client)
        res = client.get("/api/games")
        assert res.status_code == 200
        assert res.get_json() == []

    def test_add_game_no_data(self, client):
        _login(client)
        res = client.post("/api/games/add", json={})
        assert res.status_code == 400

    def test_health_endpoint(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.get_json()["status"] == "ok"

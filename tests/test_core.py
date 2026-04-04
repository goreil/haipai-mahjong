#!/usr/bin/env python3
"""Tests for core functionality: parsing, categorization, database, and API routes."""

import json
import os
import sys
import tempfile

import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db
from mj_parse import parse_game, round_header, severity
from mj_categorize import (
    MJAI_TO_ID, ID_TO_MJAI, mjai_to_tile_id, tile_id_to_base,
    extract_board_state, reconstruct_context, subtract_hand_from_wall,
    flatten_mjai_log,
)


# --- Fixtures ---

@pytest.fixture
def tmp_db():
    """Create a temporary SQLite database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = db.get_db(db_path=path)
    db.init_db(conn)
    yield conn
    conn.close()
    os.unlink(path)


@pytest.fixture
def sample_user(tmp_db):
    """Create a test user and return (conn, user_id)."""
    from werkzeug.security import generate_password_hash
    uid = db.create_user(tmp_db, "testuser", generate_password_hash("testpass"))
    return tmp_db, uid


@pytest.fixture
def mortal_data():
    """Load the sample Mortal analysis JSON."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "mortal_analysis", "2c7268c4e0205cc0.json")
    if not os.path.exists(path):
        pytest.skip("Sample Mortal JSON not available")
    with open(path) as f:
        return json.load(f)


# --- mj_parse tests ---

class TestParsing:
    def test_severity_levels(self):
        assert severity(0.01) == "?"
        assert severity(0.49) == "?"
        assert severity(0.50) == "??"
        assert severity(1.00) == "??"
        assert severity(1.01) == "???"

    def test_round_header(self):
        assert round_header({"bakaze": "E", "kyoku": 1, "honba": 0}) == "E1"
        assert round_header({"bakaze": "S", "kyoku": 3, "honba": 2}) == "S3-2"

    def test_parse_game_structure(self, mortal_data):
        game = parse_game(mortal_data, game_date="2026-01-01")
        assert game["date"] == "2026-01-01"
        assert isinstance(game["rounds"], list)
        assert len(game["rounds"]) > 0

        rnd = game["rounds"][0]
        assert "round" in rnd
        assert isinstance(rnd["mistakes"], list)

    def test_parse_game_mistakes(self, mortal_data):
        game = parse_game(mortal_data, game_date="2026-01-01")
        # Find a round with mistakes
        mistakes = [m for rnd in game["rounds"] for m in rnd["mistakes"]]
        assert len(mistakes) > 0

        m = mistakes[0]
        assert "turn" in m
        assert "severity" in m
        assert "ev_loss" in m
        assert "hand" in m
        assert isinstance(m["hand"], list)
        assert "actual" in m
        assert "expected" in m
        assert "top_actions" in m


# --- mj_categorize tests ---

class TestTileConversion:
    def test_mjai_to_id_basic(self):
        assert mjai_to_tile_id("1m") == 0
        assert mjai_to_tile_id("9s") == 26
        assert mjai_to_tile_id("E") == 27
        assert mjai_to_tile_id("C") == 33
        assert mjai_to_tile_id("5mr") == 34

    def test_id_to_mjai_roundtrip(self):
        for mjai, tid in MJAI_TO_ID.items():
            assert ID_TO_MJAI[tid] == mjai

    def test_tile_id_to_base(self):
        assert tile_id_to_base(4) == 4   # 5m base
        assert tile_id_to_base(34) == 4  # 5mr -> 5m
        assert tile_id_to_base(35) == 13  # 5pr -> 5p
        assert tile_id_to_base(36) == 22  # 5sr -> 5s
        assert tile_id_to_base(27) == 27  # E stays E


class TestBoardState:
    def test_extract_board_state(self, mortal_data):
        kyokus = mortal_data["review"]["kyokus"]
        entry = next(e for e in kyokus[0]["entries"] if not e["is_equal"])

        board = extract_board_state(mortal_data, 0, entry["tiles_left"])
        assert "dora_indicators" in board
        assert isinstance(board["dora_indicators"], list)
        assert len(board["dora_indicators"]) >= 1

        assert board["seat_wind"] in ("E", "S", "W", "N")
        assert board["round_wind"] in ("E", "S")

        assert isinstance(board["scores"], list)
        assert len(board["scores"]) == 4

        assert isinstance(board["all_discards"], list)
        assert len(board["all_discards"]) == 4
        for d in board["all_discards"]:
            assert "seat" in d
            assert "discards" in d
            assert "riichi_idx" in d

    def test_board_state_late_game(self, mortal_data):
        """Board state with more events should have more discards."""
        kyokus = mortal_data["review"]["kyokus"]
        for ki in range(len(kyokus)):
            for entry in kyokus[ki]["entries"]:
                if not entry["is_equal"] and entry["tiles_left"] < 50:
                    board = extract_board_state(mortal_data, ki, entry["tiles_left"])
                    total_discards = sum(len(d["discards"]) for d in board["all_discards"])
                    assert total_discards > 0
                    return
        pytest.skip("No late-game mistakes found")


# --- db tests ---

class TestDatabase:
    def test_init_db(self, tmp_db):
        tables = tmp_db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {r["name"] for r in tables}
        assert "users" in table_names
        assert "games" in table_names
        assert "mistakes" in table_names
        assert "feedback" in table_names

    def test_create_user(self, tmp_db):
        from werkzeug.security import generate_password_hash
        uid = db.create_user(tmp_db, "alice", generate_password_hash("pw"))
        assert uid is not None
        user = db.get_user_by_username(tmp_db, "alice")
        assert user is not None
        assert user["username"] == "alice"

    def test_add_and_get_game(self, sample_user):
        conn, uid = sample_user
        game_dict = {
            "date": "2026-01-01",
            "log_url": None,
            "mortal_file": None,
            "summary": {"total_mistakes": 1, "total_ev_loss": 0.5},
            "rounds": [{
                "round": "E1",
                "honba": 0,
                "turn_count": 10,
                "outcome": None,
                "mistakes": [{
                    "turn": 5,
                    "severity": "??",
                    "ev_loss": 0.50,
                    "category": "1A",
                    "note": None,
                    "hand": ["1m", "2m", "3m"],
                    "melds": [],
                    "shanten": 1,
                    "draw": "4m",
                    "actual": {"type": "dahai", "pai": "1m"},
                    "expected": {"type": "dahai", "pai": "3m"},
                    "top_actions": [],
                }],
            }],
        }
        gid = db.add_game(conn, uid, game_dict)
        assert gid is not None

        game = db.get_game(conn, gid, user_id=uid)
        assert game is not None
        assert game["date"] == "2026-01-01"
        assert len(game["rounds"]) == 1
        assert len(game["rounds"][0]["mistakes"]) == 1
        assert game["rounds"][0]["mistakes"][0]["turn"] == 5

    def test_delete_game(self, sample_user):
        conn, uid = sample_user
        game_dict = {
            "date": "2026-01-01",
            "rounds": [{"round": "E1", "honba": 0, "turn_count": 5,
                         "outcome": None, "mistakes": []}],
        }
        gid = db.add_game(conn, uid, game_dict)
        assert db.delete_game(conn, gid, user_id=uid) is True
        assert db.get_game(conn, gid, user_id=uid) is None

    def test_update_mistake_data(self, sample_user):
        conn, uid = sample_user
        game_dict = {
            "date": "2026-01-01",
            "rounds": [{"round": "E1", "honba": 0, "turn_count": 10,
                         "outcome": None, "mistakes": [{
                "turn": 3, "severity": "?", "ev_loss": 0.05,
                "category": None, "note": None,
                "hand": ["1m"], "melds": [], "actual": {"type": "dahai", "pai": "1m"},
                "expected": {"type": "dahai", "pai": "2m"}, "top_actions": [],
            }]}],
        }
        gid = db.add_game(conn, uid, game_dict)
        mid = conn.execute("SELECT id FROM mistakes WHERE game_id = ?", (gid,)).fetchone()["id"]

        db.update_mistake_data(conn, mid, {"category": "1A", "cpp_best": "2m"})

        row = conn.execute("SELECT * FROM mistakes WHERE id = ?", (mid,)).fetchone()
        assert row["category"] == "1A"
        data = json.loads(row["data_json"])
        assert data["cpp_best"] == "2m"

    def test_list_games(self, sample_user):
        conn, uid = sample_user
        for i in range(3):
            db.add_game(conn, uid, {
                "date": f"2026-01-0{i+1}",
                "rounds": [{"round": "E1", "honba": 0, "turn_count": 5,
                             "outcome": None, "mistakes": []}],
            })
        games = db.list_games(conn, uid)
        assert len(games) == 3

    def test_feedback_insertion(self, sample_user):
        conn, uid = sample_user
        conn.execute(
            "INSERT INTO feedback (user_id, type, message) VALUES (?, ?, ?)",
            (uid, "bug", "Something is broken"),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM feedback WHERE user_id = ?", (uid,)).fetchone()
        assert row["type"] == "bug"
        assert row["message"] == "Something is broken"


# --- API route tests ---

class TestAPI:
    @pytest.fixture
    def client(self, tmp_path):
        """Create a Flask test client with a temporary database."""
        db_path = tmp_path / "test.db"
        os.environ["DB_PATH"] = str(db_path)
        os.environ["SECRET_KEY"] = "test-secret"

        # Re-import to pick up new DB_PATH
        import importlib
        importlib.reload(db)

        conn = db.get_db()
        db.init_db(conn)

        from werkzeug.security import generate_password_hash
        db.create_user(conn, "testuser", generate_password_hash("testpass"))
        conn.close()

        # Import app after DB setup
        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["WTF_CSRF_ENABLED"] = False

        with app_module.app.test_client() as client:
            yield client

    def _login(self, client):
        return client.post("/login", data={
            "username": "testuser",
            "password": "testpass",
        }, follow_redirects=True)

    def test_login_required(self, client):
        res = client.get("/api/games")
        assert res.status_code == 401

    def test_login_and_games(self, client):
        self._login(client)
        res = client.get("/api/games")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)

    def test_feedback_api(self, client):
        self._login(client)
        res = client.post("/api/feedback", json={
            "type": "bug",
            "message": "Test feedback",
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data["ok"] is True

    def test_feedback_validation(self, client):
        self._login(client)
        res = client.post("/api/feedback", json={"type": "bug", "message": ""})
        assert res.status_code == 400

    def test_categories_api(self, client):
        self._login(client)
        res = client.get("/api/categories")
        assert res.status_code == 200
        data = res.get_json()
        assert "1A" in data

    def test_annotate_validation(self, client):
        """Input validation on annotate endpoint."""
        self._login(client)
        # Missing required fields
        res = client.post("/api/games/1/annotate", json={})
        assert res.status_code == 400
        # Invalid category
        res = client.post("/api/games/1/annotate", json={
            "round": "E1", "turn": 1, "category": "INVALID"
        })
        assert res.status_code == 400

    def test_feedback_type_validation(self, client):
        """Feedback type must be bug/feature/general."""
        self._login(client)
        res = client.post("/api/feedback", json={
            "type": "malicious",
            "message": "test",
        })
        assert res.status_code == 400

    def test_practice_result_validation(self, client):
        """Practice result requires integer mistake_id."""
        self._login(client)
        res = client.post("/api/practice/result", json={
            "mistake_id": "not-an-int",
            "correct": True,
        })
        assert res.status_code == 400


# --- Wall reconstruction tests ---

class TestWallReconstruction:
    def test_wall_no_negatives(self, mortal_data):
        """Wall values should not go negative after subtracting hand."""
        kyokus = mortal_data["review"]["kyokus"]
        events = flatten_mjai_log(mortal_data["mjai_log"])
        start_events = [e for e in events if e.get("type") == "start_kyoku"]

        for ki, kyoku in enumerate(kyokus):
            for entry in kyoku["entries"]:
                if entry["is_equal"]:
                    continue
                hand = [t for t in entry["state"]["tehai"] if t != "?"]
                if not hand:
                    continue
                wall, _, _, _ = reconstruct_context(mortal_data, ki, entry["tiles_left"])
                wall2 = subtract_hand_from_wall(wall, hand)
                for i, v in enumerate(wall2):
                    assert v >= -1, f"kyoku={ki} tiles_left={entry['tiles_left']} wall[{i}]={v}"

    def test_wall_hand_consistency(self, mortal_data):
        """For each tile, wall + hand should not exceed 4 (or 1 for red fives)."""
        kyokus = mortal_data["review"]["kyokus"]

        kyoku = kyokus[0]
        entry = kyoku["entries"][0]
        hand = [t for t in entry["state"]["tehai"] if t != "?"]

        wall, _, _, _ = reconstruct_context(mortal_data, 0, entry["tiles_left"])
        wall2 = subtract_hand_from_wall(wall, hand)

        hand_ids = [mjai_to_tile_id(t) for t in hand]
        for i in range(34):
            in_hand = sum(1 for h in hand_ids if tile_id_to_base(h) == i)
            # Wall + hand should not exceed total copies (4)
            assert wall2[i] + in_hand <= 4, f"tile {i}: wall={wall2[i]} hand={in_hand}"


# --- Add game pipeline tests ---

SMALL_MORTAL_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "mortal_analysis", "e62f1f8cad825afa.json",
)


class TestAddGamePipeline:
    """End-to-end: add a game via the API and verify categorization results in DB."""

    @pytest.fixture
    def client(self, tmp_path):
        db_path = tmp_path / "test.db"
        os.environ["DB_PATH"] = str(db_path)
        os.environ["SECRET_KEY"] = "test-secret"

        import importlib
        importlib.reload(db)

        conn = db.get_db()
        db.init_db(conn)
        from werkzeug.security import generate_password_hash
        db.create_user(conn, "testuser", generate_password_hash("testpass"))
        conn.close()

        import app as app_module
        importlib.reload(app_module)
        app_module.app.config["TESTING"] = True
        app_module.app.config["WTF_CSRF_ENABLED"] = False

        with app_module.app.test_client() as client:
            # Login
            client.post("/login", data={"username": "testuser", "password": "testpass"},
                        follow_redirects=True)
            yield client

    @pytest.fixture
    def mortal_json(self):
        if not os.path.exists(SMALL_MORTAL_FILE):
            pytest.skip("mortal analysis file not found")
        with open(SMALL_MORTAL_FILE) as f:
            return json.load(f)

    def test_add_game_returns_json(self, client, mortal_json):
        """POST /api/games/add should return valid JSON with game_id."""
        res = client.post("/api/games/add", json={"mortal_data": mortal_json},
                          content_type="application/json")
        assert res.status_code == 200, f"Status {res.status_code}: {res.data[:200]}"
        data = res.get_json()
        assert data is not None, f"Response is not JSON: {res.data[:200]}"
        assert data.get("ok") is True
        assert "game_id" in data
        assert isinstance(data["game_id"], int)

    def test_add_game_categorizes_mistakes(self, client, mortal_json):
        """Added game should have categorized mistakes in the DB."""
        res = client.post("/api/games/add", json={"mortal_data": mortal_json},
                          content_type="application/json")
        data = res.get_json()
        game_id = data["game_id"]
        assert data.get("categorized", 0) > 0, f"No mistakes categorized: {data}"

        # Verify categories are in the DB
        conn = db.get_db()
        rows = conn.execute(
            "SELECT category FROM mistakes WHERE game_id = ? AND category IS NOT NULL",
            (game_id,),
        ).fetchall()
        assert len(rows) > 0, "No categorized mistakes in DB"

        # All categories should be valid
        valid_cats = {"1A", "2A", "3A", "3B", "3C", "4A", "4B", "4C", "5A", "5B", "6A", "6B"}
        for row in rows:
            assert row["category"] in valid_cats, f"Invalid category: {row['category']}"

    def test_add_game_has_summary(self, client, mortal_json):
        """Added game should have a computed summary with EV stats."""
        res = client.post("/api/games/add", json={"mortal_data": mortal_json},
                          content_type="application/json")
        data = res.get_json()
        summary = data.get("summary", {})
        assert summary.get("total_mistakes", 0) > 0
        assert "total_ev_loss" in summary
        assert "by_severity" in summary

    def test_add_game_has_board_state(self, client, mortal_json):
        """Each mistake should have board_state populated."""
        res = client.post("/api/games/add", json={"mortal_data": mortal_json},
                          content_type="application/json")
        data = res.get_json()
        game_id = data["game_id"]

        conn = db.get_db()
        rows = conn.execute(
            "SELECT data_json FROM mistakes WHERE game_id = ?", (game_id,),
        ).fetchall()
        for row in rows:
            mdata = json.loads(row["data_json"])
            assert "board_state" in mdata, f"Missing board_state in mistake"

    def test_get_game_after_add(self, client, mortal_json):
        """GET /api/games/<id> should return the added game with mistakes."""
        res = client.post("/api/games/add", json={"mortal_data": mortal_json},
                          content_type="application/json")
        game_id = res.get_json()["game_id"]

        res2 = client.get(f"/api/games/{game_id}")
        assert res2.status_code == 200
        game = res2.get_json()
        assert game["id"] == game_id
        assert len(game.get("rounds", [])) > 0
        # At least one round should have mistakes
        all_mistakes = [m for r in game["rounds"] for m in r.get("mistakes", [])]
        assert len(all_mistakes) > 0

    def test_delete_game(self, client, mortal_json):
        """DELETE /api/games/<id> should remove the game."""
        res = client.post("/api/games/add", json={"mortal_data": mortal_json},
                          content_type="application/json")
        game_id = res.get_json()["game_id"]

        res2 = client.delete(f"/api/games/{game_id}")
        assert res2.status_code == 200

        res3 = client.get(f"/api/games/{game_id}")
        assert res3.status_code == 404

    def test_categorize_endpoint(self, client, mortal_json):
        """POST /api/games/<id>/categorize should re-categorize."""
        res = client.post("/api/games/add", json={"mortal_data": mortal_json},
                          content_type="application/json")
        game_id = res.get_json()["game_id"]

        # Force re-categorize
        res2 = client.post(f"/api/games/{game_id}/categorize",
                           json={"force": True}, content_type="application/json")
        assert res2.status_code == 200
        data = res2.get_json()
        assert data.get("ok") is True
        assert data.get("categorized", 0) > 0

    def test_trends_after_add(self, client, mortal_json):
        """GET /api/trends should include data after adding a game."""
        client.post("/api/games/add", json={"mortal_data": mortal_json},
                    content_type="application/json")

        res = client.get("/api/trends")
        assert res.status_code == 200
        trends = res.get_json()
        assert len(trends) > 0
        assert "date" in trends[0]
        assert "total_ev_loss" in trends[0]

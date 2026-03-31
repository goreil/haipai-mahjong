#!/usr/bin/env python3
"""Migrate games.json to SQLite database (games.db).

Creates the database, imports all games under a default user (id=1),
and verifies row counts match.
"""

import json
import sys
from pathlib import Path
from werkzeug.security import generate_password_hash

import db

DIR = Path(__file__).parent
GAMES_JSON = DIR / "games.json"
DEFAULT_USERNAME = "ylue"
DEFAULT_PASSWORD = "changeme"


def main():
    if not GAMES_JSON.exists():
        print(f"Error: {GAMES_JSON} not found", file=sys.stderr)
        sys.exit(1)

    if db.DB_FILE.exists():
        print(f"Warning: {db.DB_FILE} already exists. Delete it first to re-migrate.")
        sys.exit(1)

    with open(GAMES_JSON) as f:
        data = json.load(f)

    games = data.get("games", [])
    print(f"Loaded {len(games)} games from {GAMES_JSON}")

    conn = db.get_db()
    db.init_db(conn)

    # Create default user
    password_hash = generate_password_hash(DEFAULT_PASSWORD)
    db.create_user(conn, DEFAULT_USERNAME, password_hash)
    print(f"Created default user: {DEFAULT_USERNAME} (password: {DEFAULT_PASSWORD})")
    print(f"  >>> CHANGE THIS PASSWORD after first login! <<<")

    # Import games
    total_mistakes = 0
    total_rounds = 0
    for i, game in enumerate(games):
        game_id = db.add_game(conn, user_id=1, game_dict=game)

        n_rounds = len(game.get("rounds", []))
        n_mistakes = sum(len(r.get("mistakes", [])) for r in game.get("rounds", []))
        total_rounds += n_rounds
        total_mistakes += n_mistakes
        print(f"  Game {i+1} ({game.get('date', '?')}): id={game_id}, {n_rounds} rounds, {n_mistakes} mistakes")

    # Verify
    db_games = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
    db_mistakes = conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0]

    print(f"\nMigration complete:")
    print(f"  Games:    {db_games} (expected {len(games)})")
    print(f"  Mistakes: {db_mistakes} (expected {total_mistakes})")

    if db_games != len(games) or db_mistakes != total_mistakes:
        print("  WARNING: counts don't match!", file=sys.stderr)
    else:
        print("  All counts match.")

    conn.close()
    print(f"\nDatabase saved to {db.DB_FILE}")
    print(f"games.json kept as backup (no longer used by the app)")


if __name__ == "__main__":
    main()

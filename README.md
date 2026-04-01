# Haipai - Mahjong Mistake Trainer

Personal Riichi Mahjong game analysis tool. Analyzes Tenhou replays via Mortal AI, stores structured mistake data, and provides a web UI for review, annotation, and practice.

## Deployment

### Prerequisites

- Docker + Docker Compose
- Domain with DNS pointing to the server (for HTTPS via certbot)

### First-time setup

```bash
git clone <repo-url> && cd haipai-mahjong
git submodule update --init --recursive

# Build (compiles mahjong-cpp C++ binary — takes a few minutes)
docker compose build

# Generate invite codes for user registration
docker compose up -d
docker compose exec app python3 -c "
import db
conn = db.get_db()
db.init_db(conn)
codes = db.create_invite_codes(conn, 3)
print('Invite codes:', codes)
conn.close()
"
```

### Deploying updates

After `git pull`, the type of restart depends on what changed:

| What changed | What to do |
|---|---|
| Python files (`*.py`) | Nothing — gunicorn `--reload` picks up changes automatically via volume mounts |
| Static files (`static/`) | Nothing — served directly via volume mount, just refresh browser |
| `requirements.txt` | `docker compose build && docker compose up -d` |
| `Dockerfile` | `docker compose build && docker compose up -d` |
| `docker-compose.yml` | `docker compose up -d` (recreates containers with new config) |
| `mahjong-cpp/` submodule | `docker compose build && docker compose up -d` |
| `nginx.conf` | `docker compose exec nginx nginx -s reload` |

**TL;DR for most code changes:** just `git pull` and it's live.

If the volume mounts aren't set up yet (first deploy or after a fresh `docker compose build`), run:

```bash
docker compose up -d
```

This recreates the containers with the source-mount volumes and `--reload` flag.

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `change-me-in-production` | Flask session secret — set to a random string |
| `DB_PATH` | `/app/data/games.db` | SQLite database path (persisted via `app-data` volume) |
| `NANIKIRU_BIN` | `/opt/nanikiru/nanikiru` | Path to mahjong-cpp tile efficiency binary |

### Architecture

```
Browser -> nginx (port 80/443) -> gunicorn (port 5000) -> Flask app
                                                       -> nanikiru (port 50000, local)
```

- **nginx**: reverse proxy + TLS termination
- **gunicorn**: Python WSGI server with `--reload` for hot code reloading
- **nanikiru**: C++ tile efficiency calculator, auto-started by Flask
- **SQLite**: game data stored in Docker volume `app-data`
- Source files are mounted read-only into the container so `git pull` takes effect immediately

# Infrastructure & DevOps Issues

**Date**: 2026-04-04
**Stack**: Flask + gunicorn, nginx, certbot, Docker Compose, GitHub Actions
**Host**: haipai.ylue.de (single Hetzner VPS)

---

## High Priority

### ~~I-01: gunicorn --reload in production~~ ✅

**Location**: `docker-compose.yml:19`

The compose file uses `--reload` which watches for file changes and restarts workers. This is a dev-only feature. In production it causes unnecessary restarts on any file write (e.g. SQLite WAL changes, log rotation) and has a minor security concern if the filesystem is writable.

**Fix**: Remove `--reload` from docker-compose.yml. Use a separate `docker-compose.override.yml` for dev with `--reload`.

---

### ~~I-02: No health check endpoint~~ ✅

**Location**: `app.py` (missing), `Dockerfile` (no HEALTHCHECK), `docker-compose.yml` (no healthcheck)

No `/health` route exists. Docker can't determine if the app is actually serving requests vs hung. The deploy workflow can't verify a deploy succeeded.

**Fix**: Add a simple `/health` route that returns 200. Add `HEALTHCHECK` to Dockerfile. Add `healthcheck` to docker-compose.yml. Check it after deploy in `deploy.yml`.

---

### I-03: No backup automation

**Location**: `DEPLOY.md:129-137`

Backups are manual `docker cp` commands stored on the same server as the data. No scheduling, no offsite copies, no retention policy, no restore testing.

**Fix**: Add a cron job or systemd timer for daily DB backups. Copy to offsite storage (Hetzner backup, S3, etc.). Document restore procedure.

---

### ~~I-04: No .env.example~~ ✅

**Location**: project root (missing)

No template showing required environment variables. New developers or deployments have to read through docker-compose.yml and app.py to discover what's needed.

**Fix**: Create `.env.example` with all variables documented (SECRET_KEY, FLASK_ENV, etc.).

---

## Medium Priority

### I-05: Image versions not pinned

**Location**: `Dockerfile:2,18`, `docker-compose.yml:24,37`

- `python:3.12-slim` -- could get different patch versions across builds
- `debian:12-slim` -- same issue
- `nginx:alpine` -- no version at all
- `certbot/certbot` -- no version

**Fix**: Pin to specific versions (e.g. `python:3.12.7-slim-bookworm`, `nginx:1.27-alpine`).

---

### ~~I-06: No nginx caching or compression~~ ✅

**Location**: `nginx.conf.template`

No `Cache-Control` headers for static assets (tiles, CSS, JS). No gzip compression enabled. Every page load re-transfers all 37 tile SVGs.

**Fix**: Add `gzip on; gzip_types text/plain application/json text/css image/svg+xml;`. Add `expires 1y;` for `/tiles/` and `/static/` locations.

---

### I-07: Certbot renewal has no alerting

**Location**: `docker-compose.yml:36-41`

Certbot runs in a loop with 12h sleep. If renewal fails, nobody knows until users see certificate errors. No logging, no health check, no notification.

**Fix**: Add a cert expiry check endpoint or cron job that alerts (email, webhook) when cert expires within 14 days.

---

### I-08: CI missing coverage and linting

**Location**: `.github/workflows/test.yml`

CI runs pytest but doesn't:
- Report code coverage or enforce a threshold
- Run any linter (flake8, ruff, mypy)
- Cache pip dependencies (rebuilds from scratch each run)
- Run `pip audit` for known vulnerabilities

**Fix**: Add `pytest-cov` with minimum threshold. Add `ruff` or `flake8`. Cache pip with `actions/setup-python` cache option.

---

### I-09: Deploy has no rollback or health verification

**Location**: `.github/workflows/deploy.yml`

The deploy workflow pushes code and restarts, but doesn't verify the app came back healthy. If the deploy breaks the app, it stays broken until someone notices manually. No rollback automation.

**Fix**: After deploy, `curl` the health endpoint. If it fails, `git revert` and redeploy, or at minimum send a notification.

---

### ~~I-10: HTTPS redirect commented out~~ ✅

**Location**: `nginx.conf.template:6`

The HTTP-to-HTTPS redirect is commented out. If HTTPS is enabled (which it is for haipai.ylue.de), users can still access the site over plain HTTP.

**Fix**: Uncomment the redirect. Add HSTS header.

---

## Low Priority

### I-11: No resource limits in docker-compose

**Location**: `docker-compose.yml`

No CPU or memory limits on any container. A runaway process (e.g. mahjong-cpp on a complex hand) could consume all server resources.

---

### I-12: entrypoint.sh runs chown on every startup

**Location**: `entrypoint.sh:3`

`chown -R appuser:appuser /app/data` runs every container start. On large data directories this adds unnecessary startup time. Should be done once at build time or volume creation.

---

### I-13: Dependencies use ~= instead of ==

**Location**: `requirements.txt`

Compatible release constraints (`~=`) allow minor version drift between installs. For reproducible builds, pin exact versions with `==`.

---

### I-14: No deployment approval gate

**Location**: `.github/workflows/deploy.yml`

Any push to main auto-deploys. For a single-operator project this is fine, but becomes risky with multiple contributors.

---

### I-15: deploy.yml race condition on fresh repo

**Location**: `.github/workflows/deploy.yml:50`

`git diff HEAD~1` fails if the repo has only one commit (e.g. after a force push). Edge case, but would break the deploy.

# Eisstock Tournament Manager

Tournament management software for Eisstock-Vereine. Handles team tournaments (3-8 teams across 3 Bahnen) and Zielschießen (4 disciplines, configurable rounds), with live multi-tablet score entry, TV scoreboards, and printable Siegerliste exports.

## Status

Greenfield, building MVP for club beta-test. See `Eisstock_Schema.md` for the source requirements.

## Stack

- Python 3.13 + FastAPI + SQLModel (SQLite)
- Server-rendered HTML with HTMX + Alpine.js (no build step)
- Server-Sent Events for live cross-tablet sync
- Single SQLite file = one tournament's full state

## Local dev (Windows)

```powershell
python -m venv $env:USERPROFILE\.venvs\eisstock-dev
& $env:USERPROFILE\.venvs\eisstock-dev\Scripts\python.exe -m pip install -r requirements.txt
& $env:USERPROFILE\.venvs\eisstock-dev\Scripts\python.exe -m uvicorn eisstock.app:app --reload --host 0.0.0.0 --port 8000
```

The venv lives outside OneDrive on purpose — OneDrive sync chokes on the thousands of small files in a Python venv.

Tablets on the same WiFi: open `http://<your-machine-ip>:8000/` in Chrome.

## Project layout

```
src/eisstock/
  app.py              # FastAPI entrypoint
  rotation.py         # Pure-logic schedule generator for 3/4/5/6/7/8'er Spiegel
  models.py           # SQLModel entities
  routes/             # tournament, score-entry, display, standings, zielschiessen
  templates/          # Jinja templates
  static/             # CSS, JS
tests/
  test_rotation.py
```

## Beta deploy

Built to run identically on:
- Local laptop (dev): `uvicorn` directly
- Home NUC (24/7 staging): `docker compose up -d`
- Hetzner (public demo for husband): same docker-compose behind Caddy
- Halle laptop on tournament day: same Docker image, or plain `uvicorn`

The DB is one SQLite file. To migrate environments, copy the file.

"""FastAPI app for the Eisstock tournament manager.

Single-process HTTP server intended for LAN-only or small-cloud deployment.
Tablets and the TV display all hit the same routes; the TV display uses a
1-second meta-refresh for now (SSE is a planned upgrade).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from eisstock.db import engine, get_session, init_db
from eisstock.models import (
    Game,
    Player,
    Team,
    Tournament,
    TournamentMode,
)
from eisstock.service import (
    TeamSpec,
    compute_standings,
    create_normal_tournament,
    games_for_bahn,
    list_tournaments,
    set_round_score,
    summarize_game,
)

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))


@asynccontextmanager
async def _lifespan(app: FastAPI):
    init_db()
    yield


def make_app() -> FastAPI:
    app = FastAPI(
        title="Eisstock Tournament Manager", version="0.1.0", lifespan=_lifespan
    )
    app.mount("/static", StaticFiles(directory=str(PACKAGE_DIR / "static")), name="static")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, session: Session = Depends(get_session)) -> HTMLResponse:
        tournaments = list_tournaments(session)
        return TEMPLATES.TemplateResponse(
            request, "index.html", {"tournaments": tournaments}
        )

    @app.get("/new", response_class=HTMLResponse)
    def new_tournament_form(request: Request) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, "new_tournament.html", {})

    @app.post("/new")
    async def new_tournament_submit(
        request: Request,
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        form = await request.form()
        name = str(form.get("name", "")).strip() or "Turnier"
        mode = str(form.get("mode", "normal"))
        team_count = int(form.get("team_count", 6))
        durchgaenge = int(form.get("durchgaenge", 1))
        rounds_per_game = int(form.get("rounds_per_game", 6))

        if mode != "normal":
            raise HTTPException(400, "Nur 'normal' wird aktuell unterstützt.")

        teams: list[TeamSpec] = []
        for i in range(1, team_count + 1):
            tname = str(form.get(f"team_name_{i}", "")).strip() or f"Team {i}"
            tnation = str(form.get(f"team_nation_{i}", "")).strip()
            players_raw = str(form.get(f"team_players_{i}", "")).strip()
            players = tuple(p.strip() for p in players_raw.split(",") if p.strip())
            teams.append(TeamSpec(name=tname, nation=tnation, players=players))

        tournament = create_normal_tournament(
            session,
            name=name,
            teams=teams,
            durchgaenge=durchgaenge,
            rounds_per_game=rounds_per_game,
        )
        return RedirectResponse(url=f"/tournament/{tournament.id}", status_code=303)

    @app.get("/tournament/{tournament_id}", response_class=HTMLResponse)
    def tournament_overview(
        tournament_id: int,
        request: Request,
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        tournament = session.get(Tournament, tournament_id)
        if tournament is None:
            raise HTTPException(404, "Turnier nicht gefunden")

        teams_rows = list(
            session.exec(
                select(Team)
                .where(Team.tournament_id == tournament_id)
                .order_by(Team.position)  # type: ignore[arg-type]
            )
        )
        players_by_team: dict[int, list[str]] = {}
        for player in session.exec(
            select(Player)
            .where(Player.team_id.in_([t.id for t in teams_rows]))  # type: ignore[union-attr]
            .order_by(Player.order_idx)  # type: ignore[arg-type]
        ):
            players_by_team.setdefault(player.team_id, []).append(player.name)

        teams = [
            {
                "name": t.name,
                "nation": t.nation,
                "players": players_by_team.get(t.id, []),
            }
            for t in teams_rows
        ]

        bahnen = sorted(
            {g.bahn for g in session.exec(select(Game).where(Game.tournament_id == tournament_id))},
            key=lambda b: (b == "Zusatz", b),
        )

        return TEMPLATES.TemplateResponse(
            request,
            "tournament.html",
            {"tournament": tournament, "teams": teams, "bahnen": bahnen},
        )

    @app.get("/tournament/{tournament_id}/bahn/{bahn}", response_class=HTMLResponse)
    def bahn_entry(
        tournament_id: int,
        bahn: str,
        request: Request,
        game: int | None = Query(default=None),
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        tournament = session.get(Tournament, tournament_id)
        if tournament is None:
            raise HTTPException(404, "Turnier nicht gefunden")

        games_rows = games_for_bahn(session, tournament_id, bahn)
        summaries = [summarize_game(session, g.id) for g in games_rows]  # type: ignore[arg-type]

        if not summaries:
            current_game = None
        elif game is not None:
            current_game = next((s for s in summaries if s.game.id == game), summaries[0])
        else:
            current_game = _pick_focus_game(summaries)

        return TEMPLATES.TemplateResponse(
            request,
            "bahn_entry.html",
            {
                "tournament": tournament,
                "bahn": bahn,
                "games": summaries,
                "current_game": current_game,
            },
        )

    @app.post("/tournament/{tournament_id}/bahn/{bahn}/score")
    async def record_score(
        tournament_id: int,
        bahn: str,
        request: Request,
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        form = await request.form()
        game_id = int(form.get("game_id"))  # type: ignore[arg-type]
        round_idx = int(form.get("round_idx"))  # type: ignore[arg-type]
        scoring_team_id = int(form.get("scoring_team_id"))  # type: ignore[arg-type]
        stockpunkte = int(form.get("stockpunkte", 1))
        set_round_score(
            session,
            game_id=game_id,
            round_idx=round_idx,
            scoring_team_id=scoring_team_id,
            stockpunkte=stockpunkte,
        )
        return RedirectResponse(
            url=f"/tournament/{tournament_id}/bahn/{bahn}?game={game_id}",
            status_code=303,
        )

    @app.get("/tournament/{tournament_id}/display/{bahn}", response_class=HTMLResponse)
    def bahn_display(
        tournament_id: int,
        bahn: str,
        request: Request,
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        tournament = session.get(Tournament, tournament_id)
        if tournament is None:
            raise HTTPException(404, "Turnier nicht gefunden")
        games_rows = games_for_bahn(session, tournament_id, bahn)
        summaries = [summarize_game(session, g.id) for g in games_rows]  # type: ignore[arg-type]
        current_game = _pick_active_game(summaries) if summaries else None
        return TEMPLATES.TemplateResponse(
            request,
            "bahn_display.html",
            {"tournament": tournament, "bahn": bahn, "current_game": current_game},
        )

    @app.get("/tournament/{tournament_id}/standings", response_class=HTMLResponse)
    def standings_page(
        tournament_id: int,
        request: Request,
        session: Session = Depends(get_session),
    ) -> HTMLResponse:
        tournament = session.get(Tournament, tournament_id)
        if tournament is None:
            raise HTTPException(404, "Turnier nicht gefunden")
        standings = compute_standings(session, tournament_id)
        return TEMPLATES.TemplateResponse(
            request,
            "standings.html",
            {"tournament": tournament, "standings": standings},
        )

    @app.post("/tournament/{tournament_id}/deductions")
    async def set_deductions(
        tournament_id: int,
        request: Request,
        session: Session = Depends(get_session),
    ) -> RedirectResponse:
        form = await request.form()
        team_rows = list(
            session.exec(select(Team).where(Team.tournament_id == tournament_id))
        )
        for team in team_rows:
            dp = form.get(f"dp_{team.id}")
            ds = form.get(f"ds_{team.id}")
            if dp is not None:
                team.referee_deduction_points = int(dp)
            if ds is not None:
                team.referee_deduction_stockpunkte = int(ds)
            session.add(team)
        session.commit()
        return RedirectResponse(
            url=f"/tournament/{tournament_id}/standings", status_code=303
        )

    @app.get("/tournament/{tournament_id}/standings.xlsx")
    def standings_xlsx(
        tournament_id: int,
        session: Session = Depends(get_session),
    ) -> Response:
        from openpyxl import Workbook

        tournament = session.get(Tournament, tournament_id)
        if tournament is None:
            raise HTTPException(404, "Turnier nicht gefunden")
        standings = compute_standings(session, tournament_id)

        wb = Workbook()
        ws = wb.active
        ws.title = "Siegerliste"
        ws.append([tournament.name])
        ws.append([])
        ws.append(["Rang", "Mannschaft", "Spieler", "Nation", "Punkte", "Diff.", "Stockpkt."])
        for i, s in enumerate(standings, start=1):
            ws.append([
                i,
                s.team_name,
                ", ".join(s.players),
                s.nation,
                f"{s.adjusted_points_won} : {s.game_points_against}",
                s.stockpunkte_diff,
                f"{s.stockpunkte_for} : {s.stockpunkte_against}",
            ])

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)
        return Response(
            content=buf.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f'attachment; filename="siegerliste-{tournament_id}.xlsx"'
            },
        )

    return app


app = make_app()

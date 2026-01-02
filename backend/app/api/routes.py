"""HTTP surface. Thin on purpose: parse, delegate, map errors to status codes.

No scoring, no prompt assembly and no persistence decisions live in this file.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status

from ..config import Settings
from ..game.engine import EmptyMessage, GameEngine, GameOver
from ..game.rules import INFLUENCE_THRESHOLD, MAX_TURNS
from ..providers import DoormanProvider, JudgeUnavailable
from ..sessions.store import InvalidSessionId, SessionNotFound, SessionStore
from .dependencies import get_engine, get_provider, get_settings, get_store
from .schemas import (
    Debrief,
    DebriefTurn,
    Health,
    SessionState,
    SessionSummary,
    TurnRequest,
    TurnResponse,
)

router = APIRouter()


def _load(store: SessionStore, session_id: str):
    try:
        return store.get(session_id)
    except InvalidSessionId as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "malformed session id") from exc
    except SessionNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such session") from exc


@router.get("/healthz", response_model=Health, tags=["ops"])
def healthz(provider: DoormanProvider = Depends(get_provider)) -> Health:
    """Liveness plus the two facts a reviewer wants: which brain, and is it offline."""
    return Health(
        status="ok",
        provider=provider.name,
        offline=provider.offline,
        threshold=INFLUENCE_THRESHOLD,
        max_turns=MAX_TURNS,
    )


@router.post("/api/sessions", response_model=SessionState, status_code=status.HTTP_201_CREATED, tags=["game"])
def create_session(
    store: SessionStore = Depends(get_store),
) -> SessionState:
    """Start a run. The id is issued here, never chosen by the client."""
    return SessionState.from_session(store.create(), INFLUENCE_THRESHOLD)


@router.get("/api/sessions/{session_id}", response_model=SessionState, tags=["game"])
def read_session(
    session_id: str,
    store: SessionStore = Depends(get_store),
) -> SessionState:
    """Read a run. Unknown ids 404 rather than being created on the spot."""
    return SessionState.from_session(_load(store, session_id), INFLUENCE_THRESHOLD)


@router.delete("/api/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["game"])
def delete_session(
    session_id: str,
    store: SessionStore = Depends(get_store),
) -> None:
    """Abandon a run."""
    try:
        store.delete(session_id)
    except InvalidSessionId as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "malformed session id") from exc


@router.post("/api/sessions/{session_id}/turns", response_model=TurnResponse, tags=["game"])
def play_turn(
    session_id: str,
    body: TurnRequest,
    engine: GameEngine = Depends(get_engine),
    store: SessionStore = Depends(get_store),
) -> TurnResponse:
    """Speak one line to Marcus and find out what it cost you."""
    session = _load(store, session_id)
    try:
        result = engine.play_turn(session, body.message)
    except EmptyMessage as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "message cannot be empty") from exc
    except GameOver as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"this run already ended ({exc.status.value})",
        ) from exc
    except JudgeUnavailable as exc:
        # The turn is deliberately *not* consumed. Scoring it zero and moving
        # on is how a stalled model used to produce an unwinnable run.
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "the judge could not score that turn — nothing was charged, try again",
        ) from exc

    return TurnResponse(
        reply=result.turn.doorman_reply,
        score_delta=result.turn.score_delta,
        cumulative_score=session.cumulative_score,
        threshold=INFLUENCE_THRESHOLD,
        status=session.status,
        turns_used=session.turns_used,
        turns_remaining=session.turns_remaining,
        injection_blocked=result.injection_blocked,
        audio_base64=result.audio_base64,
    )


@router.get("/api/sessions/{session_id}/debrief", response_model=Debrief, tags=["game"])
def debrief(
    session_id: str,
    store: SessionStore = Depends(get_store),
) -> Debrief:
    """Reveal the hidden judge's per-turn reasoning, once the run is over."""
    session = _load(store, session_id)
    if not session.status.is_terminal:
        raise HTTPException(status.HTTP_409_CONFLICT, "the run is still in progress")

    turns = [
        DebriefTurn(
            index=turn.index,
            player_message=turn.player_message,
            doorman_reply=turn.doorman_reply,
            score_delta=turn.score_delta,
            tactic=turn.tactic,
            reasoning=turn.reasoning,
        )
        for turn in session.turns
    ]
    best = max(turns, key=lambda t: t.score_delta).index if turns else None
    worst = min(turns, key=lambda t: t.score_delta).index if turns else None

    return Debrief(
        session_id=session.session_id,
        status=session.status,
        cumulative_score=session.cumulative_score,
        threshold=INFLUENCE_THRESHOLD,
        turns_used=session.turns_used,
        best_turn=best,
        worst_turn=worst,
        turns=turns,
    )


@router.get("/api/admin/sessions", response_model=list[SessionSummary], tags=["ops"])
def list_sessions(
    x_admin_token: str | None = Header(default=None),
    store: SessionStore = Depends(get_store),
    settings: Settings = Depends(get_settings),
) -> list[SessionSummary]:
    """Every stored run. Disabled unless ``DOORMAN_ADMIN_TOKEN`` is set."""
    if not settings.admin_token:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "admin endpoints are disabled")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid admin token")
    return [SessionSummary(**row) for row in store.list_summaries()]

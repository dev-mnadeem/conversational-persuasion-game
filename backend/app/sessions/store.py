"""Session persistence behind a narrow port.

Two adapters ship: an in-memory store the tests use, and a JSON-file store the
dev server uses so a run survives a reload. Both implement
:class:`SessionStore`, so swapping in Redis or Postgres later is a new class,
not a rewrite of the engine.
"""

from __future__ import annotations

import json
import os
import re
import secrets
from abc import ABC, abstractmethod
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

from .models import Session

#: Ids are issued by :func:`new_session_id` and validated on the way back in,
#: so a session id can never widen into a filesystem path.
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{8,64}$")

SESSION_ID_BYTES = 16


class InvalidSessionId(ValueError):
    """Raised when a caller supplies an id that was not issued by the server."""


class SessionNotFound(LookupError):
    """Raised when a session id is well formed but unknown."""


def new_session_id() -> str:
    """Issue an unguessable session id."""
    return secrets.token_urlsafe(SESSION_ID_BYTES)


def validate_session_id(session_id: str) -> str:
    """Return ``session_id`` if it matches the issued-id shape, else raise.

    Rejecting is deliberately different from the old behaviour of stripping
    unsafe characters: stripping let ``a/b`` and ``ab`` collide onto the same
    stored run.
    """
    if not SESSION_ID_PATTERN.fullmatch(session_id or ""):
        raise InvalidSessionId(session_id)
    return session_id


class SessionStore(ABC):
    """Port for reading and writing runs."""

    @abstractmethod
    def create(self) -> Session:
        """Issue a new id and persist an empty run."""

    @abstractmethod
    def get(self, session_id: str) -> Session:
        """Load a run. Raises :class:`SessionNotFound` if it does not exist."""

    @abstractmethod
    def save(self, session: Session) -> None:
        """Persist the current state of a run."""

    @abstractmethod
    def delete(self, session_id: str) -> None:
        """Remove a run. Deleting an unknown run is not an error."""

    @abstractmethod
    def list_summaries(self) -> list[dict]:
        """Return one summary row per stored run, for the admin endpoint."""

    def replace(self, session_id: str) -> Session:
        """Delete a run and issue a fresh one — the 'play again' path."""
        self.delete(session_id)
        return self.create()


class InMemorySessionStore(SessionStore):
    """Non-durable store. Used by the tests and by stateless deployments."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        session = Session(session_id=new_session_id())
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session:
        validate_session_id(session_id)
        try:
            return self._sessions[session_id]
        except KeyError as exc:
            raise SessionNotFound(session_id) from exc

    def save(self, session: Session) -> None:
        session.touch()
        self._sessions[session.session_id] = session

    def delete(self, session_id: str) -> None:
        validate_session_id(session_id)
        self._sessions.pop(session_id, None)

    def list_summaries(self) -> list[dict]:
        return [_summarise(session) for session in self._sessions.values()]


class JsonFileSessionStore(SessionStore):
    """One JSON file per run, with a bounded in-process read cache.

    Writes go through a temporary file and :func:`os.replace` so a crash
    mid-write cannot leave a half-written run on disk — the previous
    implementation wrote in place and a truncated file silently reset a run.
    """

    def __init__(self, directory: Path, cache_size: int = 256) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: OrderedDict[str, Session] = OrderedDict()
        self._cache_size = max(1, cache_size)

    def _path(self, session_id: str) -> Path:
        return self._dir / f"{validate_session_id(session_id)}.json"

    def _remember(self, session: Session) -> None:
        self._cache[session.session_id] = session
        self._cache.move_to_end(session.session_id)
        while len(self._cache) > self._cache_size:
            self._cache.popitem(last=False)

    def create(self) -> Session:
        session = Session(session_id=new_session_id())
        self.save(session)
        return session

    def get(self, session_id: str) -> Session:
        validate_session_id(session_id)
        cached = self._cache.get(session_id)
        if cached is not None:
            self._cache.move_to_end(session_id)
            return cached

        path = self._path(session_id)
        if not path.exists():
            raise SessionNotFound(session_id)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            session = Session.from_dict(raw)
        except (json.JSONDecodeError, KeyError, ValueError, OSError) as exc:
            raise SessionNotFound(session_id) from exc

        self._remember(session)
        return session

    def save(self, session: Session) -> None:
        session.touch()
        path = self._path(session.session_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(session.to_dict(), indent=2), encoding="utf-8")
        os.replace(tmp, path)
        self._remember(session)

    def delete(self, session_id: str) -> None:
        self._cache.pop(validate_session_id(session_id), None)
        self._path(session_id).unlink(missing_ok=True)

    def list_summaries(self) -> list[dict]:
        summaries = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                summaries.append(_summarise(Session.from_dict(json.loads(path.read_text(encoding="utf-8")))))
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                continue
        return summaries

    def purge_older_than(self, max_age_hours: int) -> int:
        """Delete runs untouched for ``max_age_hours``. Returns the count."""
        cutoff = datetime.now(timezone.utc)
        deleted = 0
        for path in list(self._dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                updated = datetime.fromisoformat(raw.get("updated_at", raw["created_at"]))
            except (json.JSONDecodeError, KeyError, ValueError, OSError):
                continue
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if (cutoff - updated).total_seconds() / 3600 > max_age_hours:
                path.unlink(missing_ok=True)
                self._cache.pop(path.stem, None)
                deleted += 1
        return deleted


def _summarise(session: Session) -> dict:
    return {
        "session_id": session.session_id,
        "cumulative_score": session.cumulative_score,
        "turns_used": session.turns_used,
        "status": session.status.value,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }

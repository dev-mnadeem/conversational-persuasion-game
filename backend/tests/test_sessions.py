"""Session identity and persistence."""

import json

import pytest

from app.game.rules import MAX_TURNS, GameStatus
from app.sessions.models import Session, Turn
from app.sessions.store import (
    InMemorySessionStore,
    InvalidSessionId,
    JsonFileSessionStore,
    SessionNotFound,
    new_session_id,
    validate_session_id,
)

STORES = ["memory", "file"]


@pytest.fixture(params=STORES)
def any_store(request, tmp_path):
    if request.param == "memory":
        return InMemorySessionStore()
    return JsonFileSessionStore(tmp_path, cache_size=4)


def test_issued_ids_are_unguessable_and_unique():
    ids = {new_session_id() for _ in range(200)}
    assert len(ids) == 200
    assert all(len(value) >= 16 for value in ids)


@pytest.mark.parametrize("bad", ["", "..", "../../etc/passwd", "a/b", "short", "x" * 100, "has space"])
def test_ids_outside_the_issued_shape_are_rejected(bad):
    """Rejecting beats sanitising: stripping let 'a/b' and 'ab' collide."""
    with pytest.raises(InvalidSessionId):
        validate_session_id(bad)


def test_an_issued_id_validates():
    value = new_session_id()
    assert validate_session_id(value) == value


def test_unknown_sessions_are_not_created_on_read(any_store):
    """A GET used to create a run, so anyone could fill the disk with them."""
    with pytest.raises(SessionNotFound):
        any_store.get(new_session_id())


def test_create_then_read_round_trips(any_store):
    created = any_store.create()
    assert any_store.get(created.session_id).session_id == created.session_id


def test_saved_state_survives_a_reload(any_store):
    session = any_store.create()
    session.cumulative_score = 42
    session.turns_used = 3
    session.status = GameStatus.IN_PROGRESS
    session.turns.append(
        Turn(
            index=1,
            player_message="hi",
            doorman_reply="hm",
            score_delta=6,
            reasoning="r",
            tactic="politeness",
        )
    )
    any_store.save(session)

    loaded = any_store.get(session.session_id)
    assert loaded.cumulative_score == 42
    assert loaded.turns[0].tactic == "politeness"


def test_delete_removes_the_run(any_store):
    session = any_store.create()
    any_store.delete(session.session_id)
    with pytest.raises(SessionNotFound):
        any_store.get(session.session_id)


def test_deleting_an_unknown_run_is_not_an_error(any_store):
    any_store.delete(new_session_id())


def test_replace_issues_a_fresh_id(any_store):
    first = any_store.create()
    second = any_store.replace(first.session_id)
    assert second.session_id != first.session_id
    assert second.cumulative_score == 0


def test_summaries_cover_every_stored_run(any_store):
    ids = {any_store.create().session_id for _ in range(3)}
    assert {row["session_id"] for row in any_store.list_summaries()} == ids


def test_file_store_survives_a_cold_process(tmp_path):
    first = JsonFileSessionStore(tmp_path)
    session = first.create()
    session.cumulative_score = 55
    first.save(session)

    second = JsonFileSessionStore(tmp_path)
    assert second.get(session.session_id).cumulative_score == 55


def test_file_store_evicts_beyond_the_cache_bound(tmp_path):
    store = JsonFileSessionStore(tmp_path, cache_size=2)
    sessions = [store.create() for _ in range(5)]
    assert len(store._cache) == 2
    assert store.get(sessions[0].session_id).session_id == sessions[0].session_id


def test_a_corrupt_file_reads_as_missing_rather_than_crashing(tmp_path):
    store = JsonFileSessionStore(tmp_path)
    session = store.create()
    store._cache.clear()
    (tmp_path / f"{session.session_id}.json").write_text("{not json")
    with pytest.raises(SessionNotFound):
        store.get(session.session_id)


def test_writes_leave_no_temporary_files_behind(tmp_path):
    store = JsonFileSessionStore(tmp_path)
    store.save(store.create())
    assert not list(tmp_path.glob("*.tmp"))
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_stored_json_is_readable_by_hand(tmp_path):
    store = JsonFileSessionStore(tmp_path)
    session = store.create()
    raw = json.loads((tmp_path / f"{session.session_id}.json").read_text())
    assert raw["status"] == GameStatus.IN_PROGRESS.value


def test_purge_removes_only_stale_runs(tmp_path):
    store = JsonFileSessionStore(tmp_path)
    fresh = store.create()
    stale = store.create()
    stale.updated_at = "2020-01-01T00:00:00+00:00"
    path = tmp_path / f"{stale.session_id}.json"
    path.write_text(json.dumps(stale.to_dict()))

    assert store.purge_older_than(max_age_hours=24) == 1
    assert store.get(fresh.session_id)
    with pytest.raises(SessionNotFound):
        store.get(stale.session_id)


def test_turns_remaining_tracks_the_budget():
    session = Session(session_id=new_session_id())
    assert session.turns_remaining == MAX_TURNS
    session.turns_used = MAX_TURNS + 3
    assert session.turns_remaining == 0


def test_session_round_trips_through_a_dict():
    session = Session(session_id=new_session_id(), cumulative_score=17, turns_used=2)
    session.turns.append(
        Turn(index=1, player_message="p", doorman_reply="d", score_delta=9, reasoning="r", tactic="music")
    )
    restored = Session.from_dict(session.to_dict())
    assert restored.to_dict() == session.to_dict()

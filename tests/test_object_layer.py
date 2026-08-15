"""Tests for the Gotham-lite object layer: investigation provenance + alert
lifecycle workflow (scores immutable; state is operational bookkeeping)."""
from __future__ import annotations

import pytest

import src.object_layer as ol


def test_fsm_transitions_are_sound() -> None:
    assert ol.ALERT_STATUSES == ("OPEN", "ACKNOWLEDGED", "RESOLVED", "SUPPRESSED")
    # RESOLVED cannot jump straight back to ACKNOWLEDGED.
    assert "ACKNOWLEDGED" not in ol._STATUS_TRANSITIONS["RESOLVED"]
    assert ol._STATUS_TRANSITIONS["RESOLVED"] == {"OPEN"}
    # Every declared status is a valid key in the FSM.
    for status in ol.ALERT_STATUSES:
        assert status in ol._STATUS_TRANSITIONS


def test_alert_state_transition_and_audit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ol, "ALERT_STATE_PATH", tmp_path / "alert_state.json")
    monkeypatch.setattr(ol, "ACTIONS_PATH", tmp_path / "actions.jsonl")

    rec = ol.update_alert_state(40258, "ACKNOWLEDGED", operator="tester", note="triaged")
    assert rec["status"] == "ACKNOWLEDGED"
    assert rec["previous_status"] == "OPEN"
    assert ol.get_alert_state(40258)["status"] == "ACKNOWLEDGED"

    # Valid: ACK -> SUPPRESSED
    ol.update_alert_state(40258, "SUPPRESSED")
    assert ol.get_alert_state(40258)["status"] == "SUPPRESSED"

    # Invalid: SUPPRESSED -> RESOLVED must be rejected and state untouched.
    with pytest.raises(ValueError):
        ol.update_alert_state(40258, "RESOLVED")
    assert ol.get_alert_state(40258)["status"] == "SUPPRESSED"


def test_materialize_investigation_includes_provenance() -> None:
    bundle = ol.materialize_investigation({}, {})
    assert bundle["schema"] == "athena.investigation.v1"
    assert "provenance" in bundle
    assert isinstance(bundle["provenance"].get("models"), dict)


def test_action_for_status_is_specific() -> None:
    assert ol.ACTION_FOR_STATUS["ACKNOWLEDGED"] == "AcknowledgeAlert"
    assert ol.ACTION_FOR_STATUS["RESOLVED"] == "ResolveAlert"
    assert ol.ACTION_FOR_STATUS["SUPPRESSED"] == "SuppressAlert"
    assert ol.ACTION_FOR_STATUS["OPEN"] == "OpenCase"


def test_corrupt_alert_state_does_not_reset(tmp_path, monkeypatch) -> None:
    path = tmp_path / "alert_state.json"
    path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(ol, "ALERT_STATE_PATH", path)
    monkeypatch.setattr(ol, "ACTIONS_PATH", tmp_path / "actions.jsonl")
    with pytest.raises(ValueError, match="corrupt"):
        ol.update_alert_state(40258, "ACKNOWLEDGED")
    assert path.read_text(encoding="utf-8") == "{not-json"


def test_resolved_audits_as_resolve_alert(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(ol, "ALERT_STATE_PATH", tmp_path / "alert_state.json")
    monkeypatch.setattr(ol, "ACTIONS_PATH", tmp_path / "actions.jsonl")
    ol.update_alert_state(40258, "ACKNOWLEDGED")
    ol.update_alert_state(40258, "RESOLVED")
    actions = ol.read_actions()
    assert actions[-1]["action"] == "ResolveAlert"


def test_expand_neighbors_two_hops() -> None:
    bundle = {
        "objects": [
            {
                "id": "sat:1",
                "kind": "satellite",
                "gotham_category": "Entity",
                "links": [{"type": "threatens", "target": "sat:2"}],
            },
            {
                "id": "sat:2",
                "kind": "satellite",
                "gotham_category": "Entity",
                "links": [{"type": "hasAlert", "target": "alert:2"}],
            },
            {"id": "alert:2", "kind": "alert", "gotham_category": "Event", "links": []},
        ]
    }
    one = ol.expand_neighbors(bundle, "sat:1", hops=1)
    assert {n["id"] for n in one["nodes"]} == {"sat:1", "sat:2"}
    two = ol.expand_neighbors(bundle, "sat:1", hops=2)
    assert {n["id"] for n in two["nodes"]} == {"sat:1", "sat:2", "alert:2"}

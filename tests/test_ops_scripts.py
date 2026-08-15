from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_cron_job_line_is_not_a_comment() -> None:
    src = (ROOT / "scripts" / "install_daily_cron.sh").read_text(encoding="utf-8")
    # The schedule must stand as its own line; marker is a trailing comment.
    assert "JOB_CMD=" in src
    assert '"$MARKER $JOB_CMD"' not in src
    assert "$MARKER" in src
    assert "CRON_TZ=UTC" in src


def test_daily_ingest_uses_python_sync_and_exits_nonzero() -> None:
    src = (ROOT / "scripts" / "run_daily_ingest.sh").read_text(encoding="utf-8")
    assert "sync_frontend_data.py" in src
    assert "exit 1" in src


def test_continuous_validation_note_not_inverted() -> None:
    src = (ROOT / "scripts" / "run_continuous_validation.py").read_text(encoding="utf-8")
    assert "too strict" in src
    assert "too loose / distribution shifted" not in src


def test_score_latest_materializes_investigation() -> None:
    """run-daily calls score_latest directly (not cmd_score). Investigation
    must be written there or the object graph stays stale."""
    src = (ROOT / "src" / "anomaly_monitor.py").read_text(encoding="utf-8")
    assert "write_investigation" in src
    # The write lives inside score_latest, not only the CLI wrapper.
    score_idx = src.find("def score_latest")
    next_def = src.find("\ndef ", score_idx + 1)
    body = src[score_idx:next_def]
    assert "write_investigation" in body
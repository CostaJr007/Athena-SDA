import pytest

from src.catalog import (
    clear_watchlist_cache,
    get_object,
    remove_watchlist_object,
    upsert_watchlist_object,
)


def test_upsert_and_remove_roundtrip(tmp_path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text('{"version": 1, "objects": []}', encoding="utf-8")
    clear_watchlist_cache()
    obj = upsert_watchlist_object(
        {"norad_id": 99999, "name": "TEST-SAT", "role": "suspect", "country": "US", "orbit_class": "LEO"},
        path=path,
    )
    assert obj["norad_id"] == 99999
    # load from that path
    clear_watchlist_cache()
    assert get_object(99999) is None  # default path is the repo watchlist
    assert remove_watchlist_object(99999, path=path) is True
    assert remove_watchlist_object(99999, path=path) is False


def test_starlink_cannot_be_persisted(tmp_path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text('{"version": 1, "objects": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="Starlink"):
        upsert_watchlist_object(
            {"norad_id": 44713, "name": "STARLINK-1007", "role": "baseline"},
            path=path,
        )

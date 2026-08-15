from src.whatif import run_whatif
from src.utils import generate_mock_tle_history


def test_injected_maneuver_fires_detector() -> None:
    out = run_whatif(9001, delta_km=4.5, num_days=40, allow_mock=True)
    assert out["injected"] is True
    assert out["fired"] is True
    assert out["delta_cusum"] > 0
    assert out["source"] in ("mock", "provided", "history")


def test_whatif_uses_provided_history_not_norad_as_orbit() -> None:
    hist = generate_mock_tle_history(40258, num_days=40, anomaly_type=None)
    hist["semi_major_axis_km"] = 42164.0
    out = run_whatif(40258, delta_km=4.5, hist=hist)
    assert out["source"] == "provided"
    assert out["injected"] is True
    assert out["fired"] is True
    assert out["n_epochs"] == len(hist)

"""Validation: full Bob briefing + app imports."""
from src.models import load_models
from src.pipeline import build_demo_constellation, process_constellation
from src.bob import answer_operator_query, generate_bob_briefing

iforest, xgb, rkhs, _ = load_models()
sats = build_demo_constellation()
out = process_constellation(sats, iforest, xgb, rkhs)
by_id = {p["id"]: p for p in out}

# Full Bob briefing for Yaogan (hostile shadowing)
p = by_id[44231]
meta = sats[44231]["metadata"]
briefing = generate_bob_briefing(
    p["features"],
    {"threat_level": p["threat_level"], "classification": p["classification"],
     "confidence": p["confidence"], "ambiguity": p["ambiguity"]},
    44231, p["min_dist_mil"], sat_metadata=meta,
    ml_context={"xgb_class": p["xgb_class"], "xgb_confidence": p["xgb_confidence"],
                "anomaly_score": p["anomaly_score"]},
)
print("=== FULL BRIEFING (YAOGAN) ===")
print(briefing)
print()

# History tool
print("=== HISTORY TOOL (#2001) ===")
print(answer_operator_query("History for #2001", sats, out, by_id))
print()

# App import check
print("=== APP IMPORT ===", end=" ")
import app  # noqa: F401
print("OK")
print("\n✅ Validation passed")

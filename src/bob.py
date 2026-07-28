"""
Bob copilot — IBM Granite / watsonx.ai

Implements the qualitative stages of a Palantir-style LLM + Geospatial pipeline
(US 2024/0394296 A1):
  1. Filter / context (tools)
  2. Quantitative scores (from ML pipeline)
  3. Descriptive brief (LLM or local template)
  4. Classification + recommendations
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import numpy as np

WATSONX_AVAILABLE = False
try:
    from ibm_watsonx_ai.foundation_models import Model
    from ibm_watsonx_ai import Credentials

    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False

# Backward-compatible alias
WATSONX_DISPONIVEL = WATSONX_AVAILABLE


def get_watsonx_model():
    api_key = os.environ.get("WATSONX_APIKEY")
    project_id = os.environ.get("WATSONX_PROJECT_ID")
    wx_url = os.environ.get("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
    if not WATSONX_AVAILABLE or not api_key or not project_id:
        return None
    try:
        credentials = Credentials(url=wx_url, api_key=api_key)
        parameters = {
            "decoding_method": "greedy",
            "max_new_tokens": 600,
            "min_new_tokens": 40,
            "temperature": 0.0,
        }
        # Prefer newer Granite instruct if available; SDK will error → catch
        for model_id in (
            "ibm/granite-3-8b-instruct",
            "ibm/granite-13b-instruct-v2",
        ):
            try:
                return Model(
                    model_id=model_id,
                    params=parameters,
                    credentials=credentials,
                    project_id=project_id,
                )
            except Exception:
                continue
        return None
    except Exception as e:
        print(f"Failed to initialize watsonx.ai: {e}")
        return None


# ---------------------------------------------------------------------------
# Tool calling stubs (local catalog — same APIs Bob would call in production)
# ---------------------------------------------------------------------------

def tool_get_object_metadata(norad_id: int, catalog: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    sat = catalog.get(norad_id)
    if not sat:
        return {"error": f"NORAD {norad_id} not found in the active catalog."}
    return dict(sat["metadata"])


def tool_get_object_history(norad_id: int, catalog: Dict[int, Dict[str, Any]], days: int = 7) -> Dict[str, Any]:
    sat = catalog.get(norad_id)
    if not sat:
        return {"error": f"NORAD {norad_id} not found."}
    hist = sat["history"]
    tail = hist.tail(max(days, 1))
    return {
        "norad_id": norad_id,
        "n_epochs": len(tail),
        "sma_start": float(tail["semi_major_axis_km"].iloc[0]),
        "sma_end": float(tail["semi_major_axis_km"].iloc[-1]),
        "delta_sma_km": float(tail["semi_major_axis_km"].iloc[-1] - tail["semi_major_axis_km"].iloc[0]),
        "inc_mean": float(tail["inclination_deg"].mean()),
    }


def tool_get_close_approaches(
    norad_id: int,
    processed_by_id: Dict[int, Dict[str, Any]],
    threshold_km: float = 50.0,
) -> Dict[str, Any]:
    row = processed_by_id.get(norad_id)
    if not row:
        return {"error": f"NORAD {norad_id} has no analysis yet."}
    return {
        "norad_id": norad_id,
        "min_distance_to_military_km": row.get("min_dist_mil"),
        "closest_asset": row.get("closest_asset_name"),
        "within_threshold": float(row.get("min_dist_mil", 999)) < threshold_km,
        "cointegration_pvalue": row.get("cointegration_pvalue"),
    }


def tool_get_space_weather() -> Dict[str, Any]:
    """Live/historical space weather from local GFZ store (F10.7, Ap, Kp)."""
    try:
        from src.space_weather import lookup_space_weather, status as sw_status

        sw = lookup_space_weather(None)
        st = sw_status()
        f107 = float(sw.get("f10_7", 120))
        ap = float(sw.get("ap_index", 10))
        if ap >= 50 or f107 >= 200:
            note = "High solar/geomagnetic activity — elevated LEO drag (watch for false-positive maneuver flags)."
        elif ap >= 20 or f107 >= 150:
            note = "Moderate activity; station-keeping and natural drag remain plausible."
        else:
            note = "Relatively quiet conditions."
        rng = st.get("range") or []
        return {
            "source": "gfz_kp_f107",
            "f10_7": f107,
            "f10_7_adj": float(sw.get("f10_7_adj", f107)),
            "ap_index": ap,
            "kp": float(sw.get("kp_mean", 2)),
            "f10_7_delta_7d": float(sw.get("f10_7_delta_7d", 0)),
            "ap_max_7d": float(sw.get("ap_max_7d", ap)),
            "geomagnetic_storm": float(sw.get("geomagnetic_storm", 0)),
            "store_days": st.get("n_days"),
            "store_range": f"{rng[0] if rng else '?'} → {rng[1] if len(rng)>1 else '?'}",
            "note": note,
        }
    except Exception as e:
        return {
            "source": "fallback",
            "f10_7": 120.0,
            "ap_index": 10,
            "kp": 2,
            "note": f"Space weather unavailable ({e}); using quiet defaults.",
        }


def tool_list_alerts(processed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    alerts = [p for p in processed if p["classification"] != "NORMAL"]
    alerts.sort(key=lambda x: x.get("kelly_allocation", 0), reverse=True)
    return [
        {
            "id": a["id"],
            "name": a["name"],
            "classification": a["classification"],
            "threat_level": a["threat_level"],
            "kelly": a["kelly_allocation"],
            "min_dist_mil": a.get("min_dist_mil"),
        }
        for a in alerts
    ]


def generate_bob_briefing(
    features: Dict[str, float],
    fuzzy_result: Dict[str, Any],
    norad_id: int,
    min_dist_mil: float,
    sat_metadata: Optional[Dict[str, Any]] = None,
    ml_context: Optional[Dict[str, Any]] = None,
) -> str:
    """Stage 3–4: qualitative brief from quantitative state."""
    if sat_metadata is None:
        sat_metadata = {
            "name": f"OBJ-{norad_id}",
            "country": "Unknown",
            "purpose": "Military / Reconnaissance" if min_dist_mil < 50 else "Commercial",
        }

    threat_level = float(fuzzy_result.get("threat_level", 0))
    classification = fuzzy_result.get("classification", "NORMAL")
    confidence = float(fuzzy_result.get("confidence", 0))
    ambiguity = float(fuzzy_result.get("ambiguity", 1 - confidence))

    shannon = features.get("shannon_entropy_sma_30d", 0.0)
    kolmogorov = features.get("kolmogorov_proxy_7d", 0.0)
    hurst = features.get("hurst_exponent_sma", 0.5)
    adf = features.get("adf_pvalue", 0.0)
    l1_cusum = features.get("l1_cusum_sma", 0.0)
    delta_sma = features.get("delta_sma_7d_km", 0.0)
    tle_age = features.get("tle_age_hours", 12.0)
    coint = features.get("cointegration_pvalue", 1.0)
    ricci = features.get("ricci_mean", 0.0)
    rkhs = features.get("spectral_anomaly_rkhs", 0.0)

    xgb_line = ""
    if ml_context:
        xgb_line = (
            f"- XGBoost: {ml_context.get('xgb_class', '?')} "
            f"(conf {float(ml_context.get('xgb_confidence', 0))*100:.1f}%) | "
            f"anomaly_score={float(ml_context.get('anomaly_score', 0)):.3f}\n"
        )

    prompt = f"""[ATHENA-SDA SYSTEM — SPACE DOMAIN AWARENESS]
You are BOB, a senior SDA analyst. Produce a tactical briefing in English.

METADATA:
- NORAD #{norad_id} | {sat_metadata.get('name')} | {sat_metadata.get('country')} | {sat_metadata.get('purpose')}

QUANTITATIVE:
- Distance to protected military asset: {min_dist_mil:.2f} km
- ΔSMA 7d: {delta_sma:.4f} km | TLE age: {tle_age:.1f}h
- Shannon: {shannon:.2f} | Kolmogorov: {kolmogorov:.2f} | Hurst: {hurst:.2f}
- ADF p: {adf:.4f} | CUSUM L1: {l1_cusum:.2f} | Cointegration p: {coint:.4f}
- Ricci: {ricci:.3f} | RKHS anomaly: {rkhs:.3f}
{xgb_line}- Fuzzy: {classification} | threat={threat_level:.2f} | conf={confidence*100:.1f}%

INSTRUCTIONS:
1. Header with classification and confidence.
2. Justify with physics/math (Hurst, Kolmogorov, CUSUM, cointegration).
3. Assess RPO / conjunction box (~10 km).
4. List 3 prioritized tactical actions.
5. Formal military tone. English only.

BRIEFING:"""

    model = get_watsonx_model()
    if model is not None:
        try:
            response = model.generate(prompt=prompt)
            text = response["results"][0]["generated_text"]
            return text.strip()
        except Exception as e:
            print(f"watsonx inference error: {e}")

    return _local_briefing(
        sat_metadata, norad_id, classification, threat_level, confidence, ambiguity,
        hurst, kolmogorov, adf, l1_cusum, delta_sma, tle_age, min_dist_mil, coint,
        ricci, rkhs, ml_context,
    )


def _local_briefing(
    sat_metadata, norad_id, classification, threat_level, confidence, ambiguity,
    hurst, kolmogorov, adf, l1_cusum, delta_sma, tle_age, min_dist_mil, coint,
    ricci, rkhs, ml_context,
) -> str:
    xgb_bit = ""
    if ml_context:
        xgb_bit = (
            f"- XGBoost layer: **{ml_context.get('xgb_class')}** "
            f"(confidence {float(ml_context.get('xgb_confidence', 0))*100:.0f}%), "
            f"anomaly_score={float(ml_context.get('anomaly_score', 0)):.2f}\n"
        )

    shadow = ""
    if coint < 0.05:
        shadow = (
            f"- **Shadowing / cointegration:** p-value={coint:.4f} < 0.05 — altitude series "
            f"cointegrated with a high-value asset (escort / pursuit pattern).\n"
        )

    body = f"""SDA BRIEFING — ATHENA
OBJECT: {sat_metadata.get('name')} (#{norad_id}) | ORIGIN: {sat_metadata.get('country')}
CLASSIFICATION: **{classification}** (risk {threat_level:.2f}) | CONFIDENCE: {confidence*100:.1f}% | AMBIGUITY: {ambiguity*100:.1f}%

QUANTITATIVE ANALYSIS:
{xgb_bit}- **Hurst H={hurst:.2f}:** {"active propulsion persistence (low thrust)" if hurst > 0.55 else "near-noise / mean-reverting behavior"}.
- **Kolmogorov K={kolmogorov:.2f}:** {"high-complexity trajectory (active control)" if kolmogorov > 0.5 else "compressible / Keplerian dynamics"}.
- **ADF p={adf:.4f} | CUSUM L1={l1_cusum:.2f}:** structural break {"detected" if (adf > 0.05 or l1_cusum > 0.5) else "not dominant"}.
- **ΔSMA 7d = {delta_sma:.4f} km** | TLE age **{tle_age:.1f} h**
- **Military proximity: {min_dist_mil:.2f} km** | Ricci≈{ricci:.2f} | RKHS≈{rkhs:.2f}
{shadow}
"""

    if classification in ("HOSTILE", "HOSTIL"):
        actions = """RECOMMENDED ACTIONS (High Kelly Priority):
1. Notify SDA cell / Space Command and log emergency conjunction notice.
2. Optical/radar sensor tasking on next overpass; verify payload status.
3. Prepare evasive maneuver plan if distance < conjunction threshold (10 km).
4. Generate formal intelligence report for space threat catalog."""
    elif classification in ("SUSPECT", "SUSPEITO"):
        actions = """RECOMMENDED ACTIONS:
1. Add to 24h high-priority watchlist with 25–50 km threshold.
2. Increase TLE ingest frequency (Space-Track / CelesTrak).
3. Monitor cointegration and Hurst exponent across next 6 orbits.
4. Provide partial briefing to command if distance drops below 25 km."""
    elif classification in ("ANOMALOUS", "ANÔMALO", "ANOMALO"):
        actions = """RECOMMENDED ACTIONS:
1. Maintain passive tracking; correlate with space weather (F10.7/Ap indices).
2. Await fresh TLE if data age > 48h (elevated uncertainty).
3. Reprocess feature metrics upon next catalog update."""
    else:
        actions = """RECOMMENDED ACTIONS:
1. Maintain standard catalog sweep.
2. Behavior consistent with normal station-keeping or natural atmospheric decay."""

    return (body + "\n" + actions).strip()


def answer_operator_query(
    user_input: str,
    catalog: Dict[int, Dict[str, Any]],
    processed: List[Dict[str, Any]],
    processed_by_id: Dict[int, Dict[str, Any]],
) -> str:
    """
    Lightweight intent router for Bob chat:
    - briefing by NORAD
    - list alerts
    - space weather
    - history / approaches tools
    """
    text = user_input.strip()
    low = text.lower()

    # Intent: list alerts / status (EN + legacy PT keywords)
    if any(k in low for k in (
        "alerta", "alertas", "status", "resumo", "overview", "hostil", "suspeito",
        "alert", "alerts", "threat", "threats", "summary",
    )):
        alerts = tool_list_alerts(processed)
        if not alerts:
            return "No active threat alerts at this time. Catalog within normal baseline."
        lines = ["**Active Threat Alerts (Ordered by Kelly Priority):**"]
        for a in alerts:
            lines.append(
                f"- #{a['id']} {a['name']}: **{a['classification']}** | "
                f"threat {a['threat_level']:.2f} | Kelly {a['kelly']*100:.0f}% | "
                f"military dist. {a['min_dist_mil']:.1f} km"
            )
        weather = tool_get_space_weather()
        lines.append(
            f"\nSpace weather: F10.7={weather['f10_7']}, Ap={weather['ap_index']}. {weather['note']}"
        )
        return "\n".join(lines)

    if any(k in low for k in ("clima", "space weather", "f10", "arrasto", "weather", "drag")):
        w = tool_get_space_weather()
        return (
            f"**Space weather:** F10.7={w['f10_7']}, Ap={w['ap_index']}, Kp={w['kp']}.\n"
            f"{w['note']}"
        )

    # Extract NORAD id
    norad_id = None
    for word in re.findall(r"#?(\d{3,6})", text):
        candidate = int(word)
        if candidate in catalog or candidate in processed_by_id:
            norad_id = candidate
            break

    if norad_id is None:
        # Try match by name fragment
        for sid, sat in catalog.items():
            name = sat["metadata"]["name"].lower()
            if name.split()[0].lower() in low or any(
                part.lower() in low for part in name.replace("(", " ").replace(")", " ").split() if len(part) > 3
            ):
                norad_id = sid
                break

    if norad_id is None:
        ids = ", ".join(f"#{k}" for k in sorted(catalog.keys())[:12])
        return (
            "I could not identify the object. Examples:\n"
            "- `Briefing for #44231`\n"
            "- `Active alerts?`\n"
            "- `History for #2001`\n"
            f"Catalog IDs: {ids}..."
        )

    # History intent
    if any(k in low for k in (
        "históric", "historico", "history", "trajetória", "trajetoria", "trajectory",
        "sma", "últimos dias", "ultimos dias", "last days",
    )):
        h = tool_get_object_history(norad_id, catalog, days=14)
        if "error" in h:
            return h["error"]
        return (
            f"**Orbital history #{norad_id}** (recent window):\n"
            f"- Epochs: {h['n_epochs']}\n"
            f"- SMA: {h['sma_start']:.3f} → {h['sma_end']:.3f} km (Δ {h['delta_sma_km']:+.4f} km)\n"
            f"- Mean inclination: {h['inc_mean']:.3f}°"
        )

    # Approaches intent
    if any(k in low for k in (
        "aproxima", "approach", "approaches", "distância", "distancia", "distance",
        "rpo", "conjun", "proximity",
    )):
        ca = tool_get_close_approaches(norad_id, processed_by_id)
        if "error" in ca:
            return ca["error"]
        return (
            f"**Approaches #{norad_id}:**\n"
            f"- Min distance to military asset: **{ca['min_distance_to_military_km']:.2f} km**\n"
            f"- Closest asset: {ca['closest_asset']}\n"
            f"- Within 50 km: {'YES' if ca['within_threshold'] else 'no'}\n"
            f"- Cointegration p-value: {ca['cointegration_pvalue']}"
        )

    # Default: full briefing
    row = processed_by_id.get(norad_id)
    if row is None:
        return f"Object #{norad_id} is in the catalog but has no processed score yet."

    meta = catalog[norad_id]["metadata"] if norad_id in catalog else {
        "name": row["name"], "country": row["country"], "purpose": row["purpose"],
    }
    return generate_bob_briefing(
        row["features"],
        {
            "threat_level": row["threat_level"],
            "classification": row["classification"],
            "confidence": row["confidence"],
            "ambiguity": row["ambiguity"],
        },
        norad_id,
        row["min_dist_mil"],
        sat_metadata=meta,
        ml_context={
            "xgb_class": row.get("xgb_class"),
            "xgb_confidence": row.get("xgb_confidence"),
            "anomaly_score": row.get("anomaly_score"),
        },
    )

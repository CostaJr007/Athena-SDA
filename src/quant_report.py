"""
Athena-SDA — Quant report (HTML) for HOSTILE / SUSPECT / ANOMALY / NOMINAL labels.
Top: plain-language summary. Below: mathematical foundation and numbers.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.tle_store import ALERTS_DIR, ensure_dirs

REPORTS_DIR = ALERTS_DIR / "reports"
PUBLIC_REPORTS = Path(__file__).resolve().parent / "frontend" / "public" / "reports"


def _esc(x: Any) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def _f(x: Any, nd: int = 3) -> str:
    try:
        if x is None:
            return "—"
        return f"{float(x):.{nd}f}"
    except (TypeError, ValueError):
        return "—"


def _ui_threat(entry: Dict[str, Any]) -> str:
    """Same rules as Mission board (frontend boardThreat)."""
    status = str(entry.get("status") or "")
    pair = entry.get("pair") or {}
    pair_level = str(pair.get("risk_level") or "").upper()
    pair_risk = float(pair.get("pair_risk") or 0)
    att = float(entry.get("attention_score") or entry.get("anomaly_score") or 0)
    is_anom = bool(entry.get("is_anomaly"))

    if status == "PAIR_ELEVATED" and (
        pair_level == "CRITICAL" or att >= 0.65 or pair_risk >= 0.9
    ):
        return "HOSTILE"
    if status == "PAIR_ELEVATED" or pair_risk >= 0.55:
        return "SUSPECT"
    if is_anom or status == "ANOMALY":
        return "ANOMALY"
    if status == "UNRELIABLE_DATA":
        return "ANOMALY"
    return "NOMINAL"


def _threat_color(tier: str) -> str:
    return {
        "HOSTILE": "#fb7185",
        "SUSPECT": "#fbbf24",
        "ANOMALY": "#fb923c",
        "NOMINAL": "#34d399",
    }.get(tier, "#a1a1aa")


def _feature_rows(fs: Dict[str, Any]) -> List[Dict[str, str]]:
    specs = [
        (
            "dfa_hurst_sma",
            "DFA exponent α",
            "Drag-detrended fluctuation scaling. α>0.5: persistent drift/low thrust; α≈0.5: noise; α<0.5: mean reversion.",
        ),
        (
            "shannon_entropy_sma_30d",
            "Shannon entropy H(Δa)",
            "Disorder in altitude change (~30 days). High: irregular orbit / active control.",
        ),
        (
            "lz76_complexity",
            "LZ76 complexity",
            "Lempel-Ziv complexity of the up/down pattern (Kaspar-Schuster). Active control patterns are less regular.",
        ),
        (
            "page_cusum_sma",
            "Page CUSUM",
            "ARL-calibrated cumulative deviation — sees when the series left its prior regime.",
        ),
        (
            "permutation_entropy",
            "Permutation entropy",
            "Rank-order complexity (Bandt-Pompe), robust for short noisy TLE windows.",
        ),
        (
            "delta_sma_7d_km",
            "Δ altitude 7d (km)",
            "How mean altitude changed over the last week (burn, drag, or station-keeping).",
        ),
        (
            "min_distance_to_military_km",
            "Distance to asset (km)",
            "How close the object gets to a protected watchlist asset.",
        ),
        (
            "cointegration_pvalue",
            "Cointegration (p-value)",
            "Low p: the two orbits move together long-term (statistical shadowing).",
        ),
        (
            "f10_7",
            "F10.7",
            "Solar activity — drives thermosphere density and LEO drag.",
        ),
        (
            "ap_index",
            "Ap",
            "Geomagnetic activity. Storms can change altitude without a burn.",
        ),
        (
            "geomagnetic_storm",
            "Storm Flag",
            "1 = stormy climate — cross-check with Δ altitude before calling a burn.",
        ),
        (
            "tle_age_hours",
            "TLE Age (hours)",
            "How fresh the data is. Stale TLE lowers confidence; it does not prove a threat.",
        ),
    ]
    rows = []
    for key, title, meaning in specs:
        val = fs.get(key)
        rows.append(
            {
                "key": key,
                "title": title,
                "value": _f(val, 4) if val is not None else "—",
                "meaning": meaning,
            }
        )
    return rows


def _plain_summary(entry: Dict[str, Any], tier: str) -> Dict[str, Any]:
    anom = float(entry.get("anomaly_score") or 0)
    att = float(entry.get("attention_score") or anom)
    pair = entry.get("pair") or {}
    fs = entry.get("features_snapshot") or {}
    onset = entry.get("anomaly_onset") or {}
    dq = entry.get("data_quality") or {}
    role = str(entry.get("role") or "—")
    name = str(entry.get("object_name") or "object")

    if tier == "HOSTILE":
        headline = (
            f"<strong>{_esc(name)}</strong> is labeled <strong>HOSTILE</strong> "
            "because the system sees <strong>high risk relative to a protected asset</strong> "
            "(close approach and/or a “stuck” trajectory) and elevated attention priority."
        )
    elif tier == "SUSPECT":
        headline = (
            f"<strong>{_esc(name)}</strong> is labeled <strong>SUSPECT</strong> "
            "because there is <strong>an elevated pair with an asset</strong> (proximity or orbital shadowing), "
            "but not yet at maximum priority."
        )
    elif tier == "ANOMALY":
        headline = (
            f"<strong>{_esc(name)}</strong> is labeled <strong>ANOMALY</strong> "
            "because the <strong>object’s own orbit behavior</strong> left the pattern "
            "learned from that satellite’s history (or the data is low-confidence)."
        )
    else:
        headline = (
            f"<strong>{_esc(name)}</strong> is <strong>NOMINAL</strong>: "
            "there is no strong pair alert or orbit deviation above the "
            "Mission board threshold."
        )

    points: List[str] = []
    points.append(
        "Athena looks at <strong>two things</strong>: "
        f"(1) this object’s <strong>orbital series</strong> vs its own past "
        f"(anomaly = <strong>{anom:.2f}</strong>); "
        f"(2) whether it approaches or “tracks” a <strong>protected asset</strong> "
        f"(attention = <strong>{att:.2f}</strong>)."
    )

    if pair:
        points.append(
            f"Relative to <strong>{_esc(pair.get('asset_name'))}</strong> "
            f"(#{_esc(pair.get('asset_norad'))}): distance ≈ "
            f"<strong>{_esc(_f(pair.get('min_distance_km'), 1))} km</strong>, "
            f"pair risk = <strong>{_esc(_f(pair.get('pair_risk')))}</strong> "
            f"({_esc(pair.get('risk_level'))}). "
            "That weighs more in priority than orbital noise alone."
        )
    else:
        points.append(
            f"Watchlist role: <strong>{_esc(role)}</strong>. "
            "No suspect×asset pair is highlighted in this score — "
            "the main read is the object’s own series behavior."
        )

    if onset.get("first_elevated_at"):
        points.append(
            f"Series noise appears <strong>elevated since about "
            f"{_esc(str(onset.get('first_elevated_at'))[:10])}</strong> "
            f"(method {_esc(onset.get('method'))}). "
            "This answers “since when the orbit looked unusual”."
        )

    try:
        h = fs.get("dfa_hurst_sma")
        if h is not None and float(h) >= 0.7:
            points.append(
                f"Altitude shows <strong>persistence</strong> (DFA α ≈ {float(h):.2f}): "
                "the series tends to keep the same direction (slow drift / low thrust)."
            )
        elif h is not None and float(h) <= 0.4:
            points.append(
                f"Altitude <strong>mean-reverts</strong> (DFA α ≈ {float(h):.2f}): "
                "more station-keeping than continuous drift."
            )
    except (TypeError, ValueError):
        pass

    try:
        sh = fs.get("shannon_entropy_sma_30d")
        if sh is not None and float(sh) >= 2.5:
            points.append(
                f"Altitude variation is <strong>disordered</strong> "
                f"(Shannon ≈ {float(sh):.2f}): many irregular up/down moves in the recent window."
            )
    except (TypeError, ValueError):
        pass

    if float(fs.get("geomagnetic_storm") or 0) >= 1:
        points.append(
            "There is a <strong>geomagnetic storm</strong> in context: "
            "part of the altitude change may be drag, not only propulsion."
        )

    if not dq.get("reliable", True):
        points.append(
            f"<strong>Low TLE quality</strong> "
            f"({_esc(', '.join(dq.get('issues') or []) or '—')}). "
            "Treat the alert with caution."
        )
    elif dq.get("issues"):
        points.append(
            f"Usable data, with caveats: {_esc(', '.join(dq.get('issues') or []))}."
        )

    if tier == "HOSTILE":
        points.append(
            "Board rule: elevated pair <strong>and</strong> "
            "(CRITICAL pair, or attention ≥ 0.65, or pair_risk ≥ 0.9)."
        )
    elif tier == "SUSPECT":
        points.append(
            "Board rule: elevated pair or pair_risk ≥ 0.55, short of HOSTILE."
        )
    elif tier == "ANOMALY":
        points.append(
            "Board rule: strong series deviation or unreliable data."
        )
    else:
        points.append("Board rule: no alert threshold was crossed.")

    return {"headline": headline, "points": points}


def render_quant_html(
    entry: Dict[str, Any],
    *,
    report_meta: Optional[Dict[str, Any]] = None,
) -> str:
    report_meta = report_meta or {}
    tier = _ui_threat(entry)
    color = _threat_color(tier)
    fs = entry.get("features_snapshot") or {}
    pair = entry.get("pair") or {}
    onset = entry.get("anomaly_onset") or {}
    dq = entry.get("data_quality") or {}
    day = report_meta.get("day") or "—"
    gen = report_meta.get("generated_at") or datetime.now(timezone.utc).isoformat()
    thr = 0.55
    if isinstance(report_meta.get("summary"), dict):
        thr = report_meta["summary"].get("threshold", 0.55) or 0.55

    plain = _plain_summary(entry, tier)
    plain_points = "".join(f"<li>{p}</li>" for p in plain["points"])
    feat_rows = _feature_rows(fs)
    feat_html = "".join(
        "<tr><td><span class='feat-title'>"
        + _esc(r["title"])
        + "</span><br><code>"
        + _esc(r["key"])
        + "</code></td><td class='num'>"
        + _esc(r["value"])
        + "</td><td class='mean'>"
        + _esc(r["meaning"])
        + "</td></tr>"
        for r in feat_rows
    )

    norad = entry.get("norad_id")
    name = entry.get("object_name") or f"NORAD {norad}"
    anom = entry.get("anomaly_score")
    att = entry.get("attention_score")

    if not pair:
        pair_block = (
            "<p class='lead-muted'>No suspect×asset pair is highlighted in this score.</p>"
        )
    else:
        pair_block = (
            '<div class="grid">'
            f'<div class="chip"><div class="k">Protected asset</div>'
            f'<div class="v sm">{_esc(pair.get("asset_name"))}<br>'
            f'<span class="muted">#{_esc(pair.get("asset_norad"))}</span></div></div>'
            f'<div class="chip"><div class="k">Distance</div>'
            f'<div class="v">{_esc(_f(pair.get("min_distance_km"), 1))} '
            f'<span class="unit">km</span></div></div>'
            f'<div class="chip"><div class="k">Cointegration (p)</div>'
            f'<div class="v">{_esc(_f(pair.get("cointegration_pvalue"), 4))}</div></div>'
            f'<div class="chip"><div class="k">Pair risk</div>'
            f'<div class="v">{_esc(_f(pair.get("pair_risk")))} · '
            f'{_esc(pair.get("risk_level"))}</div></div>'
            "</div>"
            '<p class="lead-muted" style="margin-top:0.85rem">'
            "In plain terms: how close this object gets and how tightly it moves with an asset "
            "the watchlist protects. That raises priority even when the orbit alone "
            "is not extremely noisy."
            "</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Athena · {_esc(name)} · {_esc(tier)}</title>
  <style>
    :root {{
      --bg: #02040a; --panel: #0a0c10; --border: rgba(255,255,255,0.12);
      --text: #f4f4f5; --muted: #a1a1aa; --accent: #34d399; --tier: {color};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: "IBM Plex Sans", system-ui, sans-serif;
      background: var(--bg); color: var(--text); line-height: 1.55; font-size: 15.5px;
    }}
    .wrap {{ max-width: 880px; margin: 0 auto; padding: 1.5rem 1.25rem 3rem; }}
    header {{
      border: 1px solid var(--border);
      background: linear-gradient(180deg, #0c1018, #06080c);
      padding: 1.35rem 1.5rem; margin-bottom: 1rem;
    }}
    .brand {{ font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }}
    h1 {{ margin: 0.4rem 0 0.3rem; font-size: 1.5rem; font-weight: 600; }}
    .meta {{ color: var(--muted); font-size: 13.5px; }}
    .tier {{
      display: inline-block; margin-top: 0.85rem; border: 1px solid var(--tier);
      color: var(--tier); padding: 0.3rem 0.7rem; font-size: 12px;
      letter-spacing: 0.14em; text-transform: uppercase; font-weight: 600;
    }}
    section {{
      border: 1px solid var(--border); background: var(--panel);
      padding: 1.1rem 1.35rem; margin-bottom: 0.9rem;
    }}
    h2 {{
      margin: 0 0 0.85rem; font-size: 12px; letter-spacing: 0.16em;
      text-transform: uppercase; color: var(--muted); font-weight: 600;
    }}
    .headline {{ font-size: 1.05rem; line-height: 1.55; margin: 0 0 0.9rem; }}
    ul.plain {{ margin: 0; padding-left: 1.15rem; }}
    ul.plain li {{ margin-bottom: 0.65rem; }}
    .lead-muted {{ color: var(--muted); font-size: 13.5px; margin: 0; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }}
    th, td {{ border-top: 1px solid var(--border); padding: 0.6rem 0.4rem; vertical-align: top; text-align: left; }}
    th {{ color: var(--muted); font-weight: 500; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; }}
    .num {{ font-variant-numeric: tabular-nums; font-family: "IBM Plex Mono", ui-monospace, monospace; white-space: nowrap; }}
    .muted {{ color: var(--muted); font-size: 12.5px; }}
    .mean {{ color: #d4d4d8; font-size: 13px; }}
    .feat-title {{ color: #e4e4e7; font-size: 13.5px; }}
    code {{ font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 11px; color: #6ee7b7; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(148px, 1fr)); gap: 0.55rem; }}
    .chip {{ border: 1px solid var(--border); background: #000; padding: 0.6rem 0.7rem; }}
    .chip .k {{ font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }}
    .chip .v {{ margin-top: 0.25rem; font-size: 1.1rem; font-variant-numeric: tabular-nums; }}
    .chip .v.sm {{ font-size: 0.95rem; line-height: 1.35; }}
    .unit {{ font-size: 0.75rem; color: var(--muted); }}
    .math-note {{
      margin-top: 0.85rem; padding-top: 0.75rem; border-top: 1px solid var(--border);
      color: var(--muted); font-size: 13px;
    }}
    footer {{ margin-top: 1.25rem; font-size: 12.5px; color: var(--muted); }}
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand">Athena-SDA · quant report</div>
      <h1>{_esc(name)} <span class="muted">#{_esc(norad)}</span></h1>
      <div class="meta">
        {_esc(entry.get('role'))} · {_esc(entry.get('country'))} · {_esc(entry.get('purpose'))} · {_esc(entry.get('orbit_class'))}
        <br />score day {_esc(day)} · {_esc(str(gen)[:19])}
      </div>
      <div class="tier">{_esc(tier)}</div>
    </header>

    <section>
      <h2>Summary — why {_esc(tier)}</h2>
      <p class="headline">{plain["headline"]}</p>
      <ul class="plain">{plain_points}</ul>
    </section>

    <section>
      <h2>Today’s numbers</h2>
      <div class="grid">
        <div class="chip"><div class="k">Anomaly (orbit)</div><div class="v">{_esc(_f(anom))}</div></div>
        <div class="chip"><div class="k">Attention (priority)</div><div class="v">{_esc(_f(att))}</div></div>
        <div class="chip"><div class="k">Monitor status</div><div class="v sm">{_esc(entry.get('status'))}</div></div>
        <div class="chip"><div class="k">XGB class</div><div class="v sm">{_esc(entry.get('xgb_class') or '—')}</div></div>
        <div class="chip"><div class="k">Change vs yesterday</div><div class="v">{_esc(_f(entry.get('score_delta_1d')))}</div></div>
        <div class="chip"><div class="k">Anomaly threshold</div><div class="v">{_esc(_f(thr, 2))}</div></div>
      </div>
      <p class="lead-muted" style="margin-top:0.85rem">
        <strong>Anomaly</strong> = how unusual the orbit is vs this satellite's history.
        <strong>Attention</strong> = priority (mix of anomaly + pair risk vs asset).
      </p>
    </section>

    <section>
      <h2>Relation to protected asset</h2>
      {pair_block}
    </section>

    <section>
      <h2>When the noise rose</h2>
      <div class="grid">
        <div class="chip"><div class="k">Noise elevated since</div>
          <div class="v sm">{_esc(str(onset.get("first_elevated_at") or "—")[:16])}</div></div>
        <div class="chip"><div class="k">Method</div>
          <div class="v sm">{_esc(onset.get("method") or "—")}</div></div>
        <div class="chip"><div class="k">Altitude break</div>
          <div class="v sm">{_esc(str(onset.get("sma_change_at") or "—")[:16])}</div></div>
        <div class="chip"><div class="k">Windows scored</div>
          <div class="v">{_esc(onset.get("n_windows_scored") if onset.get("n_windows_scored") is not None else "—")}</div></div>
      </div>
      <p class="lead-muted" style="margin-top:0.85rem">
        Dates from TLE epochs / feature-window ends — useful for an operational timeline.
      </p>
    </section>

    <section>
      <h2>Mathematical foundation</h2>
      <p class="lead-muted" style="margin-bottom:0.9rem">
        Below: what each measure means and its value in the current snapshot.
        Isolation Forest uses them jointly on the series past; none alone “is the alarm”.
      </p>
      <table>
        <thead>
          <tr><th>Measure</th><th>Value</th><th>What it means</th></tr>
        </thead>
        <tbody>{feat_html}</tbody>
      </table>
      <div class="math-note">
        <strong>Protocol:</strong> train only on the series past (daily holdout);
        today’s point is only scored. Attention with pair:
        attention ≈ 0.45 × anomaly + 0.55 × pair_risk.
        <br />
        <strong>TLE quality:</strong> score {_esc(_f(dq.get("score")))} ·
        reliable={_esc(dq.get("reliable"))} · age {_esc(_f(dq.get("tle_age_hours"), 1))} h ·
        issues: {_esc(", ".join(dq.get("issues") or []) or "none")}.
        <br />
        <strong>Window:</strong> {_esc(entry.get("window_end") or "—")} ·
        anomaly threshold {_esc(_f(thr, 2))}.
      </div>
    </section>

    <footer>
      Athena-SDA · quant report · {_esc(day)} · daily watchlist score.
    </footer>
  </div>
</body>
</html>
"""


def load_risk_report(path: Optional[Path] = None) -> Dict[str, Any]:
    p = path or (ALERTS_DIR / "risk_report_latest.json")
    if not p.exists():
        raise FileNotFoundError(f"risk_report not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def find_board_entry(report: Dict[str, Any], norad_id: int) -> Optional[Dict[str, Any]]:
    for b in report.get("board") or []:
        if int(b.get("norad_id") or -1) == int(norad_id):
            return b
    return None


def write_quant_report(
    norad_id: int,
    *,
    risk_path: Optional[Path] = None,
    also_public: bool = True,
) -> Path:
    ensure_dirs()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = load_risk_report(risk_path)
    entry = find_board_entry(report, norad_id)
    if not entry:
        raise KeyError(f"NORAD {norad_id} not on risk board")

    html_doc = render_quant_html(entry, report_meta=report)
    day = report.get("day") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out = REPORTS_DIR / f"quant_{norad_id}_{day}.html"
    latest = REPORTS_DIR / f"quant_{norad_id}_latest.html"
    out.write_text(html_doc, encoding="utf-8")
    latest.write_text(html_doc, encoding="utf-8")

    if also_public:
        PUBLIC_REPORTS.mkdir(parents=True, exist_ok=True)
        (PUBLIC_REPORTS / f"quant_{norad_id}_latest.html").write_text(html_doc, encoding="utf-8")
        (PUBLIC_REPORTS / f"quant_{norad_id}_{day}.html").write_text(html_doc, encoding="utf-8")

    return latest


def write_all_quant_reports(
    *,
    risk_path: Optional[Path] = None,
    also_public: bool = True,
) -> List[Path]:
    ensure_dirs()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report = load_risk_report(risk_path)
    day = report.get("day") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    paths: List[Path] = []
    index_rows: List[str] = []

    for b in report.get("board") or []:
        nid = int(b.get("norad_id"))
        p = write_quant_report(nid, risk_path=risk_path, also_public=also_public)
        paths.append(p)
        tier = _ui_threat(b)
        index_rows.append(
            f"<tr><td class='num'>{nid}</td><td>{_esc(b.get('object_name'))}</td>"
            f"<td>{_esc(b.get('country'))}</td>"
            f"<td style='color:{_threat_color(tier)}'>{tier}</td>"
            f"<td class='num'>{_esc(_f(b.get('attention_score')))}</td>"
            f"<td class='num'>{_esc(_f(b.get('anomaly_score')))}</td>"
            f"<td><a href='quant_{nid}_latest.html'>open report</a></td></tr>"
        )

    index_html = f"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="utf-8"/><title>Athena quant</title>
<style>
body{{font-family:system-ui,sans-serif;background:#02040a;color:#f4f4f5;margin:0;padding:1.5rem}}
table{{border-collapse:collapse;width:100%;max-width:960px}}
td,th{{border-top:1px solid rgba(255,255,255,.12);padding:.5rem;text-align:left;font-size:14px}}
a{{color:#34d399}} .num{{font-variant-numeric:tabular-nums}}
h1{{font-size:1.2rem}} .muted{{color:#a1a1aa;font-size:13px}}
</style></head><body>
<h1>Athena-SDA · quant reports</h1>
<p class="muted">day {_esc(day)}</p>
<table>
<thead><tr><th>NORAD</th><th>Name</th><th>Country</th><th>Label</th><th>Att</th><th>Anom</th><th></th></tr></thead>
<tbody>
{"".join(index_rows)}
</tbody></table>
</body></html>
"""
    (REPORTS_DIR / "index.html").write_text(index_html, encoding="utf-8")
    if also_public:
        PUBLIC_REPORTS.mkdir(parents=True, exist_ok=True)
        (PUBLIC_REPORTS / "index.html").write_text(index_html, encoding="utf-8")
    return paths

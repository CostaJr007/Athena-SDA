#!/usr/bin/env python3
"""
Athena-SDA — daily anomaly monitoring CLI

  Past  → train Isolation Forest baseline
  Daily → inject fresh TLEs into history
  Score → flag distribution shifts vs baseline

Examples:
  # 1) Seed history (local CSV and/or HF stream)
  python scripts/run_anomaly_monitor.py seed-history
  python scripts/run_anomaly_monitor.py seed-history --hf

  # 2) Pull today's CelesTrak snapshot into the store
  python scripts/run_anomaly_monitor.py ingest-daily

  # 3) Train baseline on the past (exclude last day)
  python scripts/run_anomaly_monitor.py train-baseline

  # 4) Score latest windows
  python scripts/run_anomaly_monitor.py score

  # Full loop (ingest → train if missing → score)
  python scripts/run_anomaly_monitor.py run-daily
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Project root on path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def cmd_seed_history(args: argparse.Namespace) -> None:
    from src.tle_store import (
        load_history,
        seed_from_existing_csv,
        seed_from_hf_history_streaming,
        reload_watchlist,
        DEFAULT_WATCHLIST,
    )

    names = reload_watchlist()
    print("=== seed-history ===")
    print(f"Watchlist: {len(names)} NORADs from catalog")
    if not args.skip_local:
        local = seed_from_existing_csv()
        print(f"Local CSV seed: {len(local)} rows")

    if args.hf:
        seed_from_hf_history_streaming(
            norad_ids=list(names.keys()) if names else list(DEFAULT_WATCHLIST.keys()),
            start_year=args.start_year,
            max_rows=args.max_rows,
            prefer_year_parquet=not args.stream,
            end_year=args.end_year,
        )

    hist = load_history()
    n_sats = hist["norad_id"].nunique() if len(hist) else 0
    print(f"History store: {len(hist)} epochs, {n_sats} sats")
    if len(hist):
        g = hist.groupby("norad_id").size()
        print(f"Sats with ≥20 epochs: {int((g >= 20).sum())}/{n_sats}")
        print(f"Range: {hist['timestamp'].min()} → {hist['timestamp'].max()}")


def cmd_ingest_daily(args: argparse.Namespace) -> None:
    from src.tle_store import (
        DEFAULT_WATCHLIST,
        append_epochs,
        fetch_celestrak_watchlist,
        fetch_hf_constellation_latest,
        reload_watchlist,
        save_daily_snapshot,
    )

    names = reload_watchlist()
    ids = list(names.keys()) if names else list(DEFAULT_WATCHLIST.keys())
    print("=== ingest-daily ===")
    print(f"Watchlist targets: {len(ids)}")
    frames = []

    if args.source in ("celestrak", "both"):
        print("Fetching CelesTrak (CATNR + groups)…")
        try:
            df_c = fetch_celestrak_watchlist(
                norad_ids=ids,
                groups=tuple(g for g in args.groups.split(",") if g.strip()),
                prefer_catnr=not args.groups_only,
            )
            frames.append(df_c)
            print(f"  watchlist hits: {len(df_c)} sats/epochs")
        except Exception as e:
            print(f"  CelesTrak error: {e}")

    if args.source in ("hf", "both"):
        print("Fetching HF constellation-tle-latest…")
        try:
            df_h = fetch_hf_constellation_latest()
            idset = set(ids)
            if "norad_id" in df_h.columns and len(df_h):
                hit = df_h[df_h["norad_id"].isin(idset)]
                frames.append(hit if len(hit) else df_h.head(500))
            print(f"  HF rows kept: {len(frames[-1]) if frames else 0}")
        except Exception as e:
            print(f"  HF error: {e}")

    if not frames:
        print("No data ingested.")
        return

    import pandas as pd

    day_df = pd.concat(frames, ignore_index=True)
    path = save_daily_snapshot(day_df)
    full, n_new = append_epochs(day_df)
    print(f"Snapshot: {path}")
    print(f"Appended ~{n_new} new epoch rows → history total {len(full)}")


def cmd_train(args: argparse.Namespace) -> None:
    from src.anomaly_monitor import train_baseline_from_history

    print("=== train-baseline (série = passado; holdout fora) ===")
    meta = train_baseline_from_history(
        holdout_days=args.holdout_days,
        contamination=args.contamination,
        sample_mode=getattr(args, "sample_mode", "hybrid"),
    )
    print(json_dumps(meta))


def cmd_score(args: argparse.Namespace) -> None:
    from src.anomaly_monitor import score_latest

    print("=== score-latest (hoje vs série / baseline) ===")
    report = score_latest(
        anomaly_threshold=args.threshold,
        use_full_pipeline=not args.if_only,
        with_pairs=not args.no_pairs,
        delta_relevance=getattr(args, "delta_relevance", 0.08),
    )
    anoms = [a for a in report["alerts"] if a.get("is_anomaly")]
    print(f"\nAnomalies / elevated ({len(anoms)}):")
    for a in anoms[:20]:
        pair = a.get("pair") or {}
        dlt = a.get("score_delta_1d")
        dlt_s = f"Δ1d={dlt:+.3f}" if dlt is not None else "Δ1d=n/a"
        print(
            f"  #{a['norad_id']:>5}  {a.get('object_name',''):<22}  "
            f"anom={a['anomaly_score']:.3f}  {dlt_s}  "
            f"[{a.get('status','')}]  pair={pair.get('risk_level','-')} "
            f"vs {pair.get('asset_name','')}"
        )
    if not anoms:
        print("  (none above threshold with reliable data)")
    # top attention even if not anomaly
    ranked = sorted(
        report["alerts"],
        key=lambda x: -float(x.get("attention_score") or x.get("anomaly_score") or 0),
    )
    print("\nTop attention:")
    for a in ranked[:8]:
        pair = a.get("pair") or {}
        print(
            f"  [{a.get('role','?'):8}] #{a['norad_id']:>5}  "
            f"att={float(a.get('attention_score') or a.get('anomaly_score') or 0):.3f}  "
            f"anom={float(a.get('anomaly_score') or 0):.3f}  "
            f"{a.get('object_name','')[:20]:20}  "
            f"pair→{pair.get('asset_name','-')[:18]} r={pair.get('pair_risk','-')}"
        )


def cmd_score_pairs(args: argparse.Namespace) -> None:
    from src.pair_score import score_all_pairs

    print("=== score-pairs (suspect × asset) ===")
    rep = score_all_pairs(top_k_per_suspect=args.top_k, max_pairs=args.max_pairs)
    print(f"pairs={rep['n_pairs_scored']} elevated={rep['n_elevated']}")
    for p in (rep.get("pairs") or [])[:15]:
        if p.get("error"):
            continue
        print(
            f"  {p.get('suspect_name','')[:22]:22} → {p.get('asset_name','')[:20]:20}  "
            f"dist={p.get('min_distance_km')} km  coint_p={p.get('cointegration_pvalue')}  "
            f"risk={p.get('pair_risk')} [{p.get('risk_level')}]"
        )


def cmd_run_daily(args: argparse.Namespace) -> None:
    """
    Protocolo diário padrão:
      1) ingest  → anexa TLE de hoje à série
      2) train   → baseline = série até D−holdout (ontem e antes); hoje NÃO treina
      3) score   → compara última janela com a série; alerta se desvio relevante
    """
    from pathlib import Path
    from src.anomaly_monitor import IFOREST_MONITOR_PATH, train_baseline_from_history, score_latest
    from src.config import MODELS_DIR

    print("=== run-daily (série → baseline; hoje → comparação) ===")
    cmd_ingest_daily(args)

    model = IFOREST_MONITOR_PATH if IFOREST_MONITOR_PATH.exists() else MODELS_DIR / "isolation_forest.joblib"
    # Padrão: SEMPRE retreina o baseline no passado (holdout), a menos que --skip-retrain
    do_train = not getattr(args, "skip_retrain", False)
    if do_train or not model.exists():
        print(
            f"Atualizando baseline na SÉRIE (passado, holdout={args.holdout_days}d)…"
        )
        train_baseline_from_history(
            holdout_days=args.holdout_days,
            contamination=args.contamination,
            sample_mode=getattr(args, "sample_mode", "hybrid"),
        )
    else:
        print(f"Usando baseline existente (--skip-retrain): {model}")

    score_latest(
        anomaly_threshold=args.threshold,
        use_full_pipeline=not args.if_only,
        delta_relevance=getattr(args, "delta_relevance", 0.08),
    )


def cmd_status(args: argparse.Namespace) -> None:
    from src.tle_store import load_history, DAILY_DIR, ALERTS_DIR, EPOCHS_CSV, EPOCHS_PARQUET
    from src.anomaly_monitor import IFOREST_MONITOR_PATH, MONITOR_META_PATH
    from src.config import MODELS_DIR
    from src.catalog import summary as catalog_summary

    hist = load_history()
    print("=== store status ===")
    print(f"history rows: {len(hist)}")
    if len(hist):
        print(f"sats: {hist['norad_id'].nunique()}")
        print(f"range: {hist['timestamp'].min()} → {hist['timestamp'].max()}")
        covered = set(int(x) for x in hist["norad_id"].unique())
    else:
        covered = set()
    print(f"epochs parquet: {EPOCHS_PARQUET.exists()}  csv: {EPOCHS_CSV.exists()}")
    print(f"daily dir: {DAILY_DIR} ({len(list(DAILY_DIR.glob('tle_*.csv')))} snapshots)")
    print(f"alerts dir: {ALERTS_DIR}")
    print(f"monitor IF: {IFOREST_MONITOR_PATH.exists()}")
    print(f"pipeline IF: {(MODELS_DIR / 'isolation_forest.joblib').exists()}")
    try:
        from src.space_weather import status as sw_status, lookup_space_weather

        sws = sw_status()
        now = lookup_space_weather(None)
        print("=== space weather ===")
        print(f"days={sws.get('n_days')} range={sws.get('range')}")
        print(
            f"today-ish: F10.7={now.get('f10_7'):.1f} Ap={now.get('ap_index'):.0f} "
            f"Kp={now.get('kp_mean'):.2f} storm={now.get('geomagnetic_storm')}"
        )
    except Exception as e:
        print(f"=== space weather === (unavailable: {e})")

    cat = catalog_summary()
    print("=== catalog ===")
    print(f"source: {cat.get('source')}")
    print(f"objects: {cat['n_objects']}  roles: {cat['counts']}")
    missing = [n for n in cat["norad_ids"] if n not in covered]
    print(f"history coverage: {cat['n_objects'] - len(missing)}/{cat['n_objects']} watchlist sats")
    if missing:
        print(f"missing from history (need seed/ingest): {missing[:12]}{'…' if len(missing) > 12 else ''}")

    if MONITOR_META_PATH.exists():
        print("=== monitor meta ===")
        print(MONITOR_META_PATH.read_text(encoding="utf-8")[:500])


def cmd_catalog(args: argparse.Namespace) -> None:
    from src.catalog import clear_watchlist_cache, load_watchlist, summary

    clear_watchlist_cache()
    s = summary()
    print("=== watchlist catalog ===")
    print(json_dumps(s))
    if args.verbose:
        wl = load_watchlist()
        for o in wl["objects"]:
            print(
                f"  [{o['role']:8}] #{o['norad_id']:<6}  {o['name']:<32}  "
                f"{o['country']}/{o['purpose']}/{o['orbit_class']}"
            )


def cmd_seed_space_weather(args: argparse.Namespace) -> None:
    from src.space_weather import clear_lookup_cache, seed_space_weather, status

    print("=== seed-space-weather (GFZ F10.7 / Ap / Kp) ===")
    meta = seed_space_weather(
        start_year=args.start_year,
        merge_noaa=not args.no_noaa,
        force=args.force,
        keep_full_archive=args.full_archive,
    )
    clear_lookup_cache()
    print(json_dumps(meta if isinstance(meta, dict) else status()))


def cmd_space_weather_status(args: argparse.Namespace) -> None:
    from src.space_weather import lookup_space_weather, status

    print("=== space-weather store ===")
    print(json_dumps(status()))
    sw = lookup_space_weather(None)
    print("latest lookup:", json_dumps(sw))


def json_dumps(obj) -> str:
    import json
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def main() -> None:
    p = argparse.ArgumentParser(description="Athena-SDA anomaly monitor (past train + daily inject)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("seed-history", help="Import local CSV and optional HF TLE history")
    s.add_argument("--hf", action="store_true", help="Load HF space-track-tle-history (year parquet by default)")
    s.add_argument("--start-year", type=int, default=2024)
    s.add_argument("--end-year", type=int, default=None, help="Last year inclusive (default: current UTC year)")
    s.add_argument("--max-rows", type=int, default=15000, help="Only for --stream mode")
    s.add_argument(
        "--stream",
        action="store_true",
        help="Legacy full-archive streaming (slow). Default is year-parquet + filter.",
    )
    s.add_argument("--skip-local", action="store_true", help="Skip real_tle_history CSV import")
    s.set_defaults(func=cmd_seed_history)

    s = sub.add_parser("ingest-daily", help="Fetch today's TLEs and append to history")
    s.add_argument("--source", choices=["celestrak", "hf", "both"], default="celestrak")
    s.add_argument(
        "--groups",
        default="visual,stations,resource,weather,gps-ops",
        help="CelesTrak groups used only as fallback fill (CSV). Prefer CATNR.",
    )
    s.add_argument(
        "--groups-only",
        action="store_true",
        help="Skip per-NORAD CATNR; only use GROUP dumps (legacy)",
    )
    s.set_defaults(func=cmd_ingest_daily)

    s = sub.add_parser(
        "train-baseline",
        help="Treina IF na SÉRIE (passado até D−holdout); hoje não entra no treino",
    )
    s.add_argument("--holdout-days", type=int, default=1, help="Dias finais excluídos do treino (1=ontem e antes)")
    s.add_argument("--contamination", type=float, default=0.08)
    s.add_argument(
        "--sample-mode",
        choices=["hybrid", "recent", "full"],
        default="hybrid",
        help="Como amostrar a série: hybrid=longa+recente (padrão)",
    )
    s.set_defaults(func=cmd_train)

    s = sub.add_parser(
        "score",
        help="Compara última janela de cada sat com o baseline da série (+ pares)",
    )
    s.add_argument("--threshold", type=float, default=0.55)
    s.add_argument(
        "--delta-relevance",
        type=float,
        default=0.08,
        help="Δ anomaly_score vs ontem para marcar mudança relevante",
    )
    s.add_argument("--if-only", action="store_true", help="Skip XGBoost layer")
    s.add_argument("--no-pairs", action="store_true", help="Skip suspect×asset pair scoring")
    s.set_defaults(func=cmd_score)

    s = sub.add_parser("score-pairs", help="Score suspect×asset proximity + cointegration only")
    s.add_argument("--top-k", type=int, default=3, help="Top assets kept per suspect")
    s.add_argument("--max-pairs", type=int, default=80)
    s.set_defaults(func=cmd_score_pairs)

    s = sub.add_parser(
        "run-daily",
        help="Protocolo diário: ingest → baseline na série (passado) → score do hoje",
    )
    s.add_argument("--source", choices=["celestrak", "hf", "both"], default="celestrak")
    s.add_argument("--groups", default="visual,stations,resource,weather,gps-ops")
    s.add_argument("--groups-only", action="store_true")
    s.add_argument(
        "--skip-retrain",
        action="store_true",
        help="Não retreina baseline (só score). Padrão é sempre retreinar no passado.",
    )
    s.add_argument("--holdout-days", type=int, default=1)
    s.add_argument("--contamination", type=float, default=0.08)
    s.add_argument("--threshold", type=float, default=0.55)
    s.add_argument("--delta-relevance", type=float, default=0.08)
    s.add_argument(
        "--sample-mode",
        choices=["hybrid", "recent", "full"],
        default="hybrid",
    )
    s.add_argument("--if-only", action="store_true")
    s.set_defaults(func=cmd_run_daily)

    s = sub.add_parser("status", help="Show history / model / alert paths + catalog coverage")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("catalog", help="Show military-first watchlist from data/catalog/watchlist.json")
    s.add_argument("-v", "--verbose", action="store_true", help="List every object")
    s.set_defaults(func=cmd_catalog)

    s = sub.add_parser(
        "seed-space-weather",
        help="Download GFZ daily F10.7 / Ap / Kp into data/space_weather/",
    )
    s.add_argument("--force", action="store_true", help="Re-download even if cache fresh")
    s.add_argument("--start-year", type=int, default=2014, help="Keep data from this year (default 2014)")
    s.add_argument("--full-archive", action="store_true", help="Keep GFZ full archive from 1932")
    s.add_argument("--no-noaa", action="store_true", help="Skip NOAA F10.7 recent merge")
    s.set_defaults(func=cmd_seed_space_weather)

    s = sub.add_parser("space-weather-status", help="Show local space weather store + latest values")
    s.set_defaults(func=cmd_space_weather_status)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

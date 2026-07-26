"""Quick smoke test: retrain + run inference DAG on demo catalog."""
from src.models import train_and_save_models, load_models
from src.pipeline import build_demo_constellation, process_constellation
from src.bob import answer_operator_query


def main():
    import sys
    if "--train" in sys.argv:
        m = train_and_save_models()
        print("TRAIN", m["accuracy_test"], m["log_loss_test"], m["macro_f1"], m["class_distribution"])

    iforest, xgb, rkhs, metrics = load_models()
    print("metrics", metrics.get("accuracy_test"), metrics.get("class_distribution"))
    sats = build_demo_constellation()
    out = process_constellation(sats, iforest, xgb, rkhs)
    by_id = {p["id"]: p for p in out}

    print("\n--- Catalog scores ---")
    for p in sorted(out, key=lambda x: -x["threat_level"]):
        print(
            f"#{p['id']:5d} {p['name'][:28]:28s} {p['classification']:8s} "
            f"thr={p['threat_level']:.2f} xgb={p['xgb_class']:8s} "
            f"dist={p['min_dist_mil']:.1f} kelly={p['kelly_allocation']:.2f} "
            f"coint={p['cointegration_pvalue']:.3f}"
        )

    print("\n--- Bob tools ---")
    print(answer_operator_query("Quais alertas ativos?", sats, out, by_id)[:400])
    print("---")
    print(answer_operator_query("Briefing do #44231", sats, out, by_id)[:500])
    print("\nOK")


if __name__ == "__main__":
    main()

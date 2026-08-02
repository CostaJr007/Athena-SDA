# Discussion report — ML & data (Athena-SDA)

**Purpose:** Working document for ML/data improvements.  
**Project objective:** Quantitative orbital noise detection with ML + honest walk-forward validation, in a Palantir-inspired architecture (hot-swap micro-models · Data→Inference DAG · post-quant LLM · ontology board).  
**Decision rule:** Changes should strengthen walk-forward science, reproducibility, and architecture alignment.

---

## 0. Baseline state (verified)

| Item | State |
|------|--------|
| Data | ~249,580 epochs, 24 NORADs, 2014-01-01 → 2026-07-27, real GFZ space weather |
| Walk-forward | GEO panel: 5/5 interest hard hits, 0/7 civil EO placebos (thr 0.50) |
| Doctrine | IF trains on baseline+asset; suspects scored for detection |
| Paper pack | Claims A+B, figures, LaTeX article, registry |

---

## 1. Closed consensus

1. Quantitative noise analysis and alerts on military-interest objects.  
2. Keep past-only walk-forward protocol.  
3. React UI only (Streamlit removed).  
4. IF measures series strangeness; distance/coint in priority layer.  
5. Weak labels for XGB; IF + walk-forward for scientific validation.

---

## 2. Implemented improvements (summary)

- Military-first IF train (baseline+asset; no Starlink in train)  
- Multi-scale Hurst/Shannon features  
- Threshold calibration from normality quantiles  
- Model registry; monitor IF ≠ pipeline IF  
- Paper validation package + pre-peak figures  
- Expanded unique interest NORADs + civil EO placebos  
- Smoke tests and feature ablation script  

---

## 3. Follow-on work (optional)

- Larger unique interest N with citable anchors  
- Orbit-class-specific IF models  
- Full SGP4 TCA for pair geometry  
- Globe tracks from live watchlist TLEs  

---

## 4. Reproduce

```bash
python scripts/smoke_test.py
python scripts/run_anomaly_monitor.py train-baseline
python scripts/run_paper_validation.py --threshold 0.50
python scripts/plot_prepeak_curves.py
```

*Athena-SDA · ML & data working notes (English).*

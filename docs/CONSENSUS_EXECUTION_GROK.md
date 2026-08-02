# Closed consensus — execution notes (Athena-SDA)

**Mandate:** Keep the PoC auditable — quantitative noise separation under past-only walk-forward, deterministic features, versioned models, honest metrics.

**Explicit non-goals:** New larger models for vanity accuracy; replacing weak labels with tiny event labels; narrative that overstates ramp-to-report skill.

---

## Done (military-first + paper pack)

1. Honest walk-forward metrics (`first_fold_hit`, `noise_ramp`, pre-peak stats).  
2. Separate monitor/pipeline IF + `models/registry.json`.  
3. RKHS excluded from IF; multi-scale Hurst/Shannon added.  
4. Temporal purge split for XGB; accuracy labeled as weak-label agreement.  
5. Feature guards (Kolmogorov, Mandelbrot, Hurst, fuzzy clamp, coint align).  
6. Smoke tests; space weather in feature vector.  
7. Claims A+B paper validation, figures, LaTeX article (English), glossary appendix.  
8. README and foundation docs focused on system capability.  

---

## Acceptance checklist

- [x] Walk-forward runs with honest metrics  
- [x] `train-baseline` does not overwrite pipeline IF  
- [x] Paper package regenerates via `run_paper_validation.py`  
- [x] GEO Claims A+B supported in latest validation JSON  
- [x] Project docs and paper in English  

---

## Optional Lote B

- More unique interest NORADs  
- Orbit-class IF  
- Real TLE globe tracks  
- Bob event citations in UI  

*Consensus notes · English.*

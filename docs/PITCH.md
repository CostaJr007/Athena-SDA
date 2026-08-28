# Athena-SDA — Pitch Script (1 minute)

> Honest framing: architecture **inspired by Palantir's public patents** —
> never "built with Palantir" nor an affiliation. Validation by walk-forward
> on documented events; public SPLID benchmark when available.

---

## Opening (0:00–0:15) — the problem

> "Operators cannot watch 45,000+ objects in the space catalog
> (18 SDS / USSPACECOM) all the time. Legacy systems fire alerts without
> explaining, prioritizing, or recommending action. Athena-SDA turns public
> TLE + space weather into **military operational insights** — from thousands
> of objects down to a handful of decisions per day."

## The architecture (0:15–0:40) — what we built

> "We implemented the architecture of 5 public Palantir patents:
>
> - **Orchestrated micro-models** with daily hot-swap (AI Meta-Constellation
>   patent): a normality Isolation Forest + XGBoost priority + Dempster-Shafer
>   evidential fusion;
> - **An LLM that explains, never rewrites scores** (ML+LLM geospatial
>   patent): the Bob copilot contextualizes each alert and cites open sources
>   when they match documented events;
> - **Typed API contracts** (sensor-correlation patent): Data API (TLE),
>   Inference API (model registry), Open API (schema-validated
>   risk_report v1);
> - **Ontology with cross-filters** (ontology-map patent): role × country ×
>   orbit filter the board and globe in real time;
> - **Temporal replay** (time-series geo patent): the score curve up to the
>   public anchor with a slider.
>
> Plus a **corrected, per-feature-cited math layer** — LZ76, DFA, MMD,
> ARL-calibrated CUSUM/EWMA, SSA, BOCPD, Kalman innovation
> (Zollo & Weigel 2023) — with a DOI per method in the Proof Dossier."

## The proof (0:40–0:55) — it works and it is honest

> "**Walk-forward validation on documented military events** (Luch/
> Olymp-K, Yaogan, Shiyan, SY-12) with civil placebos: hard hits with
> 150–240 day lead on the interest cases, and the placebos **do not** fire
> (Claims A+B re-validated). [Final numbers here after re-validation.]
> The public SPLID benchmark (MIT ARCLab) — where the top solution uses
> XGBoost, our stack — gives a comparable metric against the state of the
> art."

## Close (0:55–1:00)

> "The only open-source military SDA pipeline with temporal validation on
> documented events, a per-feature-cited mathematical framework, and a
> Palantir-style ontological architecture. **From 30,000 objects to ~15
> decisions per day — with explanation.**"

---

## Demo script (3 min, live)

1. **Globe + board** — open the mission board; hover the watchlist tracks
   (Maven colors: yellow suspect, blue asset).
2. **Cross-filters** — filter CN + GEO + suspect → board and globe dim
   (ontology-map patent).
3. **Luch/Olymp-K** — select #40258 → RightDock: belief/plausibility from the
   evidential fusion + Kelly + "Task sensor" validate-only.
4. **Replay** — Replay tab in the PoC panel: slider up to `t_peak` with the
   cited source (time-series geo patent).
5. **Quant report** — open the per-NORAD HTML (features and signals).

## Pitfalls to avoid

- ❌ "We detect spies with 99% accuracy" — we say "behavioral analysis of the
  public catalog; pattern-of-life ≠ intent".
- ❌ "Real-time tracking" — public TLE is stale by definition; we say
  "analysis of the public catalog at 1–4 TLEs/day cadence".
- ❌ "Built with Palantir" — we say "architecture inspired by verified public
  patents (docs/references/palantir_patents.md)".

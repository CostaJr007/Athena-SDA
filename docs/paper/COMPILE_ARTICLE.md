# Compile the Athena-SDA LaTeX article

## Files

- `docs/paper/athena_sda_article.tex` — full paper (English)
- Figures in `docs/paper/figures/`

## Build

```bash
cd docs/paper
pdflatex athena_sda_article.tex
pdflatex athena_sda_article.tex
# Output: athena_sda_article.pdf
```

Requires TeX Live / MiKTeX with standard packages (`graphicx`, `hyperref`, `babel`, etc.).

## Refresh numbers and figures before final PDF

```bash
# repo root
python scripts/run_paper_validation.py --threshold 0.50
python scripts/plot_prepeak_curves.py
```

## Paper structure

1. Introduction and Claims A+B  
2. Military-first doctrine  
3. Data (TLE + GFZ)  
4. Quantitative feature math  
5. Isolation Forest past-only  
6. Walk-forward  
7. Priority layer  
8. Results + figures  
9. Discussion, limitations, reproducibility  
10. **Appendix: Glossary** (what each tool does)

## Git

Prefer committing `.tex` (and figures already in git). Commit PDF only if your workflow requires it.

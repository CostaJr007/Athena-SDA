# Compilar o artigo LaTeX (Athena-SDA)

## Ficheiro

- `docs/paper/athena_sda_article.tex` — artigo completo (PT)
- Figuras em `docs/paper/figures/`

## Compilar (local)

```bash
cd docs/paper
pdflatex athena_sda_article.tex
pdflatex athena_sda_article.tex
# PDF: athena_sda_article.pdf
```

Requisitos: TeX Live / MiKTeX com `babel-brazil`, `graphicx`, `hyperref`, etc.

## Regenerar números e figuras antes do PDF final

```bash
# na raiz do repo
python scripts/run_paper_validation.py --threshold 0.50
python scripts/plot_prepeak_curves.py
```

## Conteúdo do artigo

1. Introdução e claims A+B  
2. Doutrina militar-first  
3. Dados (TLE + GFZ)  
4. Matemática das features  
5. Isolation Forest past-only  
6. Walk-forward  
7. Prioridade (fora de A+B)  
8. Resultados + figuras pre-peak  
9. Discussão, limitações, reprodutibilidade  

## GitHub

Após gerar o PDF localmente, podes versionar só o `.tex` (recomendado) ou também o `.pdf` se o repositório aceitar binários.

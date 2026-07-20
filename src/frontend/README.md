# Frontend — ATHENA-SDA Command Center

Interface de visualização estática do projeto, inspirada no design do repositório [heartfelt-hub](https://github.com/CostaJr007/heartfelt-hub).

## Localização

```
src/frontend/
├── index.html      ← Dashboard principal (Command Center)
├── track.html      ← Dossier individual de cada objeto rastreado
└── tracks.js       ← Catálogo de dados dos 7 objetos de demonstração
```

## Como usar

### Opção 1 — Abrir diretamente no navegador

Abra o arquivo `src/frontend/index.html` no navegador. Por ser estático (sem dependências externas), funciona sem servidor.

```
# Windows
start src/frontend/index.html

# Linux / macOS
xdg-open src/frontend/index.html
```

### Opção 2 — Servir com Python (recomendado para evitar CORS)

```bash
cd src/frontend
python3 -m http.server 8080
# Acesse: http://localhost:8080
```

### Opção 3 — Servir junto com o Streamlit (produção)

O arquivo `app.py` do Streamlit pode servir os arquivos estáticos via:

```python
import streamlit.components.v1 as components
components.html(open("src/frontend/index.html").read(), height=900, scrolling=True)
```

---

## Páginas

### `index.html` — Command Center

Dashboard completo com HUD tático militar:

| Painel | Descrição |
|--------|-----------|
| **KPI Row** | Tracks ativos, Hostis, Anomalias, Kelly Max |
| **Orbital Scope** | Radar polar SVG animado com todos os objetos clicáveis |
| **Threat Board** | Tabela com NORAD ID, país (bandeira), designação, classe, altitude, velocidade, entropia, confiança |
| **Inference DAG** | Pipeline: Feature Extractor → Isolation Forest → XGBoost → Fuzzy Mamdani → Kelly → Bob/Granite |
| **Sensor Tasking** | Fila Kelly: 4 sensores GEODSS/Space Fence com alocação f* |
| **Copilot / Bob** | Chat com Bob (respostas estáticas simuladas + fallback por NORAD ID) |

### `track.html` — Dossier Individual

Página de detalhes por objeto (navegação via `track.html?id=44231`):

| Painel | Descrição |
|--------|-----------|
| **Identification** | NORAD, designação, operador, site, veículo, missão, notas de intel |
| **Current State** | LAT/LON/ALT/VEL + mapa equiretangular com marcador animado |
| **Orbital Elements** | INC, período, apogeu, perigeu |
| **ML Assessment** | Shannon entropy, confiança, barra de classificação |
| **Orbital Globe** | Globo 3D ortográfico SVG com anel de órbita real, satélite pulsante |
| **Footer Nav** | Links rápidos para outros objetos do catálogo |

---

## Objetos no Catálogo de Demonstração

| NORAD | Designação | Ameaça |
|-------|-----------|--------|
| #44231 | COSMOS-2542 | 🔴 HOSTILE |
| #48274 | USA-311 | 🟠 SUSPECT |
| #39227 | SHIYAN-7 | 🟠 SUSPECT |
| #25544 | ISS (ZARYA) | 🟢 NOMINAL |
| #43013 | NROL-42 | 🟡 ANOMALY |
| #02001 | COSMOS-482 DB | 🟡 ANOMALY |
| #58291 | STARLINK-30412 | 🟢 NOMINAL |

---

## Integração com o Pipeline Python

Quando o backend estiver implementado, substituir `tracks.js` por dados gerados dinamicamente:

```python
# athena/export.py
import json

def export_tracks_js(tracks_df, path="src/frontend/tracks.js"):
    """Exporta DataFrame de tracks para JS estático."""
    tracks = tracks_df.to_dict(orient='records')
    with open(path, 'w') as f:
        f.write("const TRACKS = ")
        json.dump(tracks, f, indent=2)
        f.write(";\nfunction getTrack(id){return TRACKS.find(t=>t.id===id);}\n")
```

Ou servir via endpoint Streamlit/FastAPI que retorna o JSON diretamente.

---

## Design System

Inspirado em HUD tático militar (heartfelt-hub):

- **Fundo:** Grid verde escuro com efeito scanlines CRT
- **Cor primária:** Verde fosforescente `oklch(0.82 0.22 148)` → `#4fbf68`
- **Classes de ameaça:** Hostile (vermelho), Suspect (âmbar), Anomaly (amarelo), Nominal (verde)
- **Tipografia:** JetBrains Mono / IBM Plex Mono (monoespacial)
- **Cantos HUD:** Decoração `.panel` com pseudoelementos `::before/::after`
- **Animações:** Scan line, radar sweep, blink alert, pulso de satélite

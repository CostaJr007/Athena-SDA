import os
import sys
from pathlib import Path

import pandas as pd
from datasets import load_dataset
from datetime import datetime
import zoneinfo

# Project root on path (script may be run from any cwd)
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

print("Iniciando o download de dados reais e públicos de satélites (Space-Track TLE History)...")
print("Fonte: Hugging Face Datasets (juliensimon/space-track-tle-history)")

# Prefer data/catalog/watchlist.json (military-first). Fallback list is validated NORADs.
try:
    from src.catalog import name_map

    TARGET_SATS = name_map()
    if not TARGET_SATS:
        raise RuntimeError("empty catalog")
except Exception:
    TARGET_SATS = {
        25544: "ISS (ZARYA)",
        39166: "NAVSTAR 68 (USA 242)",
        41038: "YAOGAN-29",
        40258: "LUCH (OLYMP-K 1)",
        39208: "SHIYAN-7 (SY-7)",
        25994: "TERRA",
        43013: "NOAA 20 (JPSS-1)",
        44714: "STARLINK-1008",
        48274: "CSS (TIANHE)",
        43603: "BEIDOU-3 M11",
    }

norad_ids = set(TARGET_SATS.keys())

# Vamos varrer o dataset remotamente usando streaming para não baixar os 40GB inteiros.
# Usamos streaming=True para processar os dados on-the-fly.
ds = load_dataset('juliensimon/space-track-tle-history', split='train', streaming=True)

# Limites de tempo (Últimos 2 anos - 2024 a 2026)
START_YEAR = 2024

collected_rows = []
total_processed = 0

print(f"Filtrando histórico real dos últimos 2 anos (>= {START_YEAR}) para os seguintes satélites estratégicos:")
for k, v in TARGET_SATS.items():
    print(f" - #{k}: {v}")

print("Buscando dados na nuvem... Isso pode demorar alguns minutos dependendo da conexão e tamanho da busca.")

# Interando pelos registros em streaming
for row in ds:
    total_processed += 1
    
    # Progresso a cada 500k linhas (o dataset tem milhões)
    if total_processed % 500000 == 0:
        print(f"Processadas {total_processed} medições orbitais...")
        
    # Verifica se é um dos satélites alvos
    if row['norad_id'] in norad_ids:
        # Verifica se o dado é recente (últimos 2 anos)
        if row['epoch'].year >= START_YEAR:
            collected_rows.append(row)
            
    # Critério de parada: Se já conseguimos muitas amostras (ex: 50.000), paramos.
    if len(collected_rows) >= 30000:
        print("Massa de dados suficiente atingida para o treinamento (30.000 TLEs históricos).")
        break

if len(collected_rows) > 0:
    df = pd.DataFrame(collected_rows)
    
    # Salva os dados na pasta data/
    DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
    os.makedirs(DATA_DIR, exist_ok=True)
    
    csv_path = os.path.join(DATA_DIR, "real_tle_history_2024_2026.csv")
    df.to_csv(csv_path, index=False)
    print(f"Download concluído com sucesso!")
    print(f"Dados reais salvos em: {csv_path} ({len(df)} registros)")
    print(df.head())
else:
    print("Nenhum dado encontrado para os filtros selecionados.")

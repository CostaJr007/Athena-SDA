import os
import pandas as pd
from datasets import load_dataset
from datetime import datetime
import zoneinfo

print("Iniciando o download de dados reais e públicos de satélites (Space-Track TLE History)...")
print("Fonte: Hugging Face Datasets (juliensimon/space-track-tle-history)")

# Lista curada de satélites de interesse para treinamento de Machine Learning.
# Inclui satélites militares, constelações civis, espiões conhecidos e satélites com manobras bruscas.
TARGET_SATS = {
    44231: "YAOGAN-31 (CN Militar/Espião)",
    43013: "COSMOS-2521 (RU Militar - Manobras Hostis)",
    25994: "TERRA (US Científico)",
    41905: "STARLINK-1001 (US Civil/Comercial)",
    43941: "USSF-22988 (US Militar Alvo)",
    43603: "SHIYAN-12 (CN Experimento Tecnológico)",
    39166: "EUTELSAT-36B (FR Comercial GEO)",
    25544: "ISS (Estação Espacial Internacional)"
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

import duckdb
import os
import pandas as pd

print("Conectando ao banco de dados público histórico Space-Track via DuckDB...")

# Conecta no duckdb em memória
con = duckdb.connect()

# Instala e carrega extensão httpfs para ler parquet remotamente
con.execute("INSTALL httpfs;")
con.execute("LOAD httpfs;")

# URL base dos parquets do dataset juliensimon/space-track-tle-history
# A estrutura de pastas lá é parquet/ com vários arquivos. Mas duckdb consegue ler com wildcard!
# Porém o Hugging Face datasets usa URLs com 'hf://' em versões recentes.
parquet_url = "hf://datasets/juliensimon/space-track-tle-history/**/*.parquet"

query = f"""
SELECT norad_id, epoch, inclination, raan, eccentricity, arg_perigee, 
       mean_anomaly, mean_motion, bstar, intl_designator, altitude_km
FROM '{parquet_url}'
WHERE year(epoch) >= 2024
  AND norad_id IN (44231, 43013, 25994, 41905, 43941, 43603, 39166, 25544)
ORDER BY epoch
"""

print("Executando extração remota (Big Data). O DuckDB está filtrando 238 milhões de registros na nuvem...")
try:
    df = con.execute(query).df()
    
    if len(df) > 0:
        DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        os.makedirs(DATA_DIR, exist_ok=True)
        csv_path = os.path.join(DATA_DIR, "real_tle_history_2024_2026.csv")
        df.to_csv(csv_path, index=False)
        print(f"Sucesso! {len(df)} registros reais baixados e salvos em {csv_path}")
    else:
        print("Nenhum registro encontrado para esses filtros (Verifique a permissão hf:// ou timeout).")
except Exception as e:
    print(f"Erro ao executar DuckDB query: {e}")
    print("Tentando fallback API REST CelesTrak (30 dias em tempo real) para garantir dados REAIS de agora:")
    
    import requests
    # Busca catálogo ativo CelesTrak JSON
    url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json"
    print("Baixando catálogo ativo global atual (CelesTrak)...")
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()
        df_celes = pd.DataFrame(data)
        
        # Filtra os satélites reais
        target_ids = [44231, 43013, 25994, 41905, 43941, 43603, 39166, 25544]
        df_filtered = df_celes[df_celes['NORAD_CAT_ID'].isin(target_ids)]
        
        DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))
        os.makedirs(DATA_DIR, exist_ok=True)
        csv_path = os.path.join(DATA_DIR, "real_celestrak_active.csv")
        df_filtered.to_csv(csv_path, index=False)
        print(f"Sucesso CelesTrak! {len(df_filtered)} satélites reais salvos em {csv_path}")
    else:
        print("Falha também no CelesTrak.")

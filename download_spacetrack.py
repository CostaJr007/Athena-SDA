"""
Download TLE history from Space-Track.org using environment credentials.

Required env vars (see .env.example):
  SPACETRACK_IDENTITY  — account email
  SPACETRACK_PASSWORD  — account password

Never hardcode credentials in this file.
"""
from __future__ import annotations

import datetime
import os
import sys

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import pandas as pd

IDENTITY = os.environ.get("SPACETRACK_IDENTITY", "").strip()
PASSWORD = os.environ.get("SPACETRACK_PASSWORD", "").strip()

if not IDENTITY or not PASSWORD:
    print(
        "Credenciais Space-Track ausentes.\n"
        "Defina SPACETRACK_IDENTITY e SPACETRACK_PASSWORD no ambiente ou no arquivo .env\n"
        "(veja .env.example)."
    )
    sys.exit(1)

try:
    from spacetrack import SpaceTrackClient
    import spacetrack.operators as op
except ImportError:
    print("Pacote 'spacetrack' não instalado. Rode: pip install spacetrack")
    sys.exit(1)

print("Autenticando no Space-Track.org via API oficial...")
st = SpaceTrackClient(identity=IDENTITY, password=PASSWORD)

targets = [44231, 43013, 25994, 41905, 43941, 43603, 39166, 25544]

start_date = datetime.date.today() - datetime.timedelta(days=40)
end_date = datetime.date.today() + datetime.timedelta(days=1)

print(f"Baixando histórico de TLEs de {start_date} até o presente...")

try:
    data = st.gp_history(
        norad_cat_id=targets,
        epoch=op.inclusive_range(start_date, end_date),
        orderby="EPOCH desc",
        format="csv",
    )

    if data:
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        csv_path = os.path.join(data_dir, "real_tle_history_2024_2026.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(data)
        df = pd.read_csv(csv_path)
        print(f"Sucesso. Dados salvos em: {csv_path}")
        print(f"Total de registros: {len(df)}")
        print(df.head())
    else:
        print("Consulta vazia. Verifique permissões da conta (GP History).")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Erro na API Space-Track: {e}")

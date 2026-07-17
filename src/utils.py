import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def parse_tle_line1(line1):
    """
    Faz o parse da linha 1 do formato TLE.
    Retorna: norad_id, classification, int_designator, epoch_year, epoch_day, bstar
    """
    try:
        norad_id = int(line1[2:7].strip())
        classification = line1[7]
        int_designator = line1[9:17].strip()
        epoch_year = int(line1[18:20])
        epoch_day = float(line1[20:32])
        # Bstar drag term (simplified parsing)
        bstar_str = line1[53:61].strip()
        if len(bstar_str) > 0:
            val = float(bstar_str[0:5]) / 100000.0
            exp = int(bstar_str[5:]) if len(bstar_str) > 5 else 0
            bstar = val * (10 ** exp)
        else:
            bstar = 0.0
        return {
            "norad_id": norad_id,
            "classification": classification,
            "int_designator": int_designator,
            "epoch_year": 2000 + epoch_year if epoch_year < 57 else 1900 + epoch_year,
            "epoch_day": epoch_day,
            "bstar": bstar
        }
    except Exception as e:
        raise ValueError(f"Erro ao parsear a linha 1 do TLE: {e}")

def parse_tle_line2(line2):
    """
    Faz o parse da linha 2 do formato TLE.
    Retorna: inclination, raan, eccentricity, arg_perigee, mean_anomaly, mean_motion
    """
    try:
        norad_id = int(line2[2:7].strip())
        inclination = float(line2[8:16])
        raan = float(line2[17:25])
        
        # Excentricidade do TLE tem o ponto decimal implícito na frente (7 dígitos)
        ecc_str = "0." + line2[26:33].strip()
        eccentricity = float(ecc_str)
        
        arg_perigee = float(line2[34:42])
        mean_anomaly = float(line2[43:51])
        mean_motion = float(line2[52:63]) # Voltas por dia
        
        return {
            "norad_id": norad_id,
            "inclination_deg": inclination,
            "raan_deg": raan,
            "eccentricity": eccentricity,
            "arg_perigee_deg": arg_perigee,
            "mean_anomaly_deg": mean_anomaly,
            "mean_motion_rev_per_day": mean_motion
        }
    except Exception as e:
        raise ValueError(f"Erro ao parsear a linha 2 do TLE: {e}")

def generate_mock_tle_history(norad_id, num_days=30, anomaly_type=None):
    """
    Gera histórico simulado de parâmetros orbitais de um satélite ao longo de X dias.
    Ideal para testar algoritmos de Hurst, Shannon, ADF, Cointegração e ML.
    
    anomaly_type:
      - None: Órbita Kepleriana normal estável (decaimento linear sutil por arrasto)
      - 'impulsive_maneuver': Uma mudança abrupta na altitude (manobra química clássica)
      - 'low_thrust_disguised': Pequena variação persistente (iônica) disfarçada
      - 'shadowing': Órbita que segue/cointegra com outra série temporal
    """
    np.random.seed(norad_id)
    
    # Parâmetros base da órbita
    base_sma = 6800.0 + np.random.uniform(-300, 300) # altitude média km (LEO)
    base_ecc = 0.001 + np.random.uniform(0.0, 0.005)
    base_inc = 51.6 + np.random.uniform(-10, 10)
    base_raan = np.random.uniform(0, 360)
    
    history = []
    
    # Arrasto sutil médio (decaimento)
    drag_rate = -0.01 / 30.0  # -10 metros por dia
    
    current_sma = base_sma
    
    for day in range(num_days):
        # Ruído Kepleriano normal de medição (Gaussiano sutil)
        noise = np.random.normal(0, 0.002) # +- 2 metros
        
        # Aplica decaimento natural
        current_sma += drag_rate + noise
        
        # Injeta anomalias/comportamentos intencionais
        if anomaly_type == 'impulsive_maneuver':
            # No dia 18, ocorre um aumento abrupto de 4 km (queima química)
            if day == 18:
                current_sma += 4.5
        elif anomaly_type == 'low_thrust_disguised':
            # A partir do dia 10, o motor iônico começa a empurrar continuamente +0.15 km/dia
            if day >= 10:
                current_sma += 0.15
        
        # Calcula movimento médio a partir do semi-eixo maior (3a Lei de Kepler)
        # mu = G*M_earth = 398600.4418 km^3/s^2
        # Periodo T = 2 * pi * sqrt(sma^3 / mu) em segundos
        # Voltas por dia = 86400 / T
        mu = 398600.4418
        period = 2 * np.pi * np.sqrt((current_sma ** 3) / mu)
        mean_motion = 86400.0 / period
        
        history.append({
            "day": day,
            "norad_id": norad_id,
            "semi_major_axis_km": current_sma,
            "eccentricity": base_ecc + np.random.normal(0, 0.0001),
            "inclination_deg": base_inc + np.random.normal(0, 0.001),
            "raan_deg": (base_raan + day * 0.05) % 360.0,
            "mean_motion_rev_per_day": mean_motion,
            "tle_age_hours": float(np.random.uniform(1, 12))
        })
        
    return pd.DataFrame(history)

def generate_shadowing_pair(norad_target, norad_spy, num_days=30):
    """
    Gera duas séries de altitudes cointegradas (RPO / shadowing).
    O espião copia a SMA do alvo com offset ~1.5 km + micro-correções
    (assinatura de baixo empuxo + Hurst alto).
    """
    df_target = generate_mock_tle_history(norad_target, num_days, anomaly_type=None)

    np.random.seed(norad_spy)
    df_spy = df_target.copy()
    df_spy["norad_id"] = norad_spy

    # Offset de proximidade tática + drift controlado (ionic-like)
    base_offset = 12.0  # km — within RPO watch box, not co-located
    offsets = base_offset + np.cumsum(np.random.normal(0.02, 0.03, num_days))
    # Keep bounded station-keeping around target
    offsets = base_offset + 0.4 * np.sin(np.linspace(0, 4 * np.pi, num_days)) + np.random.normal(0, 0.08, num_days)
    df_spy["semi_major_axis_km"] = df_target["semi_major_axis_km"].values + offsets
    # Match inclination/RAAN closely (same orbital plane pursuit)
    df_spy["inclination_deg"] = df_target["inclination_deg"].values + np.random.normal(0, 0.002, num_days)
    df_spy["raan_deg"] = df_target["raan_deg"].values + np.random.normal(0, 0.01, num_days)

    mu = 398600.4418
    periods = 2 * np.pi * np.sqrt((df_spy["semi_major_axis_km"] ** 3) / mu)
    df_spy["mean_motion_rev_per_day"] = 86400.0 / periods
    df_spy["tle_age_hours"] = np.random.uniform(2, 10, num_days)

    return df_target, df_spy

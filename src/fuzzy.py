import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

def setup_fuzzy_system():
    """
    Configura as variáveis linguísticas, funções de pertinência
    e base de regras fuzzy de acordo com a patente chinesa e doutrinas de SDA.
    """
    # === ANTECEDENTES (Entradas) ===
    # 1. Anomaly Score [0, 1]
    anomaly = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'anomaly')
    anomaly['baixo'] = fuzz.trapmf(anomaly.universe, [0, 0, 0.3, 0.5])
    anomaly['medio'] = fuzz.trimf(anomaly.universe, [0.3, 0.5, 0.7])
    anomaly['alto']  = fuzz.trapmf(anomaly.universe, [0.5, 0.7, 1.0, 1.0])

    # 2. Entropia de Shannon [0, 3.0]
    entropy_orb = ctrl.Antecedent(np.arange(0, 3.01, 0.01), 'entropy')
    entropy_orb['previsivel'] = fuzz.trapmf(entropy_orb.universe, [0, 0, 0.5, 1.0])
    entropy_orb['moderado']   = fuzz.trimf(entropy_orb.universe, [0.5, 1.0, 1.8])
    entropy_orb['caotico']    = fuzz.trapmf(entropy_orb.universe, [1.5, 2.0, 3.0, 3.0])

    # 3. Idade do TLE [0, 168h] (7 dias)
    tle_age = ctrl.Antecedent(np.arange(0, 169, 1), 'tle_age')
    tle_age['fresco']    = fuzz.trapmf(tle_age.universe, [0, 0, 24, 48])
    tle_age['degradado'] = fuzz.trimf(tle_age.universe, [24, 72, 120])
    tle_age['vencido']   = fuzz.trapmf(tle_age.universe, [72, 120, 168, 168])

    # 4. Distância de Satélite Militar [0, 500 km]
    dist_mil = ctrl.Antecedent(np.arange(0, 501, 1), 'dist_military')
    dist_mil['critico'] = fuzz.trapmf(dist_mil.universe, [0, 0, 10, 25])
    dist_mil['perto']   = fuzz.trimf(dist_mil.universe, [10, 50, 100])
    dist_mil['longe']   = fuzz.trapmf(dist_mil.universe, [50, 200, 500, 500])

    # 5. Complexidade de Kolmogorov [0, 1.0]
    kolmogorov = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'kolmogorov')
    kolmogorov['simples']  = fuzz.trapmf(kolmogorov.universe, [0, 0, 0.2, 0.4])
    kolmogorov['moderado'] = fuzz.trimf(kolmogorov.universe, [0.3, 0.5, 0.7])
    kolmogorov['complexo'] = fuzz.trapmf(kolmogorov.universe, [0.6, 0.8, 1.0, 1.0])

    # 6. Expoente de Hurst [0, 1.0]
    hurst = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'hurst')
    hurst['antipersistente'] = fuzz.trapmf(hurst.universe, [0, 0, 0.3, 0.5])
    hurst['ruido'] = fuzz.trimf(hurst.universe, [0.4, 0.5, 0.6])
    hurst['tendencia'] = fuzz.trapmf(hurst.universe, [0.5, 0.7, 1.0, 1.0])

    # === CONSEQUENTE (Saída) ===
    # Nível de Ameaça Final [0, 1.0]
    threat = ctrl.Consequent(np.arange(0, 1.01, 0.01), 'threat')
    threat['normal']   = fuzz.trapmf(threat.universe, [0, 0, 0.2, 0.35])
    threat['anomalo']  = fuzz.trimf(threat.universe, [0.2, 0.4, 0.55])
    threat['suspeito'] = fuzz.trimf(threat.universe, [0.4, 0.6, 0.8])
    threat['hostil']   = fuzz.trapmf(threat.universe, [0.65, 0.8, 1.0, 1.0])

    # === BASE DE REGRAS FUZZY ===
    rules = [
        # R1: Anomalia baixa + entropia previsível = NORMAL
        ctrl.Rule(anomaly['baixo'] & entropy_orb['previsivel'], threat['normal']),
        # R2: Anomalia média com TLE degradado/vencido = ANÔMALO (baixa confiança)
        ctrl.Rule(anomaly['medio'] & tle_age['vencido'], threat['anomalo']),
        # R3: Anomalia alta + TLE fresco + perto de militar + tendencia = HOSTIL
        ctrl.Rule(anomaly['alto'] & tle_age['fresco'] & dist_mil['critico'] & hurst['tendencia'], threat['hostil']),
        # R4: Órbita caótica + complexidade alta + tendencia = SUSPEITO
        ctrl.Rule(entropy_orb['caotico'] & kolmogorov['complexo'] & hurst['tendencia'], threat['suspeito']),
        # R5: Entropia alta + TLE fresco + distância perto = SUSPEITO
        ctrl.Rule(entropy_orb['caotico'] & tle_age['fresco'] & dist_mil['perto'], threat['suspeito']),
        # R6: Kolmogorov complexo + anomalia alta = HOSTIL (alta sofisticação)
        ctrl.Rule(kolmogorov['complexo'] & anomaly['alto'], threat['hostil']),
        # R7: TLE vencido sozinho atenua ameaça para ANÔMALO (aumenta incerteza)
        ctrl.Rule(tle_age['vencido'], threat['anomalo']),
        # R8: Distância crítica = SUSPEITO
        ctrl.Rule(dist_mil['critico'], threat['suspeito']),
        # R9: Anomalia baixa + Kolmogorov simples = NORMAL
        ctrl.Rule(anomaly['baixo'] & kolmogorov['simples'], threat['normal']),
        # R10: Caótico + Complexo + Crítico + Fresco = HOSTIL
        ctrl.Rule(entropy_orb['caotico'] & kolmogorov['complexo'] & dist_mil['critico'] & tle_age['fresco'], threat['hostil']),
    ]

    system = ctrl.ControlSystem(rules)
    return system, threat

# Inicializa o sistema uma vez para economia de processamento
_fuzzy_system, _threat_var = setup_fuzzy_system()

def fuzzy_inference_threat(features, min_dist_mil):
    """
    Executa a inferência fuzzy para estimar o nível de ameaça,
    a classificação qualitativa, a confiança e a ambiguidade.
    """
    sim = ctrl.ControlSystemSimulation(_fuzzy_system)
    
    # Alimenta as entradas "crisp" no sistema
    sim.input['anomaly'] = features.get('anomaly_score', 0.0)
    sim.input['entropy'] = features.get('shannon_entropy_sma_30d', 0.0)
    sim.input['tle_age'] = features.get('tle_age_hours', 12.0)
    sim.input['dist_military'] = min_dist_mil
    sim.input['kolmogorov'] = features.get('kolmogorov_proxy_7d', 0.0)
    sim.input['hurst'] = features.get('hurst_exponent_sma', 0.5)
    
    try:
        # Executa inferência fuzzy
        sim.compute()
        crisp_threat = float(sim.output['threat'])
    except Exception:
        # Fallback caso a inferência falhe devido a valores fora do suporte do universo
        crisp_threat = 0.0
        
    # Classificação baseada em limites de defuzzificação
    if crisp_threat < 0.35:
        classification = "NORMAL"
    elif crisp_threat < 0.55:
        classification = "ANÔMALO"
    elif crisp_threat < 0.8:
        classification = "SUSPEITO"
    else:
        classification = "HOSTIL"
        
    # Confiança: avalia o grau de pertinência na curva final
    memberships = {
        'NORMAL': float(fuzz.interp_membership(_threat_var.universe, _threat_var['normal'].mf, crisp_threat)),
        'ANÔMALO': float(fuzz.interp_membership(_threat_var.universe, _threat_var['anomalo'].mf, crisp_threat)),
        'SUSPEITO': float(fuzz.interp_membership(_threat_var.universe, _threat_var['suspeito'].mf, crisp_threat)),
        'HOSTIL': float(fuzz.interp_membership(_threat_var.universe, _threat_var['hostil'].mf, crisp_threat)),
    }
    
    confidence = memberships[classification]
    ambiguity = float(1.0 - confidence)
    
    return {
        "classification": classification,
        "threat_level": crisp_threat,
        "confidence": confidence,
        "ambiguity": ambiguity,
        "memberships": memberships
    }

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

    # === CONSEQUENT (Output) ===
    # Final Threat Level [0, 1.0]
    threat = ctrl.Consequent(np.arange(0, 1.01, 0.01), 'threat')
    threat['normal']   = fuzz.trapmf(threat.universe, [0, 0, 0.2, 0.35])
    threat['anomalo']  = fuzz.trimf(threat.universe, [0.2, 0.4, 0.55])
    threat['suspeito'] = fuzz.trimf(threat.universe, [0.4, 0.6, 0.8])
    threat['hostil']   = fuzz.trapmf(threat.universe, [0.65, 0.8, 1.0, 1.0])

    # === FUZZY RULE BASE ===
    rules = [
        # R1: Low anomaly + predictable entropy = NORMAL
        ctrl.Rule(anomaly['baixo'] & entropy_orb['previsivel'], threat['normal']),
        # R2: Medium anomaly + degraded TLE = ANOMALOUS (low confidence)
        ctrl.Rule(anomaly['medio'] & tle_age['vencido'], threat['anomalo']),
        # R3: High anomaly + fresh TLE + military proximity + trend = HOSTILE
        ctrl.Rule(anomaly['alto'] & tle_age['fresco'] & dist_mil['critico'] & hurst['tendencia'], threat['hostil']),
        # R4: Chaotic orbit + high complexity + trend = SUSPECT
        ctrl.Rule(entropy_orb['caotico'] & kolmogorov['complexo'] & hurst['tendencia'], threat['suspeito']),
        # R5: High entropy + fresh TLE + close proximity = SUSPECT
        ctrl.Rule(entropy_orb['caotico'] & tle_age['fresco'] & dist_mil['perto'], threat['suspeito']),
        # R6: Complex Kolmogorov + high anomaly = HOSTILE (high sophistication)
        ctrl.Rule(kolmogorov['complexo'] & anomaly['alto'], threat['hostil']),
        # R7: Stale TLE alone attenuates threat to ANOMALOUS
        ctrl.Rule(tle_age['vencido'], threat['anomalo']),
        # R8: Critical proximity = SUSPECT
        ctrl.Rule(dist_mil['critico'], threat['suspeito']),
        # R9: Low anomaly + simple Kolmogorov = NORMAL
        ctrl.Rule(anomaly['baixo'] & kolmogorov['simples'], threat['normal']),
        # R10: Chaotic + Complex + Critical + Fresh = HOSTILE
        ctrl.Rule(entropy_orb['caotico'] & kolmogorov['complexo'] & dist_mil['critico'] & tle_age['fresco'], threat['hostil']),
    ]

    system = ctrl.ControlSystem(rules)
    return system, threat

# Initialize system once for performance
_fuzzy_system, _threat_var = setup_fuzzy_system()

def fuzzy_inference_threat(features, min_dist_mil):
    """
    Executes fuzzy inference to estimate threat level,
    qualitative classification, confidence, and ambiguity.
    """
    sim = ctrl.ControlSystemSimulation(_fuzzy_system)
    
    # Clamp all crisp inputs to fuzzy universe supports (avoid silent fail → NORMAL)
    sim.input['anomaly'] = float(np.clip(features.get('anomaly_score', 0.0), 0.0, 1.0))
    sim.input['entropy'] = float(np.clip(features.get('shannon_entropy_sma_30d', 0.0), 0.0, 3.0))
    sim.input['tle_age'] = float(np.clip(features.get('tle_age_hours', 12.0), 0.0, 168.0))
    sim.input['dist_military'] = float(np.clip(float(min_dist_mil), 0.0, 500.0))
    sim.input['kolmogorov'] = float(np.clip(features.get('kolmogorov_proxy_7d', 0.0), 0.0, 1.0))
    sim.input['hurst'] = float(np.clip(features.get('hurst_exponent_sma', 0.5), 0.0, 1.0))
    
    try:
        # Compute fuzzy inference
        sim.compute()
        crisp_threat = float(sim.output['threat'])
    except Exception:
        # Fail-safe: uncertain/anomalous — never silent NORMAL (0.0)
        crisp_threat = 0.5
        
    # Classification based on defuzzification thresholds
    if crisp_threat < 0.35:
        classification = "NORMAL"
    elif crisp_threat < 0.55:
        classification = "ANOMALOUS"
    elif crisp_threat < 0.8:
        classification = "SUSPECT"
    else:
        classification = "HOSTILE"
        
    # Membership evaluation
    memberships = {
        'NORMAL': float(fuzz.interp_membership(_threat_var.universe, _threat_var['normal'].mf, crisp_threat)),
        'ANOMALOUS': float(fuzz.interp_membership(_threat_var.universe, _threat_var['anomalo'].mf, crisp_threat)),
        'SUSPECT': float(fuzz.interp_membership(_threat_var.universe, _threat_var['suspeito'].mf, crisp_threat)),
        'HOSTILE': float(fuzz.interp_membership(_threat_var.universe, _threat_var['hostil'].mf, crisp_threat)),
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

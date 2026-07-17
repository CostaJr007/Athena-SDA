import numpy as np
import pandas as pd
import zlib
from scipy.stats import entropy, wasserstein_distance, pareto
from sklearn.metrics.pairwise import rbf_kernel
from statsmodels.tsa.stattools import adfuller, coint

def calculate_shannon_entropy(sma_series, bins=10):
    """
    1. Entropia de Shannon (Shannon, 1948)
    Mede a desordem nas variações do semi-eixo maior.
    """
    if len(sma_series) < 2:
        return 0.0
    diffs = np.diff(sma_series)
    hist, _ = np.histogram(diffs, bins=bins)
    probs = hist / np.sum(hist)
    probs = probs[probs > 0]
    return float(entropy(probs, base=2))

def calculate_kolmogorov_proxy(sma_series):
    """
    2. Proxy de Complexidade de Kolmogorov (Kolmogorov, 1965)
    Usa compressão zlib como estimativa de complexidade algorítmica da trajetória.

    Returns value in [0, 1]; small expansion (compressed > raw) is clipped at 1.
    """
    if len(sma_series) < 2:
        return 0.0
    diffs = np.diff(sma_series)
    threshold = 0.02  # 20 metros para discretização
    tokens = []
    for d in diffs:
        if d > threshold:
            tokens.append("U")
        elif d < -threshold:
            tokens.append("D")
        else:
            tokens.append("S")

    s = "".join(tokens).encode("utf-8")
    if len(s) == 0:
        return 0.0
    compressed = zlib.compress(s)
    return float(np.clip(len(compressed) / len(s), 0.0, 1.0))

def calculate_hurst_exponent(series, max_lag=20):
    """
    3. Expoente de Hurst (Hurst, 1951)
    Mede a persistência de longo prazo na variação da altitude (R/S Analysis).
    H > 0.5: Tendência contínua persistente (propulsão ativa de baixo empuxo).
    H < 0.5: Reversão à média (manutenção de órbita padrão / ruído).
    """
    n = len(series)
    if n < 10:
        return 0.5
    lags = range(2, min(max_lag, n // 2))
    rs_values = []
    for lag in lags:
        n_segments = n // lag
        rs = []
        for i in range(n_segments):
            segment = series[i * lag : (i + 1) * lag]
            mean = np.mean(segment)
            std = np.std(segment)
            if std == 0:
                continue
            deviations = segment - mean
            cum_dev = np.cumsum(deviations)
            R = np.max(cum_dev) - np.min(cum_dev)
            rs.append(R / std)
        if len(rs) > 0:
            rs_values.append(np.mean(rs))
    if len(rs_values) < 2:
        return 0.5
    H = np.polyfit(np.log(list(lags[:len(rs_values)])), np.log(rs_values), 1)[0]
    return float(np.clip(H, 0.0, 1.0))

def calculate_ricci_proxy(pos_x, neighbors_x, pos_y, neighbors_y):
    """
    4. Curvatura de Ricci de Ollivier (Ollivier, 2007)
    Mede a curvatura de vizinhança entre dois satélites (convergência espacial).
    """
    d_xy = np.linalg.norm(pos_x - pos_y)
    if d_xy == 0:
        return 0.0
    
    # Distâncias médias locais dos vizinhos em relação a x e y
    dist_x = np.linalg.norm(neighbors_x - pos_x, axis=1) if len(neighbors_x) > 0 else np.array([0.0])
    dist_y = np.linalg.norm(neighbors_y - pos_y, axis=1) if len(neighbors_y) > 0 else np.array([0.0])
    
    w1 = wasserstein_distance(dist_x, dist_y)
    return float(1.0 - (w1 / d_xy))

def calculate_persistent_homology(positions_3d):
    """
    5. Homologia Persistente (TDA - Edelsbrunner, 2002)
    Estrutura topológica de um enxame ou janela orbital.

    Uses ripser when installed; otherwise a lightweight pairwise-distance
    proxy that still yields stable h0/h1-like scalars for the ML vector.
    """
    positions_3d = np.asarray(positions_3d, dtype=float)
    if len(positions_3d) < 5:
        return 1.0, 0.0  # (h0_pers, h1_pers)

    try:
        from ripser import ripser
        dgms = ripser(positions_3d, maxdim=1)["dgms"]
        h0 = dgms[0]
        h1 = dgms[1]
        h0_pers = np.mean([d[1] - d[0] for d in h0 if np.isfinite(d[1])]) if len(h0) > 0 else 1.0
        h1_pers = np.mean([d[1] - d[0] for d in h1]) if len(h1) > 0 else 0.0
        return float(h0_pers), float(h1_pers)
    except Exception:
        # Fallback proxy: scale-normalized pairwise distance stats
        # h0 ~ mean nearest-neighbor distance; h1 ~ spread of cycle scale
        from scipy.spatial.distance import pdist
        d = pdist(positions_3d)
        if len(d) == 0:
            return 1.0, 0.0
        # Normalize by orbital radius scale
        scale = max(np.linalg.norm(positions_3d, axis=1).mean(), 1.0)
        d_n = d / scale
        h0_pers = float(np.percentile(d_n, 10))
        h1_pers = float(np.clip(np.percentile(d_n, 75) - np.percentile(d_n, 25), 0.0, 2.0))
        return h0_pers, h1_pers

def calculate_chern_simons_proxy(positions, velocities):
    """
    6. Chern-Simons Proxy (Chern-Simons, 1974)
    Mede a quebra de conservação do momento angular específico orbital.
    """
    if len(positions) < 2:
        return 0.0
    # h = r x v (momento angular específico)
    h_vectors = np.cross(positions, velocities)
    h0 = h_vectors[0]
    norm_h0 = np.linalg.norm(h0)
    if norm_h0 == 0:
        return 0.0
    diffs = np.linalg.norm(h_vectors - h0, axis=1)
    return float(np.max(diffs) / norm_h0)

def calculate_spectral_anomaly_rkhs(features_vector, reference_matrix, gamma=0.1):
    """
    7. Anomalia Espectral em RKHS (David Hilbert)
    Mede a typicalidade da distribuição de features em um Espaço de Hilbert de Kernel Reprodutor.
    """
    if len(reference_matrix) == 0:
        return 1.0
    x = features_vector.reshape(1, -1)
    sims = rbf_kernel(x, reference_matrix, gamma=gamma)
    return float(1.0 - np.max(sims))

def calculate_lukasiewicz_implication(val_p, val_q):
    """
    9. Lógica Łukasiewicz (Łukasiewicz, 1920)
    Implicação fuzzy para validação lógica de teses.
    """
    return float(min(1.0, 1.0 - val_p + val_q))

def calculate_kelly_allocation(threat_prob, severity_multiplier):
    """
    10. Critério de Kelly (Kelly, 1956)
    Otimiza o sizing da alocação de tempo do sensor.
    """
    p = threat_prob
    q = 1.0 - p
    b = severity_multiplier
    if b <= 0:
        return 0.0
    f_star = (p * b - q) / b
    return float(max(0.0, f_star * 0.5)) # Half-Kelly para amortecer volatilidade

def calculate_williams_threat(country, purpose, orbit_class, inclination):
    """
    11. Valor Intrínseco de Williams (Williams, 1938)
    Avalia a vulnerabilidade/ameaça estratégica estática.
    """
    score = 0.0
    adversaries = ['CN', 'RU', 'KP', 'IR']
    if country in adversaries:
        score += 0.35
    elif country not in ['US', 'UK', 'FR', 'CA', 'DE']:
        score += 0.1
    
    military_purposes = ['military', 'sigint', 'asat_test', 'reconnaissance']
    if purpose in military_purposes:
        score += 0.45
    elif purpose in ['commercial', 'scientific']:
        score += 0.05
    
    # Órbita Polar LEO é indicadora clássica de escaneamento militar
    if orbit_class == 'LEO' and inclination > 55:
        score += 0.2
        
    return float(np.clip(score, 0.0, 1.0))

def calculate_kernel_smoothing(time_indices, values, bandwidth=1.5):
    """
    12. Suavização por Regressão de Kernel (Lo et al., 2000)
    Filtro Nadaraya-Watson com kernel Gaussiano para limpar ruído orbital.
    """
    n = len(values)
    smoothed = np.zeros(n)
    for i, t in enumerate(time_indices):
        diffs = (t - time_indices) / bandwidth
        weights = np.exp(-0.5 * diffs**2)
        sum_w = np.sum(weights)
        smoothed[i] = np.sum(weights * values) / sum_w if sum_w > 0 else values[i]
    return smoothed

def calculate_kernel_l1_cusum(series, window=30, threshold=3.5):
    """
    13. Algoritmo L1-CUSUM Kernelizado
    Detecta quebras estruturais cumulativas na variação orbital.
    """
    if len(series) < window:
        return 0.0
    baseline = np.median(series[-window:])
    mad = np.median(np.abs(series[-window:] - baseline))
    if mad == 0:
        mad = 1e-6
    
    current = series[-1]
    z_score = np.abs(current - baseline) / mad
    
    if z_score > 1.0:
        kernel_weight = 0.0
    else:
        kernel_weight = 0.75 * (1 - z_score**2)
        
    cusum = np.sum(kernel_weight * np.abs(np.array(series[-10:]) - baseline)) / mad
    return float(np.clip(cusum / threshold, 0.0, 1.0))

def calculate_mandelbrot_tail_anomaly(series, quantile=90):
    """
    14. Anomalias de Cauda Pesada de Mandelbrot (Mandelbrot, 1963)
    Usa a distribuição de cauda pesada de Pareto para detectar anomalias raras.
    """
    if len(series) < 15:
        return 0.0
    threshold = np.percentile(series, quantile)
    tail_data = series[series >= threshold]
    if len(tail_data) < 2 or np.all(tail_data == threshold):
        return 0.0
    
    # Estimador de Hill para o alfa de cauda
    alpha = len(tail_data) / np.sum(np.log(tail_data / threshold))
    current = series[-1]
    if current < threshold:
        return 0.0
    
    p_val = (current / threshold) ** (-alpha)
    return float(1.0 - p_val)

def calculate_adf_pvalue(series):
    """
    15. Teste de Raiz Unitária de Dickey-Fuller Aumentado (ADF)
    p-value > 0.05 -> Não-estacionário (indício forte de manobras de baixo empuxo).
    p-value <= 0.05 -> Estacionário (satélite passivo decaindo normalmente).
    """
    if len(series) < 20:
        return 0.0  # Dados insuficientes
    try:
        result = adfuller(series, regression='ct')
        p_value = result[1]
        return float(p_value)
    except Exception:
        return 0.5

def calculate_cointegration_pvalue(series_a, series_b):
    """
    16. Teste de Cointegração de Engle-Granger
    p-value < 0.05 -> Cointegrados (perseguição / shadowing tático comprovado).
    p-value >= 0.05 -> órbitas independentes normais.
    """
    if len(series_a) < 20 or len(series_b) < 20:
        return 1.0
    try:
        _, p_value, _ = coint(series_a, series_b, trend='c')
        return float(p_value)
    except Exception:
        return 1.0

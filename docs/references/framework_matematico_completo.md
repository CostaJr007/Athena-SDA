# Framework Matemático Completo — Athena-SDA

Este documento serve como referência de engenharia e modelagem para o **Athena-SDA**, unindo 16 teorias estatísticas, matemáticas e econômicas para a detecção de anomalias orbitais, identificação de manobras de baixíssimo empuxo e detecção de satélites espiões (aproximação e shadowing).

---

## 1. Entropia de Shannon (Previsibilidade Orbital)
* **Teoria:** Claude Shannon (1948)
* **Objetivo:** Quantificar o nível de desordem ou incerteza no comportamento do semi-eixo maior ($a$).

### Formulação Matemática
Dada uma série temporal de variações diárias do semi-eixo maior $\Delta a_t = a_t - a_{t-1}$, discretizamos esses valores em $N$ caixas (bins) de histograma para aproximar a distribuição de probabilidade empírica $P(x_i)$. A Entropia de Shannon é dada por:

$$H(X) = -\sum_{i=1}^{N} P(x_i) \log_2 P(x_i)$$

### Justificativa Física (SDA)
* **Órbita Kepleriana Passiva:** O satélite apenas decai devido a forças gravitacionais e arrasto atmosférico regular. A variação $\Delta a_t$ é altamente concentrada em poucas caixas. $H(X) \to 0$ (alta ordem/previsibilidade).
* **Órbita com Manobras Ativas:** As variações diárias de altitude são distribuídas de forma errática devido a ignições ocasionais. $H(X) > 1.8$ (alta desordem/caos).

### Implementação em Python
```python
import numpy as np
from scipy.stats import entropy

def shannon_entropy_sma(sma_series, bins=10):
    if len(sma_series) < 2:
        return 0.0
    diffs = np.diff(sma_series)
    hist, _ = np.histogram(diffs, bins=bins)
    probs = hist / np.sum(hist)
    # Remove probabilidades nulas
    probs = probs[probs > 0]
    return entropy(probs, base=2)
```

---

## 2. Complexidade de Kolmogorov (Detecção de Controle Algorítmico)
* **Teoria:** Andrey Kolmogorov (1965)
* **Objetivo:** Avaliar se a trajetória orbital é descrita por leis físicas simples ou por um algoritmo dinâmico de controle de guiamento.

### Formulação Matemática
A complexidade de Kolmogorov $K(s)$ é o tamanho do menor programa $p$ que gera a string $s$ em uma máquina de Turing Universal. Como $K(s)$ é indecidível, usamos um compressor sem perdas (como `zlib`) como limite superior (proxy):

$$K_{\text{proxy}}(s) = \frac{\text{Len}(\text{Compress}(s))}{\text{Len}(s)}$$

### Justificativa Física (SDA)
* **Deriva Natural:** A trajetória do satélite é descrita por equações físicas simples de propagação (baixo fluxo de informação). A representação discretizada da direção do movimento comprime muito bem ($K_{\text{proxy}} \to 0$).
* **Manobras Evasivas ou RPO:** O satélite executa micro-correções frequentes baseadas em sensores, criando uma cadeia de estados pseudo-aleatória que resiste à compressão ($K_{\text{proxy}} \to 1$).

### Implementação em Python
```python
import zlib

def kolmogorov_complexity_proxy(sma_series):
    if len(sma_series) < 2:
        return 0.0
    diffs = np.diff(sma_series)
    # Codifica a série em tokens: U (Up), D (Down), S (Stable)
    threshold = 0.05  # 50 metros
    tokens = []
    for d in diffs:
        if d > threshold:
            tokens.append("U")
        elif d < -threshold:
            tokens.append("D")
        else:
            tokens.append("S")
    
    s = "".join(tokens).encode('utf-8')
    if len(s) == 0:
        return 0.0
    compressed = zlib.compress(s)
    return len(compressed) / len(s)
```

---

## 3. Expoente de Hurst (Memória de Longo Prazo e R/S)
* **Teoria:** Harold Edwin Hurst (1951)
* **Objetivo:** Identificar se o movimento orbital possui tendência ativa de longo prazo (propulsão elétrica de baixo empuxo).

### Formulação Matemática
A análise de Faixa Redimensionada (R/S) é realizada dividindo a amplitude cumulativa desfiada da média pelo desvio padrão em janelas de tamanho $n$:

$$E \left[ \frac{R(n)}{S(n)} \right] = C \cdot n^H$$

* **$H < 0.5$:** Anti-persistente (reversão à média - manutenção de órbita padrão/station-keeping).
* **$H = 0.5$:** Caminhada aleatória pura (ruído branco Kepleriano).
* **$H > 0.5$:** Persistente (comportamento de busca de alvo / transferência orbital ativa).

### Implementação em Python
```python
def hurst_exponent(series, max_lag=20):
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
    return np.clip(H, 0.0, 1.0)
```

---

## 4. Curvatura de Ricci de Ollivier (Anomalias de Grafo Orbital)
* **Teoria:** Yann Ollivier (2007)
* **Objetivo:** Detectar convergências e distorções espaciais na vizinhança geométrica de uma constelação.

### Formulação Matemática
A curvatura de Ricci $\kappa(x, y)$ entre dois nós (satélites) no grafo geométrico é calculada usando a distância de transporte de Wasserstein-1 ($W_1$) entre as medidas de probabilidade das vizinhanças dos nós:

$$\kappa(x, y) = 1 - \frac{W_1(m_x, m_y)}{d(x, y)}$$

### Justificativa Física (SDA)
* **Estrutura Regular:** Em constelações estáveis (ex: GPS), os satélites mantêm distâncias constantes. A curvatura é estável e homogênea.
* **Aproximação Hostil:** Um satélite invasor entra na vizinhança, mudando o fluxo de transporte local de forma atípica, fazendo $\kappa(x, y)$ assumir valores positivos na direção do alvo.

### Implementação em Python
```python
from scipy.stats import wasserstein_distance

def ollivier_ricci_proxy(pos_x, neighbors_x, pos_y, neighbors_y):
    """
    Aproximação discreta da curvatura de Ricci usando Wasserstein 1D
    sobre as distâncias dos vizinhos em relação aos nós centrais.
    """
    d_xy = np.linalg.norm(pos_x - pos_y)
    if d_xy == 0:
        return 0.0
    
    # Medida empírica dos vizinhos
    dist_x = np.linalg.norm(neighbors_x - pos_x, axis=1)
    dist_y = np.linalg.norm(neighbors_y - pos_y, axis=1)
    
    w1 = wasserstein_distance(dist_x, dist_y)
    return 1.0 - (w1 / d_xy)
```

---

## 5. Homologia Persistente (TDA - Análise de Dados Topológicos)
* **Teoria:** Herbert Edelsbrunner (2002)
* **Objetivo:** Detectar deformações estruturais de longo prazo nas trajetórias de nuvens de pontos 3D.

### Formulação Matemática
Construímos a filtração de Vietoris-Rips $VR(P, \epsilon)$ variando o raio de conectividade $\epsilon$ sobre os pontos tridimensionais de posição orbital do satélite:

$$VR(P, \epsilon) = \{ \sigma \subseteq P : \text{diam}(\sigma) \le \epsilon \}$$

Acompanhamos o ciclo $H_1$ (loops 1D) ao longo da filtração para mapear sua persistência (nascimento e morte).

### Implementação em Python
```python
from ripser import ripser

def persistent_homology_features(positions_3d):
    """
    Mede a persistência topológica (H0 e H1) de um enxame ou trajetória
    """
    if len(positions_3d) < 5:
        return {'h0_persistent': 1, 'h1_persistent': 0}
    
    dgms = ripser(positions_3d, maxdim=1)['dgms']
    h0 = dgms[0]
    h1 = dgms[1]
    
    # Persistência média de H0 (componentes conexas) e H1 (loops)
    h0_pers = np.mean([d[1] - d[0] for d in h0 if np.isfinite(d[1])]) if len(h0) > 0 else 0
    h1_pers = np.mean([d[1] - d[0] for d in h1]) if len(h1) > 0 else 0
    
    return {
        'h0_persistent': h0_pers,
        'h1_persistent': h1_pers
    }
```

---

## 6. Chern-Simons Proxy (Não-Conservação do Campo Orbital)
* **Teoria:** Chern-Simons (1974)
* **Objetivo:** Medir a atuação de forças propulsoras não-conservativas (químicas ou iônicas).

### Formulação Matemática
O momento angular específico $\vec{h} = \vec{r} \times \vec{v}$ é um vetor conservado para uma órbita Kepleriana pura (campo gravitacional conservativo). A perturbação no momento angular é usada como proxy topológico de Chern-Simons:

$$\text{CS}_{\text{proxy}} = \frac{\max \|\vec{h}_t - \vec{h}_0\|}{\|\vec{h}_0\|}$$

### Implementação em Python
```python
def chern_simons_angular_momentum(positions, velocities):
    if len(positions) < 2:
        return 0.0
    # Calcula momento angular específico h = r x v
    h_vectors = np.cross(positions, velocities)
    h0 = h_vectors[0]
    norm_h0 = np.linalg.norm(h0)
    if norm_h0 == 0:
        return 0.0
    # Desvio máximo da baseline
    diffs = np.linalg.norm(h_vectors - h0, axis=1)
    return np.max(diffs) / norm_h0
```

---

## 7. Anomalia Espectral em Espaço de Hilbert (RKHS)
* **Teoria:** David Hilbert (~1900)
* **Objetivo:** Detectar mudanças de distribuição orbital mapeando as features em dimensões infinitas.

### Formulação Matemática
Usamos o kernel Gaussiano RBF $k(x, y) = \exp(-\gamma \|x - y\|^2)$ para computar a similaridade das features no espaço de Hilbert e avaliamos a norma de similaridade com um conjunto estável de referência:

$$\text{Anomalia} = 1.0 - \max_j k(x, x_{\text{ref}, j})$$

### Implementação em Python
```python
from sklearn.metrics.pairwise import rbf_kernel

def spectral_anomaly_rkhs(features_vector, reference_matrix, gamma=0.1):
    if reference_matrix.shape[0] == 0:
        return 1.0
    x = features_vector.reshape(1, -1)
    sims = rbf_kernel(x, reference_matrix, gamma=gamma)
    return 1.0 - np.max(sims)
```

---

## 8. Lógica Fuzzy de Mamdani (Inferência sob Incerteza)
* **Teoria:** Lotfi A. Zadeh (1965)
* **Objetivo:** Agregar múltiplos scores de ML e features matemáticas sob incerteza de medição.

### Formulação Matemática
Dada a entrada contínua $x$, calcula-se o grau de pertinência $\mu_A(x) \in [0, 1]$. As regras de inferência são agregadas e o valor de saída nítido é defuzzificado pelo centroide:

$$z^* = \frac{\int z \cdot \mu_C(z) dz}{\int \mu_C(z) dz}$$

### Implementação em Python
```python
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# Setup básico do sistema de controle Fuzzy
anomaly = ctrl.Antecedent(np.arange(0, 1.01, 0.01), 'anomaly')
anomaly['baixo'] = fuzz.trapmf(anomaly.universe, [0, 0, 0.3, 0.5])
anomaly['medio'] = fuzz.trimf(anomaly.universe, [0.3, 0.5, 0.7])
anomaly['alto']  = fuzz.trapmf(anomaly.universe, [0.5, 0.7, 1.0, 1.0])

# Variáveis e regras são inicializadas no módulo fuzzy.py
```

---

## 9. Lógica Łukasiewicz (Validação Lógica de Teses)
* **Teoria:** Jan Łukasiewicz (1920)
* **Objetivo:** Verificar a consistência de hipóteses aeroespaciais contínuas (ex: "Satélite A está se comportando de forma anômala implica que ele está realizando RPO").

### Formulação Matemática
A verdade da implicação de Łukasiewicz $I(p, q)$ opera sobre valores lógicos contínuos no intervalo $[0, 1]$:

$$v(p \rightarrow q) = \min(1, 1 - v(p) + v(q))$$

### Implementação em Python
```python
def lukasiewicz_implication(val_p, val_q):
    return min(1.0, 1.0 - val_p + val_q)
```

---

## 10. Critério de Kelly (Priorização e Alocação Sizing)
* **Teoria:** John Larry Kelly, Jr. (1956)
* **Objetivo:** Sintonizar o foco e tempo de varredura de sensores (radares/telescópios) nos satélites com alertas mais valiosos.

### Formulação Matemática
A fração ideal de tempo de rastreamento $f^*$ para um objeto específico é:

$$f^* = \frac{p \cdot b - q}{b}$$

* **$p$:** Probabilidade da ameaça ser real (fuzzy confidence $\times$ threat level).
* **$q = 1.0 - p$:** Probabilidade de ser falso positivo.
* **$b$:** Severidade do alvo (odds multiplicador: militar=100, civil=5).

### Implementação em Python
```python
def kelly_resource_allocation(threat_prob, severity_multiplier):
    p = threat_prob
    q = 1.0 - p
    b = severity_multiplier
    if b <= 0:
        return 0.0
    f_star = (p * b - q) / b
    return max(0.0, f_star * 0.5)  # Half-Kelly para estabilidade
```

---

## 11. Valor Intrínseco de Williams (Ameaça Heurística Estática)
* **Teoria:** John Burr Williams (1938)
* **Objetivo:** Avaliar a vulnerabilidade geopolítica estática intrínseca do satélite.

### Formulação Matemática
Atribui um peso estático com base nas propriedades fixas do satélite: país proprietário (aliados vs adversários), tipo de órbita (LEO Polar vs LEO Equatorial) e finalidade da missão (SIGINT/Reconhecimento vs Telecomunicações civil).

### Implementação em Python
```python
def williams_intrinsic_threat(country, purpose, orbit_class, inclination):
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
    
    # Órbita LEO Polar é típica de satélites espiões de alta resolução
    if orbit_class == 'LEO' and inclination > 55:
        score += 0.2
        
    return np.clip(score, 0.0, 1.0)
```

---

## 12. Suavização por Regressão de Kernel (Filtro de Ruído Harmônico)
* **Teoria:** Lo et al. (2000)
* **Objetivo:** Suavizar as séries de coordenadas para eliminar perturbações orbitais harmônicas secundárias ou erros pontuais de medição do TLE.

### Formulação Matemática
Usamos o estimador de Nadaraya-Watson com kernel Gaussiano $K_h$:

$$\hat{m}(t) = \frac{\sum_{i=1}^{n} K_h(t - t_i) Y_i}{\sum_{i=1}^{n} K_h(t - t_i)}$$

### Implementação em Python
```python
def kernel_smoothing_nadaraya_watson(time_indices, values, bandwidth=1.5):
    n = len(values)
    smoothed = np.zeros(n)
    for i, t in enumerate(time_indices):
        diffs = (t - time_indices) / bandwidth
        weights = np.exp(-0.5 * diffs**2)  # Kernel Gaussiano
        sum_w = np.sum(weights)
        smoothed[i] = np.sum(weights * values) / sum_w if sum_w > 0 else values[i]
    return smoothed
```

---

## 13. Algoritmo L1-CUSUM Kernelizado
* **Objetivo:** Detectar quebras estruturais abruptas na variação da órbita de forma estatisticamente robusta.

### Formulação Matemática
Usamos a mediana e o desvio absoluto mediano (MAD) sob o kernel Epanechnikov para evitar que outliers isolados disparem alarmes falsos de manobra:

$$z_t = \frac{|x_t - \text{median}|}{\text{MAD} + \epsilon}$$

### Implementação em Python
```python
def kernel_l1_cusum_robust(series, window=30, threshold=3.5):
    if len(series) < window:
        return 0.0
    baseline = np.median(series[-window:])
    mad = np.median(np.abs(series[-window:] - baseline))
    if mad == 0:
        mad = 1e-6
    
    current = series[-1]
    z_score = np.abs(current - baseline) / mad
    
    # Kernel Epanechnikov
    if z_score > 1.0:
        kernel_weight = 0.0
    else:
        kernel_weight = 0.75 * (1 - z_score**2)
        
    cusum = np.sum(kernel_weight * np.abs(np.array(series[-10:]) - baseline)) / mad
    return np.clip(cusum / threshold, 0.0, 1.0)
```

---

## 14. Anomalias de Cauda Pesada de Mandelbrot
* **Teoria:** Benoit Mandelbrot (1963)
* **Objetivo:** Modelar as caudas das variações orbitais por meio de distribuições de cauda pesada de Pareto.

### Formulação Matemática
As variações orbitais naturais seguem distribuições Gaussianas, mas manobras deliberadas produzem eventos extremos que violam essa suposição. Ajustamos uma distribuição de Pareto à cauda superior:

$$P(X > x) \sim \left( \frac{x_{\text{min}}}{x} \right)^\alpha$$

### Implementação em Python
```python
from scipy.stats import pareto

def mandelbrot_tail_anomaly(series, quantile=90):
    if len(series) < 15:
        return 0.0
    threshold = np.percentile(series, quantile)
    tail_data = series[series >= threshold]
    if len(tail_data) < 2 or np.all(tail_data == threshold):
        return 0.0
    
    # Estimador de Hill para o parâmetro alfa de cauda
    alpha = len(tail_data) / np.sum(np.log(tail_data / threshold))
    current = series[-1]
    if current < threshold:
        return 0.0
    
    # P-value sob distribuição Pareto
    p_val = (current / threshold) ** (-alpha)
    return 1.0 - p_val
```

---

## 15. Teste de Raiz Unitária de Dickey-Fuller Aumentado (ADF)
* **Teoria:** David Dickey, Wayne Fuller (1979)
* **Objetivo:** Detectar a perda de estacionaridade na série de resíduos orbitais detendenciados, assinalando o início de micro-manobras ativas.

### Formulação Matemática
O teste ADF ajusta um modelo de regressão linear para a primeira diferença da série orbital para testar a presença de raiz unitária ($\gamma = 0$):

$$\Delta y_t = \alpha + \beta t + \gamma y_{t-1} + \sum_{i=1}^{p} \delta_i \Delta y_{t-i} + \epsilon_t$$

* **Hipótese Nula ($H_0$):** A série possui raiz unitária (não estacionária - satélite está mudando ativamente de órbita).
* **Hipótese Alternativa ($H_1$):** A série é estacionária (satélite apenas decaindo passivamente).

### Implementação em Python
```python
from statsmodels.tsa.stattools import adfuller

def adf_stationarity_pvalue(series):
    """
    Retorna o p-value do teste ADF.
    p-value > 0.05 -> Não-estacionário (indício de mudança de comportamento/manobra).
    p-value <= 0.05 -> Estacionário (satélite passivo/Kepleriano estável).
    """
    if len(series) < 20:
        return 0.0  # Sem dados suficientes para testar
    try:
        # Executa ADF com regressão contendo constante e tendência
        result = adfuller(series, regression='ct')
        p_value = result[1]
        return p_value
    except Exception:
        return 0.5  # Em caso de erro numérico, retorna indecisão
```

---

## 16. Teste de Cointegração de Engle-Granger (RPO/Shadowing Detection)
* **Teoria:** Robert Engle, Clive Granger (1987)
* **Objetivo:** Detectar perseguição física (shadowing) entre dois satélites calculando se a diferença de suas altitudes é estacionária no longo prazo.

### Formulação Matemática
Dadas duas séries de altitudes não-estacionárias $y_{A, t}$ e $y_{B, t}$ (que decaem independentemente por arrasto), rodamos uma regressão ordinária de mínimos quadrados (OLS):

$$y_{A, t} = \beta y_{B, t} + u_t$$

Em seguida, testamos a estacionaridade dos resíduos estimados $\hat{u}_t$ usando o teste ADF. Se $\hat{u}_t$ for estacionário, as séries são **cointegradas**, significando que a distância entre eles é mantida ativa e precisamente sob controle de malha fechada.

### Implementação em Python
```python
from statsmodels.tsa.stattools import coint

def check_orbital_cointegration(series_a, series_b):
    """
    Verifica se a trajetória de dois satélites está cointegrada.
    Retorna p-value do teste de Engle-Granger.
    p-value < 0.05 -> Cointegrados (Satélite A está ativamente seguindo/espionando B).
    p-value >= 0.05 -> Não-cointegrados (Órbitas independentes que divergem).
    """
    if len(series_a) < 20 or len(series_b) < 20:
        return 1.0
    try:
        # O teste retorna estatística de teste, p-value e valores críticos
        score, p_value, _ = coint(series_a, series_b, trend='c')
        return p_value
    except Exception:
        return 1.0
```

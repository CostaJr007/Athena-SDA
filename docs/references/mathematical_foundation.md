# Mathematical Foundation of the Athena-SDA Project

This document details the mathematical framework behind the 14 theories integrated into **Athena-SDA** for orbital anomaly detection, trajectory analysis, and decision-making under uncertainty.

---

## 1. Shannon Entropy (Orbital Information Disorder)
* **Theory:** Claude Shannon (1948)
* **Objective:** Measure disorder and unpredictability in orbital parameter time series.

Shannon entropy for a discrete random variable $X$ with states $x_1, ..., x_n$ is defined as:

$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$

### Application in Satellite Tracking
We analyze variations in Semi-Major Axis ($a$) over a rolling 30-day window. Daily variations $\Delta a_t = a_t - a_{t-1}$ are binned to estimate probabilities $P(x_i)$.
* **Stable Keplerian Orbit:** Natural perturbation baseline. Probability is concentrated in few bins ($H(X) \approx 0.2$).
* **Active Maneuvering:** Intentionally altered altitude spreads variations across multiple bins, elevating entropy ($H(X) > 1.8$).

---

## 2. Kolmogorov Complexity Proxy (Algorithmic Intent Detection)
* **Theory:** Andrey Kolmogorov (1965)
* **Objective:** Determine if a trajectory is governed by passive celestial mechanics or an active control algorithm.

The Kolmogorov complexity $K(s)$ of string $s$ is the length of the shortest program $p$ running on a Universal Turing Machine $U$ that outputs $s$:

$$K(s) = \min \{ |p| : U(p) = s \}$$

### Application in Satellite Tracking
Since $K(s)$ is non-computable, lossless compression size (zlib/LZW) serves as an algorithmic complexity proxy:

$$K_{\text{proxy}}(s) = \frac{\text{Size}(\text{Compress}(s))}{\text{Size}(s)}$$

* Natural orbits compress efficiently ($K_{\text{proxy}} \to 0$).
* Complex evasive or rendezvous maneuvers yield higher algorithmic entropy ($K_{\text{proxy}} \to 1$).

---

## 3. Hurst Exponent (Long-Memory & Rescaled Range R/S Analysis)
* **Theory:** Harold Edwin Hurst (1951)
* **Objective:** Distinguish natural atmospheric drag decay from persistent electric/ion propulsion.

$$E \left[ \frac{R(n)}{S(n)} \right] = C \cdot n^H$$

* **$H = 0.5$:** Uncorrelated Brownian motion (random walk).
* **$0.5 < H \le 1.0$:** Persistent time series (long-term memory/trend).
* **$0 \le H < 0.5$:** Anti-persistent time series (mean-reverting).

---

## 4. Ollivier-Ricci Curvature (Constellation Graph Anomaly Detection)
* **Theory:** Yann Ollivier (2007)
* **Objective:** Detect local deformations in satellite constellations caused by non-cooperative orbital proximity.

$$\kappa(x, y) = 1 - \frac{W_1(m_x, m_y)}{d(x, y)}$$

---

## 5. Persistent Homology (Topological Data Analysis - TDA)
* **Theory:** Herbert Edelsbrunner (2002)
* **Objective:** Detect structural trajectory topological shifts in 3D point cloud embeddings.

Simplicial homology groups $H_k$:
* **$H_0$:** Connected components (physical clustering of assets).
* **$H_1$:** 1D loops/tunnels (circular/elliptical orbital periodicity).

---

## 6. Chern-Simons Proxy (Non-Conservative Force Field Signatures)
* **Theory:** Shiing-Shen Chern, James Harris Simons (1974)
* **Objective:** Detect non-conservative propulsive forces in orbital dynamics.

$$CS = \int_{t_0}^{t_1} (\vec{v} \cdot \vec{\omega}) dt$$

---

## 7. Spectral Anomaly in RKHS (Hilbert Space Typicality)
* **Theory:** Reproducing Kernel Hilbert Space (RKHS)
* **Objective:** Compute continuous spatial support and typicality bounds.

---

## 8. Fuzzy Logic Mamdani (Multi-Criteria Reasoning)
* **Theory:** Lotfi Zadeh (1965), Ebrahim Mamdani (1975)
* **Objective:** Calibrate linguistic risk states (`NORMAL`, `ANOMALOUS`, `SUSPECT`, `HOSTILE`).

---

## 9. Łukasiewicz Many-Valued Logic (Triangular Norm Alignment)
* **Theory:** Jan Łukasiewicz (1920)

$$T_{\text{Luka}}(a, b) = \max(0, a + b - 1)$$

---

## 10. Kelly Criterion (Resource Allocation & Threat Weighting)
* **Theory:** John Larry Kelly Jr. (1956)

---

## 11. Mandelbrot Heavy Tails (Extreme Impulse Detection)
* **Theory:** Benoît Mandelbrot (1963)

---

## 12. CUSUM L1 Change-Point (Impulsive Maneuver Detection)
* **Theory:** E. S. Page (1954)

---

## 13. Augmented Dickey-Fuller (ADF Stationarity Test)
* **Theory:** David Dickey, Wayne Fuller (1979)

---

## 14. Pair Cointegration (Orbital Shadowing & Station-Keeping Alignment)
* **Theory:** Clive Granger, Robert Engle (1987)

---
*Athena-SDA Mathematical Framework Reference Standard.*

### Aplicação no Rastreamento
Pelo teorema de Liouville, um fluxo puramente Hamiltoniano (satélite sob gravidade natural) conserva o volume e a topologia de fase, resultando em um valor constante de CS. Se o satélite aciona propulsores químicos ou iônicos, ele quebra a simetria conservativa, provocando um pico no score $CS$ e indicando uma força externa ativa.

---

## 7. Anomalia Espectral em Espaços de Hilbert (RKHS)
* **Teoria:** David Hilbert (~1900)
* **Objetivo:** Projetar trajetórias orbitais em espaços de dimensão infinita para detectar mudanças de distribuição instantâneas.

Mapeamos o vetor de estados orbitais $x_t \in \mathbb{R}^d$ para um Espaço de Hilbert de Kernel Reprodutor $\mathcal{H}_k$ através de uma função de mapeamento de características $\Phi(x_t) = k(x_t, \cdot)$, onde usamos o kernel Gaussiano RBF:

$$k(x, y) = \exp\left(-\gamma \|x - y\|^2\right)$$

A anomalia espectral é medida calculando os autovalores da matriz de Gram $K_{ij} = k(x_i, x_j)$ em uma janela móvel para computar a divergência de densidade espectral. Um desvio nas frequências dominantes indica alteração nos coeficientes harmônicos orbitais.

---

## 8. Lógica Fuzzy de Mamdani (Inferência sob Incerteza)
* **Teoria:** Lotfi A. Zadeh (1965), Ebrahim Mamdani (1975)
* **Objetivo:** Combinar diferentes features anômalas sob incerteza de medição para gerar uma classificação final.

Utilizamos funções de pertinência trapezoidais e triangulares $\mu_A(x) \in [0, 1]$ para traduzir variáveis contínuas em termos linguísticos:
* **Entradas:** `Maneuver Magnitude` ($\Delta SMA$), `Target Proximity` ($Dist$), `TLE Age` ($Age$).
* **Fuzzy Rules:** 
  $$\text{SE } \Delta SMA \text{ é ALTO } \text{ E } \text{ Proximity é PERTO } \text{ E } \text{ TLE Age é NOVO } \rightarrow \text{ Threat é RED (HOSTIL)}$$

### Mecanismo de Inferência
1. **Fuzzificação:** Calcula os graus de pertinência $\mu_i(x)$ para as entradas.
2. **Operador Fuzzy (AND):** Usa o mínimo $\mu_{A \cap B}(x) = \min(\mu_A(x), \mu_B(x))$.
3. **Defuzzificação:** Calcula o centroide da área agregada resultante das regras de Mamdani para encontrar o valor numérico nítido:
   $$z^* = \frac{\int z \cdot \mu_C(z) dz}{\int \mu_C(z) dz}$$

---

## 9. Lógica Łukasiewicz (Validação Lógica de Hipóteses)
* **Teoria:** Jan Łukasiewicz (1920)
* **Objetivo:** Avaliar a consistência lógica de suposições de ameaça operando em valores de verdade fracionários $v(A) \in [0, 1]$.

A implicação lógica de Łukasiewicz $I(p, q)$ é definida como:

$$v(p \rightarrow q) = \min(1, 1 - v(p) + v(q))$$

Utilizamos isso para calcular a consistência de premissas complexas de SDA. Por exemplo:
* Se $p$ = *"Objeto manobrou"* ($v(p) = 0.85$ via Hurst) e $q$ = *"Objeto é ativo/controlado"* ($v(q) = 0.90$ via Kolmogorov).
* A verdade da implicação $v(p \rightarrow q)$ será $\min(1, 1 - 0.85 + 0.90) = 1.0$, validando a integridade lógica da hipótese de manobra controlada.

---

## 10. Critério de Kelly (Priorização de Recursos de Busca)
* **Teoria:** John Larry Kelly, Jr. (1956)
* **Objetivo:** Otimizar a alocação de tempo de sensores terrestres (radares e telescópios) para rastreamento de alvos prioritários.

A fração ideal de recursos $f^*$ a ser alocada a uma determinada ameaça é dada por:

$$f^* = \frac{b \cdot p - q}{b}$$

Onde:
* $f^*$ é a fração da capacidade de processamento/tempo do sensor terrestre a ser alocada.
* $p$ é a probabilidade da ameaça (fornecida pelo XGBoost + Fuzzy).
* $q = 1 - p$ é a probabilidade do objeto ser inofensivo.
* $b$ representa a criticidade relativa do satélite alvo ameaçado (odds de perda estratégica).

Isso impede o desperdício de recursos críticos de rastreamento em alarmes falsos de alta incerteza.

---

## 11. Valor Intrínseco de Williams (Pesagem de Vulnerabilidade)
* **Teoria:** John Burr Williams (1938)
* **Objetivo:** Pesar a relevância estratégica de satélites no espaço baseando-se em sua utilidade residual futura.

Adaptamos a fórmula clássica de dividendos descontados para calcular o *Valor Estratégico Intrínseco* $V$ de um satélite alvo sob monitoramento:

$$V = \sum_{t=1}^{T} \frac{U_t}{(1 + r)^t}$$

Onde:
* $U_t$ é o índice de utilidade/importância do satélite no instante $t$ (militar, comunicações, GPS).
* $r$ é a taxa de obsolescência tecnológica ou decaimento orbital anual.
* $T$ é a expectativa de vida útil restante do satélite.

---

## 12. Regressão de Kernel (Suavização de Trajetórias)
* **Teoria:** Andrew W. Lo, Harry Mamaysky, A. Craig MacKinlay (2000)
* **Objetivo:** Eliminar ruído e flutuações harmônicas secundárias das séries de telemetria orbital.

Estimamos uma versão suavizada da órbita $m(t)$ a partir das medições ruidosas $Y_i$ usando o estimador Nadaraya-Watson:

$$\hat{m}(t) = \frac{\sum_{i=1}^n K_h(t - t_i) Y_i}{\sum_{i=1}^n K_h(t - t_i)}$$

Onde $K_h(u) = \frac{1}{h} K\left(\frac{u}{h}\right)$ é um kernel gaussiano de largura de banda $h$ que filtra frequências espúrias, permitindo isolar a verdadeira curva de transição orbital.

---

## 13. Algoritmo L1-CUSUM Kernelizado (Detecção de Início de Manobra)
* **Objetivo:** Detectar o instante exato de início de uma manobra de baixíssimo empuxo.

Monitoramos a soma cumulativa em um Espaço de Hilbert para detectar quebras estruturais na distribuição temporal dos elementos orbitais:

$$S_k = \max\left(0, S_{k-1} + \ln \frac{p_{\theta_1}(\Phi(x_k))}{p_{\theta_0}(\Phi(x_k))}\right)$$

Quando a estatística $S_k$ ultrapassa um limite crítico $h_{\text{thr}}$, determinamos que houve um ponto de mudança (*change-point*) e marcamos o início imediato de uma ignição de propulsão ativa do satélite.

---

## 14. Teoria de Distribuições de Caudas Pesadas (Discriminação de Ruído)
* **Teoria:** Benoit Mandelbrot (1963)
* **Objetivo:** Diferenciar perturbações orbitais naturais de distúrbios artificiais baseado no peso das caudas da distribuição de erros.

Analisamos se as variações de aceleração orbital seguem uma distribuição estável Alpha-Estável de Lévy com parâmetro de cauda $\alpha \in (0, 2]$:

$$P(X > x) \sim x^{-\alpha} \quad (x \to \infty)$$

* **$\alpha = 2$ (Distribuição Normal):** Indica flutuações orbitais geradas pela soma de micro-impactos naturais (arrasto térmico, ventos solares estáveis).
* **$\alpha < 1.5$ (Caudas Pesadas de Mandelbrot):** Indica picos extremos isolados incompatíveis com fenômenos estocásticos normais, caracterizando disparos de propulsores de alta energia em curtos espaços de tempo.

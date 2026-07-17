# Fundamentação Matemática do Projeto Athena-SDA

Este documento detalha o arcabouço matemático de 14 teorias de fronteira integradas ao **Athena-SDA** para detecção de anomalias, análise de comportamento de satélites e tomada de decisão sob incerteza.

---

## 1. Entropia de Shannon (Informação Orbital)
* **Teoria:** Claude Shannon (1948)
* **Objetivo:** Medir a desordem ou imprevisibilidade nas séries temporais de parâmetros orbitais.

A entropia de Shannon de uma variável aleatória discreta $X$ com estados possíveis $x_1, ..., x_n$ é dada por:

$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$

### Aplicação no Rastreamento
Analisamos a variação do Semi-Eixo Maior ($a$) de um objeto ao longo de uma janela de 30 dias. Discretizamos as variações diárias $\Delta a_t = a_t - a_{t-1}$ em $N$ caixas (bins) de histograma para aproximar as probabilidades $P(x_i)$.
* **Órbita Estável / Kepleriana:** Variações previsíveis geradas por forças naturais estáveis. Poucos bins concentram toda a probabilidade. Entropia próxima de zero ($H(X) \approx 0.2$).
* **Órbita com Manobras Ativas:** O satélite altera sua altitude de forma intencional, espalhando os valores de $\Delta a_t$ e gerando uma distribuição caótica. Entropia alta ($H(X) > 1.8$).

---

## 2. Proxy de Complexidade de Kolmogorov (Detecção de Intenção)
* **Teoria:** Andrey Kolmogorov (1965)
* **Objetivo:** Identificar se uma trajetória é gerada por um processo físico simples ou por um algoritmo de controle complexo.

A complexidade de Kolmogorov $K(s)$ de uma string $s$ é o comprimento do menor programa $p$ que roda em uma máquina de Turing Universal $U$ e gera $s$:

$$K(s) = \min \{ |p| : U(p) = s \}$$

### Aplicação no Rastreamento
Como $K(s)$ é computacionalmente indecidível, usamos o tamanho de um arquivo comprimido por algoritmos de compressão sem perda (LZW ou zlib) como um proxy para complexidade algorítmica.
1. Convertemos a série temporal de atitudes e altitudes em uma string simbólica discreta (ex: `U` para subida, `D` para descida, `S` para estabilidade):
   $$s = \text{"SSSSSSSUSSUDDSSS"}$$
2. O score de complexidade do objeto é o coeficiente de compressão:
   $$K_{\text{proxy}}(s) = \frac{\text{Tamanho}(Compress(s))}{\text{Tamanho}(s)}$$
* Trajetórias naturais comprimem extremamente bem ($K_{\text{proxy}} \to 0$).
* Manobras complexas de evasão de colisões ou perseguição contêm padrões de informação de alta complexidade que resistem à compressão ($K_{\text{proxy}} \to 1$).

---

## 3. Expoente de Hurst (Memória de Longo Prazo e R/S)
* **Teoria:** Harold Edwin Hurst (1951)
* **Objetivo:** Diferenciar decaimento orbital natural (arrasto atmosférico) de propulsão ativa persistente.

O expoente de Hurst $H$ é calculado dividindo a amplitude média das flutuações acumuladas ($R$) pelo desvio padrão ($S$) ao longo de subintervalos de tempo de tamanho $n$:

$$E \left[ \frac{R(n)}{S(n)} \right] = C \cdot n^H$$

* **$H = 0.5$:** Movimento browniano clássico (caminhada aleatória sem memória).
* **$0.5 < H \le 1.0$:** Série persistente (tendência de longo prazo. Se subiu hoje, tende a subir amanhã).
* **$0 \le H < 0.5$:** Série anti-persistente (reversão à média).

### Aplicação no Rastreamento
* Satélites sofrendo arrasto atmosférico natural mostram flutuações anti-persistentes ou de caminhada aleatória ($H \approx 0.3 - 0.5$).
* Um satélite utilizando propulsores elétricos (como motores de íons) para realizar uma transferência orbital sutil exibe uma forte assinatura de persistência temporal ($H \ge 0.78$), revelando a manobra mesmo sob forças de empuxo extremamente baixas.

---

## 4. Curvatura de Ricci de Ollivier (Anomalias de Grafo de Constelação)
* **Teoria:** Yann Ollivier (2007)
* **Objetivo:** Detectar deformações locais na vizinhança de uma constelação causadas por aproximação não autorizada.

A curvatura de Ricci de Ollivier $\kappa(x, y)$ entre dois nós $x$ e $y$ em um grafo é dada por:

$$\kappa(x, y) = 1 - \frac{W_1(m_x, m_y)}{d(x, y)}$$

Onde $d(x, y)$ é a distância geodésica mais curta entre os nós, $m_x, m_y$ são medidas de probabilidade locais associadas a cada nó, e $W_1$ é a métrica de transporte de Wasserstein-1 (Earth Mover's Distance):

$$W_1(m_x, m_y) = \inf_{\gamma \in \Pi(m_x, m_y)} \iint d(u, v) d\gamma(u, v)$$

### Aplicação no Rastreamento
Modelamos a rede de satélites como um grafo geométrico flutuante. Se a distância de transporte entre vizinhanças encolhe de forma anômala, a curvatura local $\kappa(x, y)$ aumenta em direção a valores positivos, sinalizando um comportamento de convergência geométrica ativa (aproximação tática).

---

## 5. Homologia Persistente (Análise de Dados Topológicos - TDA)
* **Teoria:** Herbert Edelsbrunner (2002)
* **Objetivo:** Detectar mudanças estruturais globais na trajetória orbital representadas em nuvens de pontos 3D.

Geramos uma filtração de complexos de Vietoris-Rips $VR(P, \epsilon)$ a partir de uma nuvem de pontos orbitais $P = \{p_1, ..., p_k\} \subset \mathbb{R}^3$, variando o raio de proximidade $\epsilon$:

$$VR(P, \epsilon) = \{ \sigma \subseteq P : \text{diam}(\sigma) \le \epsilon \}$$

Mapeamos o nascimento e a morte de características topológicas nos grupos de homologia simplicial $H_k$:
* **$H_0$:** Componentes conectadas (indica agrupamento/clusterização física de satélites).
* **$H_1$:** Loops/Túneis 1D (indica a forma fechada da trajetória orbital circular/elíptica).

### Aplicação no Rastreamento
Uma órbita kepleriana fechada típica gera um ciclo persistente $H_1$ de longa vida nos diagramas de persistência. Se o satélite muda de órbita para uma espiral ou faz uma fuga de plano orbital, esse ciclo $H_1$ "morre" prematuramente na filtração e novos padrões nascem, denunciando desvios na topologia da trajetória.

---

## 6. Chern-Simons Proxy (Assinatura de Campo Não Conservativo)
* **Teoria:** Shiing-Shen Chern, James Harris Simons (1974)
* **Objetivo:** Detectar a atuação de forças propulsoras não conservativas na dinâmica orbital.

Modelamos o fluxo orbital de fases do satélite. O índice de Chern-Simons proxy $CS$ é expresso como a integral helicoidal tridimensional da velocidade $\vec{v}$ e da vorticidade orbital $\vec{\omega} = \nabla \times \vec{v}$:

$$CS = \int_{t_0}^{t_1} (\vec{v} \cdot \vec{\omega}) dt$$

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

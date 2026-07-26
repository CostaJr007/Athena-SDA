# ========================================================================
# INSTRUÇÕES DE MELHORIAS ML — ATHENA-SDA (VERSÃO REAL/PRODUÇÃO)
# Documento autocontido para qualquer IA seguir passo a passo.
# Projeto: /run/media/adeilsoncosta/Novo volume/Athena-SDA/
# Data: 25/07/2026
# ========================================================================
#
# CONTEXTO:
# A versão real do Athena-SDA é altamente sofisticada, atingindo 96.3% de
# acurácia com 26 features matemáticas e topológicas. O motor de ML está
# correto, coerente e com validação out-of-time (walk-forward) robusta.
#
# PROBLEMA ATUAL (POLIMENTO):
# Restam apenas 5 "edge cases" (casos extremos) que não quebram o pipeline,
# mas causam distorções em situações limite:
# 1. Fuzzy crasha quando distância > 500km
# 2. Kolmogorov inflado para órbitas curtas
# 3. Estimador de Mandelbrot com risco de divisão por zero
# 4. Cointegração comparando séries temporais dessincronizadas
# 5. Idade do TLE congelada no banco de dados Parquet
#
# PRIORIDADE: Executar na ordem listada. Cada passo é independente.
#
# ========================================================================

# ========================================================================
# PASSO 1: CORRIGIR CRASH SILENCIOSO DO MOTOR FUZZY
# ========================================================================
# ARQUIVO: src/fuzzy.py
# FUNÇÃO: fuzzy_inference_threat()
# LINHAS: ~96
# 
# PROBLEMA: O universo da variável `dist_military` vai até 500 km. Quando a 
# distância calculada é 501+ km, o skfuzzy levanta exceção e o fallback seta 
# threat = 0.0. Satélites longe de ativos são marcados como NORMAL, mesmo que
# as features orbitais (entropia, Hurst) indiquem anomalias extremas.
#
# ANTES (Linhas 96):
#     sim.input['dist_military'] = min_dist_mil
#
# DEPOIS:
#     # Clampar ao suporte máximo do universo para não explodir a inferência
#     sim.input['dist_military'] = min(float(min_dist_mil), 500.0)
#
# Teste: Um satélite a 800km com anomalia alta não deve mais retornar threat 0.0.


# ========================================================================
# PASSO 2: CORRIGIR INFLAÇÃO DO PROXY DE KOLMOGOROV PARA SÉRIES CURTAS
# ========================================================================
# ARQUIVO: src/engine.py
# FUNÇÃO: calculate_kolmogorov_proxy(sma_series)
# LINHAS: ~42-45
#
# PROBLEMA: O tamanho do header da compressão `zlib` em strings muito curtas
# (ex: "SSSSS") é maior que a própria string. A razão de compressão fica > 1.0, 
# resultando em Kolmogorov = 1.0 (complexidade caótica máxima) para órbitas
# perfeitamente constantes.
#
# ANTES (Linhas 42-45):
#     if len(s) == 0:
#         return 0.0
#     compressed = zlib.compress(s)
#     return float(np.clip(len(compressed) / len(s), 0.0, 1.0))
#
# DEPOIS:
#     if len(s) < 10:
#         return 0.0  # Muito curto para a entropia do zlib header compensar
#     compressed = zlib.compress(s)
#     
#     # Subtrair bytes do header (tipicamente 11 bytes para strings curtas)
#     comp_len = max(len(compressed) - 11, 1)
#     return float(np.clip(comp_len / len(s), 0.0, 1.0))


# ========================================================================
# PASSO 3: PROTEGER ESTIMADOR DE HILL (MANDELBROT) CONTRA DIVISÃO POR ZERO
# ========================================================================
# ARQUIVO: src/engine.py
# FUNÇÃO: calculate_mandelbrot_tail_anomaly(series)
# LINHAS: ~247-251
#
# PROBLEMA: Se `tail_data` contém elementos onde `tail_data / threshold` é
# 1.0000000000001, o logaritmo resulta em 0.0000000. O somatório dos logs pode 
# chegar a zero exato, gerando ZeroDivisionError no cálculo de `alpha`.
#
# ANTES (Linhas 249-250):
#     # Estimador de Hill para o alfa de cauda
#     alpha = len(tail_data) / np.sum(np.log(tail_data / threshold))
#
# DEPOIS:
#     # Estimador de Hill para o alfa de cauda com guarda epsilon
#     log_sum = np.sum(np.log(tail_data / threshold))
#     if log_sum < 1e-9:
#         return 0.0
#     alpha = len(tail_data) / log_sum


# ========================================================================
# PASSO 4: CALCULAR IDADE DO TLE NO TEMPO DE INFERÊNCIA (NÃO NO INGEST)
# ========================================================================
# ARQUIVO: src/tle_store.py
# FUNÇÃO: normalize_epochs_df(df)
# LINHAS: ~154-156
# E ARQUIVO: src/models.py 
# FUNÇÃO: extract_satellite_features()
#
# PROBLEMA: O store do parquet congela a feature `tle_age_hours`. Um TLE 
# ingerido na segunda-feira sempre terá idade=0, mesmo que hoje seja sexta, 
# quebrando a lógica de incerteza temporal do Fuzzy/XGBoost.
#
# PARTE A - src/tle_store.py (Linhas 154-156)
# ANTES:
#     now = pd.Timestamp.now(tz="UTC")
#     out["tle_age_hours"] = (now - out["timestamp"]).dt.total_seconds() / 3600.0
#     out["tle_age_hours"] = out["tle_age_hours"].clip(lower=0).fillna(24.0)
#
# DEPOIS:
#     # REMOVA AS 3 LINHAS ACIMA.
#     # Em vez disso, coloque apenas um valor default de placeholder
#     # (A idade real será calculada no momento de extração das features)
#     out["tle_age_hours"] = 0.0
#
# PARTE B - src/models.py (Linhas 99-105 dentro de extract_satellite_features)
# ANTES:
#     tle_age = float(last_row.get("tle_age_hours", 12.0))
#
# DEPOIS:
#     # Calcular a idade verdadeira no momento exato em que a feature é extraída
#     if "timestamp" in last_row and pd.notnull(last_row["timestamp"]):
#         now = pd.Timestamp.now(tz="UTC")
#         tle_age = float((now - last_row["timestamp"]).total_seconds() / 3600.0)
#         tle_age = max(0.0, tle_age)
#     else:
#         tle_age = float(last_row.get("tle_age_hours", 12.0))


# ========================================================================
# PASSO 5: ALINHAR TEMPORALMENTE SÉRIES NA COINTEGRAÇÃO DE ENGLE-GRANGER
# ========================================================================
# ARQUIVO: src/pair_score.py
# FUNÇÃO: _align_series(a, b, col, max_points)
# LINHAS: ~61-68
#
# PROBLEMA: Pegar puramente as últimas 120 linhas dos DataFrames de dois 
# satélites não garante que elas se sobrepõem no tempo. O teste de 
# cointegração pode comparar órbitas da semana passada com órbitas de hoje.
#
# ANTES:
#     sa = a.sort_values("timestamp")[col].astype(float).values
#     sb = b.sort_values("timestamp")[col].astype(float).values
#     n = min(len(sa), len(sb), max_points)
#     if n < 20:
#         return sa[-n:] if n else sa, sb[-n:] if n else sb
#     return sa[-n:], sb[-n:]
#
# DEPOIS:
#     # Merge asof garante que os timestamps estejam sincronizados
#     a_sorted = a.sort_values("timestamp").tail(max_points * 2)
#     b_sorted = b.sort_values("timestamp").tail(max_points * 2)
#     
#     if len(a_sorted) == 0 or len(b_sorted) == 0:
#         return np.array([]), np.array([])
#
#     # Alinha o satélite Suspect com o Asset usando o timestamp mais próximo (max tolerancia 12h)
#     merged = pd.merge_asof(
#         a_sorted, b_sorted, on="timestamp", 
#         direction="nearest", tolerance=pd.Timedelta("12h"),
#         suffixes=('_a', '_b')
#     ).dropna(subset=[col + "_a", col + "_b"])
#
#     sa = merged[col + "_a"].astype(float).values
#     sb = merged[col + "_b"].astype(float).values
#     
#     n = min(len(sa), len(sb), max_points)
#     if n < 20:
#         return sa[-n:] if n else sa, sb[-n:] if n else sb
#     return sa[-n:], sb[-n:]


# ========================================================================
# APÓS APLICAR AS MUDANÇAS
# ========================================================================
# 1. Execute o smoke test para garantir que os módulos não quebraram:
#    cd /run/media/adeilsoncosta/Novo\ volume/Athena-SDA
#    .venv/bin/python scripts/smoke_test.py
#
# 2. Como as features orbitais mudaram sutilmente (Kologorov, TLE Age),
#    recomenda-se retreinar o baseline contínuo e o XGBoost:
#    .venv/bin/python scripts/smoke_test.py --train
# ========================================================================

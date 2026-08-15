/**
 * Athena risk_report.v1 — types + helpers for the Mission Board UI.
 * Source of truth: data/alerts/risk_report_latest.json (synced to public/data/).
 *
 * Runtime validation uses zod against the Open API contract
 * (schemas/risk_report.v1.schema.json) instead of a blind cast, so a
 * schema-drifted report surfaces as a visible error instead of NaN/crash.
 */
import { z } from 'zod'

export type Threat = 'HOSTILE' | 'SUSPECT' | 'ANOMALY' | 'NOMINAL'
export type Role = 'asset' | 'suspect' | 'baseline' | 'unknown'
export type BoardStatus =
  | 'NOMINAL'
  | 'ANOMALY'
  | 'PAIR_ELEVATED'
  | 'UNRELIABLE_DATA'
  | 'CALIBRATION_BASELINE'
  | 'ASSET_REGIME_NOISE'
  | 'CHANGE_RELEVANT'

export interface DataQuality {
  score: number
  issues: string[]
  reliable: boolean
  tle_age_hours: number
}

export interface Evidence {
  belief_anomalous?: number
  plausibility_anomalous?: number
  conflict_K?: number
}

export interface PairInfo {
  asset_norad: number
  asset_name: string
  min_distance_km: number
  cointegration_pvalue: number
  pair_risk: number
  risk_level: string
  pc?: number | null
  tca_utc?: string | null
  miss_distance_km?: number | null
}

/** Corrected math framework — feature names match src/config.py (post-audit). */
export interface FeaturesSnapshot {
  delta_sma_7d_km?: number
  delta_sma_30d_km?: number
  regime_changes_30d?: number
  shannon_entropy_sma_30d?: number
  shannon_entropy_sma_short?: number
  lz76_complexity?: number
  permutation_entropy?: number
  complexity_entropy_c?: number
  dfa_hurst_sma?: number
  dfa_hurst_sma_short?: number
  persistence_dfa_gap?: number
  mandelbrot_tail_score?: number
  adf_pvalue?: number
  static_threat?: number
  page_cusum_sma?: number
  ewma_sma?: number
  bocpd_change_prob_3d?: number
  innovation_score?: number
  ssa_residual_last?: number
  ssa_energy_ratio?: number
  mmd_typicality?: number
  tle_age_hours?: number
  f10_7?: number
  ap_index?: number
  kp_mean?: number
  geomagnetic_storm?: number
  min_distance_to_military_km?: number
  cointegration_pvalue?: number
  dcca_rho?: number
  [key: string]: number | undefined
}

export interface AnomalyOnset {
  first_elevated_at?: string | null
  method?: string
  threshold?: number
  soft_threshold?: number
  sustained?: number
  n_windows_scored?: number
  max_score_in_scan?: number | null
  sma_change_at?: string | null
  note?: string
  error?: string
}

export interface BoardEntry {
  norad_id: number
  object_name: string
  role: Role
  country: string
  purpose: string
  orbit_class: string
  anomaly_score: number
  attention_score: number
  kelly_allocation?: number
  is_anomaly: boolean
  /** Military-first doctrine: suspect noise and/or elevated pair */
  is_military_detection?: boolean
  is_platform_health_flag?: boolean
  is_calibration_object?: boolean
  military_alert_eligible?: boolean
  status: BoardStatus
  xgb_class: string | null
  data_quality: DataQuality
  evidence?: Evidence
  features_snapshot: FeaturesSnapshot
  pair: PairInfo | null
  /** When anomalous noise first rose on the series (estimate). */
  anomaly_onset?: AnomalyOnset | null
  window_end?: string | null
  score_delta_1d?: number | null
  anomaly_threshold_used?: number | null
  /** Operational FSM (OPEN/ACK/…) — not a quant score. */
  triage?: string
}

export interface TopPair {
  suspect_norad: number
  suspect_name: string
  suspect_country?: string
  asset_norad: number
  asset_name: string
  asset_country?: string
  min_distance_km: number
  cointegration_pvalue: number
  pair_risk: number
  risk_level: string
  proximity_score?: number
  coint_score?: number
  pc?: number | null
  tca_utc?: string | null
  miss_distance_km?: number | null
}

export interface RiskSummary {
  n_scored: number
  n_anomalies: number
  n_military_detections?: number
  n_platform_health_flags?: number
  n_pairs: number
  n_pair_elevated: number
  threshold: number
  focus?: string
  kelly_attention_budget?: number
}

export interface RiskReport {
  schema: string
  generated_at: string
  day: string
  doctrine?: string
  protocol?: string
  summary: RiskSummary
  board: BoardEntry[]
  top_pairs: TopPair[]
  model?: string
  train_meta?: Record<string, unknown>
  doctrine_summary?: Record<string, unknown>
}

// ---------------------------------------------------------------------------
// Single source of threat colors (THREAT_HEX) — LeftDock/RightDock/globe
// previously kept 3 parallel maps; everything now reads from here.
// ---------------------------------------------------------------------------
export const THREAT_HEX: Record<Threat, string> = {
  HOSTILE: '#fb7185',
  SUSPECT: '#fbbf24',
  ANOMALY: '#fb923c',
  NOMINAL: '#34d399',
}

/** Tailwind-based row style per threat (used by the mission board rows). */
export const THREAT_STYLE: Record<
  Threat,
  { label: string; color: string; bg: string; border: string; bar: string }
> = {
  HOSTILE: {
    label: 'HOSTILE',
    color: 'text-rose-300',
    bg: 'bg-rose-500/10',
    border: 'border-rose-400/35',
    bar: 'bg-rose-400/90',
  },
  SUSPECT: {
    label: 'SUSPECT',
    color: 'text-amber-300',
    bg: 'bg-amber-500/10',
    border: 'border-amber-400/35',
    bar: 'bg-amber-400/90',
  },
  ANOMALY: {
    label: 'ANOMALY',
    color: 'text-orange-300',
    bg: 'bg-orange-500/10',
    border: 'border-orange-400/35',
    bar: 'bg-orange-400/90',
  },
  NOMINAL: {
    label: 'NOMINAL',
    color: 'text-emerald-300',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-400/35',
    bar: 'bg-emerald-400/80',
  },
}

/** Role accent when status is calm (assets / baseline). */
export const ROLE_HEX: Record<string, string> = {
  asset: '#38bdf8',
  suspect: '#a78bfa',
  baseline: '#64748b',
}

// ---------------------------------------------------------------------------
// Cross-filter state (Palantir US 12,374,011 B2 — ontology histogram filters)
// ---------------------------------------------------------------------------
export interface BoardFilters {
  roles: string[]
  countries: string[]
  orbits: string[]
}

export const EMPTY_FILTERS: BoardFilters = { roles: [], countries: [], orbits: [] }

export function filtersActive(f: BoardFilters): boolean {
  return f.roles.length > 0 || f.countries.length > 0 || f.orbits.length > 0
}

export function matchesFilters(b: BoardEntry, f: BoardFilters): boolean {
  if (f.roles.length > 0 && !f.roles.includes(b.role)) return false
  if (f.countries.length > 0 && !f.countries.includes(b.country)) return false
  if (f.orbits.length > 0 && !f.orbits.includes(b.orbit_class)) return false
  return true
}

/**
 * Histogram of one dimension after applying every filter *except* that
 * dimension — Palantir US 12,374,011 B2 sub-histogram regeneration.
 */
export function histogramExcluding(
  board: BoardEntry[],
  filters: BoardFilters,
  exclude: keyof BoardFilters,
  keyFn: (b: BoardEntry) => string,
): Array<{ value: string; count: number }> {
  const f: BoardFilters = {
    roles: exclude === 'roles' ? [] : filters.roles,
    countries: exclude === 'countries' ? [] : filters.countries,
    orbits: exclude === 'orbits' ? [] : filters.orbits,
  }
  return boardHistogram(
    board.filter((b) => matchesFilters(b, f)),
    keyFn,
  )
}

/** Histogram of a board dimension (role / country / orbit) with counts. */
export function boardHistogram<K extends string>(
  board: BoardEntry[],
  keyFn: (b: BoardEntry) => string,
): Array<{ value: K; count: number }> {
  const counts = new Map<string, number>()
  for (const b of board) {
    const k = keyFn(b)
    counts.set(k, (counts.get(k) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([value, count]) => ({ value: value as K, count }))
    .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value))
}


/**
 * Map ML board row → UI threat tier used by docks / globe.
 * HOSTILE is reserved for critical pair risk + elevated attention, not XGB labels.
 */
export function boardThreat(b: BoardEntry): Threat {
  const pairLevel = (b.pair?.risk_level ?? '').toUpperCase()
  const pairRisk = b.pair?.pair_risk ?? 0

  if (b.status === 'CALIBRATION_BASELINE' || b.is_calibration_object) {
    return 'NOMINAL'
  }
  if (
    b.status === 'PAIR_ELEVATED' &&
    (pairLevel === 'CRITICAL' || b.attention_score >= 0.65 || pairRisk >= 0.9)
  ) {
    return 'HOSTILE'
  }
  if (
    b.status === 'PAIR_ELEVATED' ||
    pairRisk >= 0.55 ||
    b.is_military_detection
  ) {
    return 'SUSPECT'
  }
  if (
    b.is_anomaly ||
    b.status === 'ANOMALY' ||
    b.status === 'ASSET_REGIME_NOISE' ||
    b.status === 'CHANGE_RELEVANT' ||
    b.is_platform_health_flag
  ) {
    return 'ANOMALY'
  }
  if (b.status === 'UNRELIABLE_DATA') return 'ANOMALY'
  return 'NOMINAL'
}

/** Globe color: threat first, else role accent for watchlist objects. */
export function boardColor(b: BoardEntry): string {
  const threat = boardThreat(b)
  if (threat !== 'NOMINAL') return THREAT_HEX[threat]
  return ROLE_HEX[b.role] ?? THREAT_HEX.NOMINAL
}

export function boardByNorad(report: RiskReport | null): Map<number, BoardEntry> {
  const m = new Map<number, BoardEntry>()
  if (!report) return m
  for (const b of report.board) m.set(b.norad_id, b)
  return m
}

export function threatRank(t: Threat): number {
  return { HOSTILE: 0, SUSPECT: 1, ANOMALY: 2, NOMINAL: 3 }[t]
}

export function sortedBoard(report: RiskReport | null): BoardEntry[] {
  if (!report) return []
  return [...report.board].sort((a, b) => {
    const mil = Number(!!b.is_military_detection) - Number(!!a.is_military_detection)
    if (mil !== 0) return mil
    const tr = threatRank(boardThreat(a)) - threatRank(boardThreat(b))
    if (tr !== 0) return tr
    return b.attention_score - a.attention_score
  })
}

/** Format onset ISO/timestamp to short date for UI. */
export function formatPc(pc: number | null | undefined): string {
  if (pc == null || !Number.isFinite(pc)) return '—'
  if (pc === 0) return '0'
  if (pc < 0.001) return pc.toExponential(2)
  return pc.toFixed(4)
}

export function applyTriageMap(
  report: RiskReport,
  alerts: Record<string, { status?: string }>,
): RiskReport {
  return {
    ...report,
    board: report.board.map((b) => ({
      ...b,
      triage: alerts[String(b.norad_id)]?.status ?? b.triage ?? 'OPEN',
    })),
  }
}

export function formatOnsetDate(raw?: string | null): string | null {
  if (!raw) return null
  const d = new Date(raw)
  if (!Number.isNaN(d.getTime())) {
    return d.toISOString().slice(0, 10)
  }
  // already date-like
  const m = String(raw).match(/\d{4}-\d{2}-\d{2}/)
  return m ? m[0] : String(raw).slice(0, 16)
}

/** Local stub briefing — explains scores already computed (no invented threat). */
export function bobBrief(b: BoardEntry): string {
  const threat = boardThreat(b)
  const flags: string[] = []
  if (b.is_military_detection) flags.push('military detection')
  if (b.is_platform_health_flag) flags.push('platform health')
  if (b.is_calibration_object) flags.push('calibration baseline')
  const parts: string[] = [
    `${b.object_name} (NORAD ${b.norad_id}) · role ${b.role} · ${threat}.`,
    `attention=${b.attention_score.toFixed(3)} · anomaly=${b.anomaly_score.toFixed(3)} · status=${b.status}.`,
  ]
  if (b.kelly_allocation != null) {
    parts.push(`Kelly attention budget=${(b.kelly_allocation * 100).toFixed(1)}%.`)
  }
  if (flags.length) parts.push(`Flags: ${flags.join(', ')}.`)
  const onset = b.anomaly_onset
  const since = formatOnsetDate(onset?.first_elevated_at)
  if (since) {
    parts.push(
      `Series noise elevated since ~${since} (method ${onset?.method ?? 'onset'}; TLE-window estimate).`,
    )
  }
  const fs = b.features_snapshot ?? {}
  if (fs.dfa_hurst_sma != null) {
    parts.push(`DFA α=${fs.dfa_hurst_sma.toFixed(2)} (series persistence).`)
  }
  if (fs.lz76_complexity != null) {
    parts.push(`LZ76 complexity=${fs.lz76_complexity.toFixed(2)}.`)
  }
  if (fs.shannon_entropy_sma_30d != null) {
    parts.push(`Shannon H(Δa)=${fs.shannon_entropy_sma_30d.toFixed(2)}.`)
  }
  if (fs.page_cusum_sma != null && fs.page_cusum_sma >= 0.5) {
    parts.push(`Page CUSUM=${fs.page_cusum_sma.toFixed(2)} (regime shift).`)
  }
  if (fs.geomagnetic_storm != null && fs.geomagnetic_storm >= 0.5) {
    parts.push('Geomagnetic storm context active (space weather).')
  }
  if (b.pair) {
    const extra = [
      b.pair.tca_utc ? `TCA ${b.pair.tca_utc.slice(11, 16)}Z` : '',
      b.pair.pc != null ? `Pc ${formatPc(b.pair.pc)}` : '',
    ]
      .filter(Boolean)
      .join(' · ')
    parts.push(
      `Pair vs ${b.pair.asset_name} (#${b.pair.asset_norad}): dist ${b.pair.min_distance_km.toFixed(1)} km · pair_risk ${b.pair.pair_risk.toFixed(2)} (${b.pair.risk_level})${extra ? ` · ${extra}` : ''}.`,
    )
  }
  if (b.triage && b.triage !== 'OPEN') {
    parts.push(`Triage ${b.triage} (bookkeeping — scores unchanged).`)
  }
  if (!b.data_quality?.reliable) {
    parts.push(`DQ: unreliable (${(b.data_quality?.issues ?? []).join(', ') || 'issues'}).`)
  } else if (b.data_quality?.issues?.length) {
    parts.push(`DQ issues: ${b.data_quality.issues.join(', ')}.`)
  }
  parts.push('Scores from Athena monitor (IF + pairs + quant features).')
  return parts.join(' ')
}

// ---------------------------------------------------------------------------
// zod runtime validation (contract: schemas/risk_report.v1.schema.json)
// ---------------------------------------------------------------------------
const dataQualitySchema = z.object({
  score: z.number().optional(),
  issues: z.array(z.string()).optional(),
  reliable: z.boolean().optional(),
  tle_age_hours: z.number().optional(),
})

const pairInfoSchema = z
  .object({
    asset_norad: z.number().optional(),
    asset_name: z.string().optional(),
    min_distance_km: z.number().optional(),
    cointegration_pvalue: z.number().optional(),
    pair_risk: z.number().optional(),
    risk_level: z.string().optional(),
    pc: z.number().nullable().optional(),
    tca_utc: z.string().nullable().optional(),
    miss_distance_km: z.number().nullable().optional(),
    conjunction_method: z.string().optional(),
    hours_to_tca: z.number().nullable().optional(),
  })
  .passthrough()

const featuresSnapshotSchema = z
  .object({
    delta_sma_7d_km: z.number().optional(),
    dfa_hurst_sma: z.number().optional(),
    lz76_complexity: z.number().optional(),
    page_cusum_sma: z.number().optional(),
    shannon_entropy_sma_30d: z.number().optional(),
  })
  .passthrough()

const evidenceSchema = z.object({
  belief_anomalous: z.number().optional(),
  plausibility_anomalous: z.number().optional(),
  conflict_K: z.number().optional(),
})

const boardEntrySchema = z
  .object({
    norad_id: z.number(),
    object_name: z.string().optional(),
    role: z.string().optional(),
    country: z.string().optional(),
    purpose: z.string().optional(),
    orbit_class: z.string().optional(),
    anomaly_score: z.number(),
    attention_score: z.number(),
    kelly_allocation: z.number().optional(),
    is_anomaly: z.boolean().optional(),
    is_military_detection: z.boolean().optional(),
    is_platform_health_flag: z.boolean().optional(),
    is_calibration_object: z.boolean().optional(),
    status: z.string().optional(),
    xgb_class: z.string().nullable().optional(),
    data_quality: dataQualitySchema.passthrough().optional(),
    evidence: evidenceSchema.passthrough().optional(),
    features_snapshot: featuresSnapshotSchema.optional(),
    pair: pairInfoSchema.nullable().optional(),
    anomaly_onset: z.unknown().optional(),
    window_end: z.string().nullable().optional(),
    score_delta_1d: z.number().nullable().optional(),
    triage: z.string().optional(),
  })
  .passthrough()

const riskSummarySchema = z.object({
  n_scored: z.number().nullable().optional(),
  n_anomalies: z.number().nullable().optional(),
  n_military_detections: z.number().nullable().optional(),
  n_platform_health_flags: z.number().nullable().optional(),
  n_pairs: z.number().nullable().optional(),
  n_pair_elevated: z.number().nullable().optional(),
  threshold: z.number().nullable().optional(),
  focus: z.string().optional(),
  kelly_attention_budget: z.number().nullable().optional(),
})

const riskReportSchema = z.object({
  schema: z.string(),
  generated_at: z.string().optional(),
  day: z.string().optional(),
  doctrine: z.string().optional(),
  protocol: z.string().nullable().optional(),
  summary: riskSummarySchema.optional(),
  board: z.array(boardEntrySchema),
  top_pairs: z.array(z.record(z.string(), z.unknown())).optional(),
  model: z.union([z.object({}), z.string(), z.null()]).optional(),
  train_meta: z.record(z.string(), z.unknown()).optional(),
  doctrine_summary: z.record(z.string(), z.unknown()).optional(),
})

export async function fetchRiskReport(signal?: AbortSignal): Promise<RiskReport> {
  const url = `${import.meta.env.BASE_URL}data/risk_report_latest.json`
  const res = await fetch(url, { signal })
  if (!res.ok) throw new Error(`risk_report HTTP ${res.status}`)
  const data: unknown = await res.json()
  try {
    // Runtime-validated against the contract; then typed.
    return riskReportSchema.parse(data) as unknown as RiskReport
  } catch (err) {
    if (err instanceof z.ZodError) {
      const first = err.issues[0]
      throw new Error(
        `risk_report schema mismatch: ${first?.path.join('.') ?? '?'} ${first?.message ?? ''}`,
      )
    }
    throw err
  }
}

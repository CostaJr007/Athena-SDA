/**
 * Athena risk_report.v1 — types + helpers for the Mission Board UI.
 * Source of truth: data/alerts/risk_report_latest.json (synced to public/data/).
 */

export type Threat = 'HOSTILE' | 'SUSPECT' | 'ANOMALY' | 'NOMINAL'
export type Role = 'asset' | 'suspect' | 'baseline' | string
export type BoardStatus =
  | 'NOMINAL'
  | 'ANOMALY'
  | 'PAIR_ELEVATED'
  | 'UNRELIABLE_DATA'
  | 'CALIBRATION_BASELINE'
  | 'ASSET_REGIME_NOISE'
  | 'CHANGE_RELEVANT'
  | string

export interface DataQuality {
  score: number
  issues: string[]
  reliable: boolean
  tle_age_hours: number
}

export interface PairInfo {
  asset_norad: number
  asset_name: string
  min_distance_km: number
  cointegration_pvalue: number
  pair_risk: number
  risk_level: string
}

export interface FeaturesSnapshot {
  delta_sma_7d_km?: number
  shannon_entropy_sma_30d?: number
  shannon_entropy_sma_short?: number
  hurst_exponent_sma?: number
  hurst_exponent_sma_short?: number
  persistence_hurst_gap?: number
  kolmogorov_proxy_7d?: number
  l1_cusum_sma?: number
  tle_age_hours?: number
  f10_7?: number
  ap_index?: number
  kp_mean?: number
  geomagnetic_storm?: number
  min_distance_to_military_km?: number
  cointegration_pvalue?: number
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
  is_anomaly: boolean
  /** Military-first doctrine: suspect noise and/or elevated pair */
  is_military_detection?: boolean
  is_platform_health_flag?: boolean
  is_calibration_object?: boolean
  military_alert_eligible?: boolean
  status: BoardStatus
  xgb_class: string | null
  data_quality: DataQuality
  features_snapshot: FeaturesSnapshot
  pair: PairInfo | null
  /** When anomalous noise first rose on the series (estimate). */
  anomaly_onset?: AnomalyOnset | null
  window_end?: string | null
  score_delta_1d?: number | null
  anomaly_threshold_used?: number | null
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

export const THREAT_HEX: Record<Threat, string> = {
  HOSTILE: '#fb7185',
  SUSPECT: '#fbbf24',
  ANOMALY: '#fb923c',
  NOMINAL: '#34d399',
}

/** Role accent when status is calm (assets / baseline). */
export const ROLE_HEX: Record<string, string> = {
  asset: '#38bdf8',
  suspect: '#a78bfa',
  baseline: '#64748b',
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
  if (flags.length) parts.push(`Flags: ${flags.join(', ')}.`)
  const onset = b.anomaly_onset
  const since = formatOnsetDate(onset?.first_elevated_at)
  if (since) {
    parts.push(
      `Series noise elevated since ~${since} (method ${onset?.method ?? 'onset'}; TLE-window estimate).`,
    )
  }
  const fs = b.features_snapshot ?? {}
  if (fs.hurst_exponent_sma != null) {
    parts.push(`Hurst=${fs.hurst_exponent_sma.toFixed(2)} (series persistence).`)
  }
  if (fs.persistence_hurst_gap != null) {
    parts.push(`Hurst gap (full−short)=${fs.persistence_hurst_gap.toFixed(2)}.`)
  }
  if (fs.shannon_entropy_sma_30d != null) {
    parts.push(`Shannon H(Δa)=${fs.shannon_entropy_sma_30d.toFixed(2)}.`)
  }
  if (fs.geomagnetic_storm != null && fs.geomagnetic_storm >= 0.5) {
    parts.push('Geomagnetic storm context active (space weather).')
  }
  if (b.pair) {
    parts.push(
      `Pair vs ${b.pair.asset_name} (#${b.pair.asset_norad}): dist ${b.pair.min_distance_km.toFixed(1)} km · pair_risk ${b.pair.pair_risk.toFixed(2)} (${b.pair.risk_level}).`,
    )
  }
  if (!b.data_quality?.reliable) {
    parts.push(`DQ: unreliable (${(b.data_quality?.issues ?? []).join(', ') || 'issues'}).`)
  } else if (b.data_quality?.issues?.length) {
    parts.push(`DQ issues: ${b.data_quality.issues.join(', ')}.`)
  }
  parts.push('Scores from Athena monitor (IF + pairs + quant features).')
  return parts.join(' ')
}

export async function fetchRiskReport(signal?: AbortSignal): Promise<RiskReport> {
  const url = `${import.meta.env.BASE_URL}data/risk_report_latest.json`
  const res = await fetch(url, { signal })
  if (!res.ok) throw new Error(`risk_report HTTP ${res.status}`)
  const data = (await res.json()) as RiskReport
  if (!data?.schema || !Array.isArray(data.board)) {
    throw new Error('invalid risk_report payload')
  }
  return data
}

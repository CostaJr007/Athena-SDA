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
  hurst_exponent_sma?: number
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
  status: BoardStatus
  xgb_class: string | null
  data_quality: DataQuality
  features_snapshot: FeaturesSnapshot
  pair: PairInfo | null
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
  n_pairs: number
  n_pair_elevated: number
  threshold: number
}

export interface RiskReport {
  schema: string
  generated_at: string
  day: string
  summary: RiskSummary
  board: BoardEntry[]
  top_pairs: TopPair[]
  model?: string
  train_meta?: Record<string, unknown>
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

  if (
    b.status === 'PAIR_ELEVATED' &&
    (pairLevel === 'CRITICAL' || b.attention_score >= 0.65 || pairRisk >= 0.9)
  ) {
    return 'HOSTILE'
  }
  if (b.status === 'PAIR_ELEVATED' || pairRisk >= 0.55) return 'SUSPECT'
  if (b.is_anomaly || b.status === 'ANOMALY') return 'ANOMALY'
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
    const tr = threatRank(boardThreat(a)) - threatRank(boardThreat(b))
    if (tr !== 0) return tr
    return b.attention_score - a.attention_score
  })
}

/** Local stub briefing — explains scores already computed (no invented threat). */
export function bobBrief(b: BoardEntry): string {
  const threat = boardThreat(b)
  const parts: string[] = [
    `${b.object_name} (NORAD ${b.norad_id}) · role ${b.role} · ${threat}.`,
    `attention=${b.attention_score.toFixed(3)} · anomaly=${b.anomaly_score.toFixed(3)} · status=${b.status}.`,
  ]
  const fs = b.features_snapshot ?? {}
  if (fs.hurst_exponent_sma != null) {
    parts.push(`Hurst=${fs.hurst_exponent_sma.toFixed(2)} (persistência da série).`)
  }
  if (fs.shannon_entropy_sma_30d != null) {
    parts.push(`Shannon H(Δa)=${fs.shannon_entropy_sma_30d.toFixed(2)}.`)
  }
  if (b.pair) {
    parts.push(
      `Par vs ${b.pair.asset_name} (#${b.pair.asset_norad}): dist ${b.pair.min_distance_km.toFixed(1)} km · pair_risk ${b.pair.pair_risk.toFixed(2)} (${b.pair.risk_level}).`,
    )
  }
  if (!b.data_quality?.reliable) {
    parts.push(`DQ: unreliable (${(b.data_quality?.issues ?? []).join(', ') || 'issues'}).`)
  } else if (b.data_quality?.issues?.length) {
    parts.push(`DQ issues: ${b.data_quality.issues.join(', ')}.`)
  }
  parts.push('Scores pré-calculados pelo monitor (IF + pares); Bob não inventa ameaça.')
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

/**
 * Walk-forward pré-report summary (public/data/walkforward_summary.json).
 * Validates lead-time of IF noise vs open-source report anchors.
 */

export interface WalkforwardParams {
  step_days: number
  holdout_days: number
  anomaly_threshold: number
  hit_window_days: number
}

export interface WalkforwardSummaryStats {
  n_interest_targets: number
  n_placebo_targets: number
  hit_rate_interest: number
  soft_hit_rate_interest: number
  hit_rate_placebo: number
  soft_hit_rate_placebo: number
  elevated_pre_peak_noise_rate_interest: number
  elevated_pre_peak_noise_rate_placebo: number
  mean_lead_time_days_interest: number
  median_lead_time_days_interest: number
  mean_max_anomaly_interest: number
  mean_max_anomaly_placebo: number
  anomaly_threshold: number
  interpretation?: string
}

export interface TargetMetrics {
  norad_id: number
  object_name: string
  hit_at_event?: boolean
  soft_hit_at_event?: boolean
  lead_time_days?: number | null
  anomaly_score_max?: number
  is_placebo?: boolean
  pre_peak_noise?: {
    elevated_noise_before_peak?: boolean
    noise_ramp?: number
    pre_peak_anomaly_max?: number
  }
}

export interface WalkforwardEvent {
  event_id: string
  type?: string
  t_peak?: string
  metrics?: Record<string, TargetMetrics>
  n_folds?: number
  sources?: string[]
}

export interface WalkforwardSummary {
  generated_at: string
  params: WalkforwardParams
  summary: WalkforwardSummaryStats
  events: WalkforwardEvent[]
}

export interface EventRow {
  event_id: string
  type: string
  t_peak: string
  norad_id: number
  object_name: string
  is_placebo: boolean
  hit: boolean
  lead_days: number | null
  elevated_pre: boolean
}

export function flattenEvents(wf: WalkforwardSummary | null): EventRow[] {
  if (!wf?.events?.length) return []
  const rows: EventRow[] = []
  for (const ev of wf.events) {
    const metrics = ev.metrics ?? {}
    for (const m of Object.values(metrics)) {
      if (!m) continue
      rows.push({
        event_id: ev.event_id,
        type: ev.type ?? 'event',
        t_peak: ev.t_peak ?? '—',
        norad_id: m.norad_id,
        object_name: m.object_name,
        is_placebo: Boolean(m.is_placebo),
        hit: Boolean(m.hit_at_event),
        lead_days:
          m.lead_time_days == null || Number.isNaN(m.lead_time_days)
            ? null
            : Number(m.lead_time_days),
        elevated_pre: Boolean(m.pre_peak_noise?.elevated_noise_before_peak),
      })
    }
  }
  // interest first, then by lead time desc
  return rows.sort((a, b) => {
    if (a.is_placebo !== b.is_placebo) return a.is_placebo ? 1 : -1
    return (b.lead_days ?? -1) - (a.lead_days ?? -1)
  })
}

export async function fetchWalkforwardSummary(
  signal?: AbortSignal,
): Promise<WalkforwardSummary> {
  const url = `${import.meta.env.BASE_URL}data/walkforward_summary.json`
  const res = await fetch(url, { signal })
  if (!res.ok) throw new Error(`walkforward HTTP ${res.status}`)
  const data = (await res.json()) as WalkforwardSummary
  if (!data?.summary || !Array.isArray(data.events)) {
    throw new Error('invalid walkforward payload')
  }
  return data
}

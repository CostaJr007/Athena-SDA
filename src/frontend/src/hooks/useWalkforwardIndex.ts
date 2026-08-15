import { useEffect, useState } from 'react'
import type { WfCaseHit } from '@/lib/investigation'

interface WfFile {
  events?: Array<{
    event_id?: string
    type?: string
    t_peak?: string
    metrics?: Record<
      string,
      {
        norad_id?: number
        object_name?: string
        hit_at_event?: boolean
        lead_time_days?: number | null
        anomaly_score_max?: number
        is_placebo?: boolean
      }
    >
  }>
}

export function useWalkforwardIndex(): WfCaseHit[] {
  const [cases, setCases] = useState<WfCaseHit[]>([])

  useEffect(() => {
    const ctrl = new AbortController()
    const url = `${import.meta.env.BASE_URL}data/walkforward_summary.json`
    void (async () => {
      try {
        const res = await fetch(url, { signal: ctrl.signal })
        if (!res.ok) return
        const data = (await res.json()) as WfFile
        if (ctrl.signal.aborted) return
        const out: WfCaseHit[] = []
        for (const ev of data.events ?? []) {
          if (!ev.event_id || !ev.metrics) continue
          for (const m of Object.values(ev.metrics)) {
            if (m.norad_id == null) continue
            out.push({
              eventId: ev.event_id,
              type: ev.type ?? '',
              tPeak: ev.t_peak ?? '',
              norad: m.norad_id,
              name: m.object_name ?? '',
              hit: !!m.hit_at_event,
              leadDays: m.lead_time_days ?? null,
              maxScore: m.anomaly_score_max ?? null,
              isPlacebo: !!m.is_placebo,
            })
          }
        }
        setCases(out)
      } catch {
        /* empty index */
      }
    })()
    return () => ctrl.abort()
  }, [])

  return cases
}

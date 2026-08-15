import { useEffect, useState } from 'react'
import { applyTriageMap, fetchRiskReport, type RiskReport } from '@/lib/risk-report'

export interface RiskReportState {
  status: 'loading' | 'ready' | 'error'
  report: RiskReport | null
  error: string | null
}

/**
 * Loads the static risk_report snapshot from public/data/.
 * Refresh with `python scripts/sync_frontend_data.py` after run-daily.
 */
export function useRiskReport(): RiskReportState {
  const [state, setState] = useState<RiskReportState>({
    status: 'loading',
    report: null,
    error: null,
  })

  useEffect(() => {
    const ctrl = new AbortController()
    void (async () => {
      try {
        let report = await fetchRiskReport(ctrl.signal)
        if (ctrl.signal.aborted) return
        try {
          let alerts: Record<string, { status?: string }> | undefined
          const live = await fetch('/api/alert-state', { signal: ctrl.signal })
          if (live.ok) {
            alerts = (await live.json())?.alerts
          } else {
            const snap = await fetch(
              `${import.meta.env.BASE_URL}data/alert_state.json`,
              { signal: ctrl.signal },
            )
            if (snap.ok) alerts = (await snap.json())?.alerts
          }
          if (alerts) report = applyTriageMap(report, alerts)
        } catch {
          /* triage overlay optional */
        }
        if (ctrl.signal.aborted) return
        setState({ status: 'ready', report, error: null })
      } catch (err) {
        if (ctrl.signal.aborted) return
        setState({
          status: 'error',
          report: null,
          error: err instanceof Error ? err.message : String(err),
        })
      }
    })()
    return () => ctrl.abort()
  }, [])

  return state
}

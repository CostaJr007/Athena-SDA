import { useEffect, useState } from 'react'
import { fetchRiskReport, type RiskReport } from '@/lib/risk-report'

export interface RiskReportState {
  status: 'loading' | 'ready' | 'error'
  report: RiskReport | null
  error: string | null
}

/**
 * Loads the static risk_report snapshot from public/data/.
 * Refresh with `scripts/sync_frontend_data.sh` after run-daily.
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
        const report = await fetchRiskReport(ctrl.signal)
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

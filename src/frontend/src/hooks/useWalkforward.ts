import { useEffect, useState } from 'react'
import {
  fetchWalkforwardSummary,
  type WalkforwardSummary,
} from '@/lib/walkforward'

export interface WalkforwardState {
  status: 'loading' | 'ready' | 'error'
  summary: WalkforwardSummary | null
  error: string | null
}

export function useWalkforward(): WalkforwardState {
  const [state, setState] = useState<WalkforwardState>({
    status: 'loading',
    summary: null,
    error: null,
  })

  useEffect(() => {
    const ctrl = new AbortController()
    void (async () => {
      try {
        const summary = await fetchWalkforwardSummary(ctrl.signal)
        if (ctrl.signal.aborted) return
        setState({ status: 'ready', summary, error: null })
      } catch (err) {
        if (ctrl.signal.aborted) return
        setState({
          status: 'error',
          summary: null,
          error: err instanceof Error ? err.message : String(err),
        })
      }
    })()
    return () => ctrl.abort()
  }, [])

  return state
}

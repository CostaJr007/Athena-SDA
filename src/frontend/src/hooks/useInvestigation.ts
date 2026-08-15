import { useEffect, useState } from 'react'
import type { InvestigationBundle, InvObject } from '@/lib/investigation'

function isBundle(data: unknown): data is InvestigationBundle {
  if (!data || typeof data !== 'object') return false
  const rec = data as InvestigationBundle
  return rec.schema === 'athena.investigation.v1' && Array.isArray(rec.objects)
}

function patchTriage(
  bundle: InvestigationBundle,
  alerts: Record<string, { status?: string }>,
): InvestigationBundle {
  const objects: InvObject[] = bundle.objects.map((o) => {
    if (o.norad == null) return o
    const status = alerts[String(o.norad)]?.status
    if (!status) return o
    return { ...o, triage: { ...(o.triage ?? {}), status } }
  })
  return { ...bundle, objects }
}

async function loadJson(url: string, signal: AbortSignal): Promise<unknown | null> {
  try {
    const res = await fetch(url, { signal })
    if (!res.ok) return null
    return await res.json()
  } catch {
    return null
  }
}

/**
 * Prefer sidecar investigation (live), then the synced static snapshot.
 * Overlay alert_state so ACK in the canvas matches the board.
 */
export function useInvestigation(): InvestigationBundle | null {
  const [bundle, setBundle] = useState<InvestigationBundle | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    const { signal } = ctrl
    const staticUrl = `${import.meta.env.BASE_URL}data/investigation_latest.json`
    void (async () => {
      const fromStatic = await loadJson(staticUrl, signal)
      const fromApi = await loadJson('/api/investigation', signal)
      let next: InvestigationBundle | null = null
      if (isBundle(fromApi)) next = fromApi
      else if (isBundle(fromStatic)) next = fromStatic
      if (!next) return

      const liveState = await loadJson('/api/alert-state', signal)
      const staticState = await loadJson(
        `${import.meta.env.BASE_URL}data/alert_state.json`,
        signal,
      )
      const state = (liveState ?? staticState) as { alerts?: Record<string, { status?: string }> } | null
      if (state?.alerts) next = patchTriage(next, state.alerts)
      if (!signal.aborted) setBundle(next)
    })()
    return () => ctrl.abort()
  }, [])

  return bundle
}

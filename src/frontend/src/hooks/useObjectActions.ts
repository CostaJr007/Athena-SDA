/**
 * Operator action log (Foundry Actions analogue).
 * Validate-only: never mutates IF/XGB scores (US 12,657,514; US 2024/0394296).
 */
import { useCallback, useEffect, useState } from 'react'

export type ActionName =
  | 'AcknowledgeAlert'
  | 'OpenCase'
  | 'TaskSatellite'
  | 'ResolveAlert'
  | 'SuppressAlert'

export interface ObjectAction {
  ts: string
  action: ActionName
  norad: number
  operator: string
  validate_only: boolean
  params?: Record<string, unknown>
}

const LS_KEY = 'athena.actions.v1'

function readLocal(): ObjectAction[] {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw) as ObjectAction[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeLocal(rows: ObjectAction[]) {
  localStorage.setItem(LS_KEY, JSON.stringify(rows.slice(-200)))
}

const STATUS_FOR_ACTION: Partial<Record<ActionName, string>> = {
  AcknowledgeAlert: 'ACKNOWLEDGED',
  ResolveAlert: 'RESOLVED',
  SuppressAlert: 'SUPPRESSED',
  OpenCase: 'OPEN',
}

export function useObjectActions(norad: number | null) {
  const [log, setLog] = useState<ObjectAction[]>(() => readLocal())
  const [triage, setTriage] = useState<string>('OPEN')

  useEffect(() => {
    if (norad == null) return
    const ctrl = new AbortController()
    void (async () => {
      try {
        const res = await fetch(`/api/alert-state?norad=${norad}`, { signal: ctrl.signal })
        if (!res.ok) return
        const data = (await res.json()) as { status?: string }
        if (data.status) setTriage(data.status)
      } catch {
        /* sidecar optional */
      }
    })()
    return () => ctrl.abort()
  }, [norad])

  const record = useCallback(
    async (action: ActionName, params: Record<string, unknown> = {}) => {
      if (norad == null) return
      const rec: ObjectAction = {
        ts: new Date().toISOString(),
        action,
        norad,
        operator: 'local',
        validate_only: true,
        params,
      }
      const next = [...readLocal(), rec]
      writeLocal(next)
      setLog(next)
      const status = STATUS_FOR_ACTION[action]
      if (status) {
        try {
          const res = await fetch('/api/alert-state', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ norad, status, operator: 'local', note: params.note ?? '' }),
          })
          if (res.ok) {
            const body = (await res.json()) as { status?: string }
            if (body.status) setTriage(body.status)
            return
          }
        } catch {
          /* fall through to action log */
        }
      }
      try {
        await fetch('/api/actions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(rec),
        })
      } catch {
        /* sidecar optional */
      }
    },
    [norad],
  )

  const forObject = norad == null ? [] : log.filter((a) => a.norad === norad)
  return { log: forObject, record, triage }
}

import { useEffect, useState } from 'react'
import { UI_GROUPS } from '@/lib/satellites'

export type CatalogFocus = 'all' | 'watchlist' | 'military' | 'selected'

interface CatalogPanelProps {
  open: boolean
  onClose: () => void
  counts: number[]
  groupVisible: boolean[]
  onToggleGroup: (index: number) => void
  focus: CatalogFocus
  onFocusChange: (f: CatalogFocus) => void
  watchlistN: number
  militaryN: number
}

/**
 * Floating catalog controls — layers + focus filter (not buried in Mission board).
 */
export default function CatalogPanel({
  open,
  onClose,
  counts,
  groupVisible,
  onToggleGroup,
  focus,
  onFocusChange,
  watchlistN,
  militaryN,
}: CatalogPanelProps) {
  if (!open) return null

  return (
    <div className="athena-panel pointer-events-auto flex max-h-[min(460px,60vh)] w-[min(300px,calc(100vw-1.5rem))] flex-col overflow-hidden">
      <div className="flex shrink-0 items-center justify-between border-b border-white/10 px-3 py-2">
        <div>
          <div className="text-[13px] font-semibold uppercase tracking-[0.14em] text-zinc-100">
            Catalog
          </div>
          <div className="mt-0.5 text-[11px] text-zinc-500">
            Layers · focus filter
          </div>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="athena-btn px-2 py-0.5 text-[11px]"
        >
          Close
        </button>
      </div>

      <div className="shrink-0 space-y-2 border-b border-white/10 px-3 py-2.5">
        <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">
          Globe focus
        </div>
        <div className="grid grid-cols-1 gap-1">
          {(
            [
              {
                id: 'all' as const,
                label: 'All catalog',
                hint: 'Full CelesTrak layers',
              },
              {
                id: 'watchlist' as const,
                label: `Watchlist only (${watchlistN})`,
                hint: 'Asset · suspect · baseline',
              },
              {
                id: 'military' as const,
                label: `Military focus (${militaryN})`,
                hint: 'Asset + suspect only',
              },
              {
                id: 'selected' as const,
                label: 'Selected only (Solo focus)',
                hint: 'Isolate analyzed object',
              },
            ] as const
          ).map((opt) => {
            const active = focus === opt.id
            return (
              <button
                key={opt.id}
                type="button"
                onClick={() => onFocusChange(opt.id)}
                className={`border px-2.5 py-2 text-left transition-colors ${
                  active
                    ? 'border-emerald-400/50 bg-emerald-400/12 text-emerald-100'
                    : 'border-white/10 bg-black/40 text-zinc-300 hover:bg-white/[0.04]'
                }`}
              >
                <div className="text-[13px] font-medium">{opt.label}</div>
                <div className="mt-0.5 text-[11px] text-zinc-500">{opt.hint}</div>
              </button>
            )
          })}
        </div>
        {focus !== 'all' && (
          <p className="text-[11px] leading-relaxed text-zinc-500">
            Layers below still apply inside the focus set. Mission board always
            lists the full watchlist.
          </p>
        )}
      </div>

      <WatchlistEditor />

      <div className="athena-scroll min-h-0 flex-1 overflow-y-auto px-2 py-2">
        <div className="mb-1.5 px-1 text-[11px] uppercase tracking-[0.16em] text-zinc-500">
          Layers
        </div>
        <div className="space-y-0.5">
          {UI_GROUPS.map((g, i) => (
            <button
              key={g.key}
              type="button"
              onClick={() => onToggleGroup(i)}
              className={`flex min-h-[34px] w-full items-center gap-2.5 px-2 py-1 text-left transition-opacity hover:bg-white/[0.05] ${
                groupVisible[i] ? '' : 'opacity-35'
              }`}
            >
              <span
                className="h-2 w-2 shrink-0"
                style={{
                  background: g.color,
                  boxShadow: `0 0 5px ${g.color}66`,
                }}
              />
              <span className="flex-1 truncate text-sm text-zinc-300">
                {g.label}
              </span>
              <span className="text-[13px] tabular-nums text-zinc-500">
                {(counts[i] ?? 0).toLocaleString()}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

interface WlObj {
  norad_id: number
  name: string
  role: string
}

function WatchlistEditor() {
  const [rows, setRows] = useState<WlObj[] | null>(null)
  const [norad, setNorad] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('suspect')
  const [err, setErr] = useState<string | null>(null)

  const refresh = async () => {
    try {
      const res = await fetch('/api/watchlist')
      if (!res.ok) {
        setRows(null)
        return
      }
      const data = (await res.json()) as { objects?: WlObj[] }
      setRows(data.objects ?? [])
      setErr(null)
    } catch {
      setRows(null)
    }
  }

  useEffect(() => {
    const id = window.setTimeout(() => {
      void refresh()
    }, 0)
    return () => window.clearTimeout(id)
  }, [])

  if (rows == null) {
    return (
      <p className="border-t border-white/10 px-3 py-2 text-[11px] text-zinc-600">
        Watchlist edits need the sidecar on :8787.
      </p>
    )
  }

  const add = async () => {
    const n = parseInt(norad, 10)
    if (!Number.isFinite(n)) {
      setErr('NORAD required')
      return
    }
    try {
      const res = await fetch('/api/watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ norad_id: n, name: name || `NORAD-${n}`, role }),
      })
      if (!res.ok) {
        setErr('upsert failed')
        return
      }
      setNorad('')
      setName('')
      await refresh()
    } catch {
      setErr('sidecar offline')
    }
  }

  const remove = async (id: number) => {
    await fetch(`/api/watchlist?norad=${id}`, { method: 'DELETE' })
    await refresh()
  }

  return (
    <div className="border-t border-white/10 px-3 py-2">
      <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">
        Watchlist · persist
      </div>
      <div className="mt-1.5 flex flex-wrap gap-1">
        <input
          value={norad}
          onChange={(e) => setNorad(e.target.value)}
          placeholder="NORAD"
          className="athena-input w-16 px-1 py-0.5 text-[11px]"
        />
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="name"
          className="athena-input min-w-0 flex-1 px-1 py-0.5 text-[11px]"
        />
        <select
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="athena-input px-1 py-0.5 text-[11px]"
        >
          <option value="asset">asset</option>
          <option value="suspect">suspect</option>
          <option value="baseline">baseline</option>
        </select>
        <button type="button" className="athena-btn px-1.5 py-0.5 text-[11px]" onClick={() => void add()}>
          Add
        </button>
      </div>
      {err && <p className="mt-1 text-[11px] text-rose-300">{err}</p>}
      <div className="athena-scroll mt-1 max-h-24 overflow-y-auto text-[11px] text-zinc-400">
        {rows.slice(0, 12).map((r) => (
          <div key={r.norad_id} className="flex items-center justify-between gap-1 py-0.5">
            <span className="truncate">
              #{r.norad_id} {r.name} · {r.role}
            </span>
            <button
              type="button"
              className="text-[10px] text-zinc-500 hover:text-rose-300"
              onClick={() => void remove(r.norad_id)}
            >
              rm
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

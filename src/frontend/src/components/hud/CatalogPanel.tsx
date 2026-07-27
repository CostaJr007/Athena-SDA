import { UI_GROUPS } from '@/lib/satellites'

export type CatalogFocus = 'all' | 'watchlist' | 'military'

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
    <div className="athena-panel pointer-events-auto flex max-h-[min(420px,55vh)] w-[min(300px,calc(100vw-1.5rem))] flex-col overflow-hidden">
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

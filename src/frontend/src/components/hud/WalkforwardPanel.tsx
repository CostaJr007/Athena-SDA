import { flattenEvents, type WalkforwardSummary } from '@/lib/walkforward'

interface WalkforwardPanelProps {
  summary: WalkforwardSummary | null
  status: 'loading' | 'ready' | 'error'
  onSelectNorad?: (norad: number) => void
}

function pct(v: number | undefined): string {
  if (v == null || Number.isNaN(v)) return '—'
  return `${Math.round(v * 100)}%`
}

export default function WalkforwardPanel({
  summary,
  status,
  onSelectNorad,
}: WalkforwardPanelProps) {
  if (status === 'loading') {
    return (
      <div className="border border-dashed border-white/15 px-2.5 py-3 text-[11px] text-zinc-500">
        Loading walk-forward…
      </div>
    )
  }
  if (status === 'error' || !summary) {
    return (
      <div className="border border-white/10 bg-black/40 px-2.5 py-2 text-[10px] text-zinc-500">
        Walk-forward snapshot unavailable. Run{' '}
        <code className="text-zinc-400">python scripts/run_walkforward.py</code>{' '}
        then sync.
      </div>
    )
  }

  const s = summary.summary
  const rows = flattenEvents(summary).slice(0, 8)

  return (
    <div className="border border-white/10 bg-black/50">
      <div className="border-b border-white/10 px-2.5 py-2">
        <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">
          Walk-forward pré-report
        </div>
        <div className="mt-1.5 grid grid-cols-2 gap-1.5 text-[11px]">
          <Cell
            k="Hit interesse"
            v={pct(s.hit_rate_interest)}
            tone="text-emerald-300"
          />
          <Cell
            k="Hit placebo"
            v={pct(s.hit_rate_placebo)}
            tone="text-zinc-300"
          />
          <Cell
            k="Ruído pré-peak"
            v={pct(s.elevated_pre_peak_noise_rate_interest)}
            tone="text-amber-300"
          />
          <Cell
            k="Lead médio"
            v={
              s.mean_lead_time_days_interest != null
                ? `${Math.round(s.mean_lead_time_days_interest)}d`
                : '—'
            }
            tone="text-sky-300"
          />
        </div>
        <p className="mt-2 text-[9px] leading-relaxed text-zinc-500">
          IF treina só no passado (past-only). Hit = score ≥ thr na janela do
          report open-source. Placebos devem ficar baixos.
        </p>
      </div>

      <div className="max-h-[180px] space-y-1 overflow-y-auto athena-scroll p-1.5">
        {rows.map((r) => (
          <button
            key={`${r.event_id}-${r.norad_id}`}
            type="button"
            onClick={() => onSelectNorad?.(r.norad_id)}
            className={`w-full border px-2 py-1.5 text-left transition-colors hover:bg-white/[0.04] ${
              r.is_placebo
                ? 'border-white/10 bg-black/30'
                : r.hit
                  ? 'border-emerald-400/25 bg-emerald-500/5'
                  : 'border-white/10 bg-black/40'
            }`}
          >
            <div className="flex items-center justify-between gap-1">
              <span className="truncate text-[10px] font-medium text-zinc-200">
                {r.object_name}
              </span>
              <span
                className={`shrink-0 text-[9px] tracking-wider ${
                  r.is_placebo
                    ? 'text-zinc-500'
                    : r.hit
                      ? 'text-emerald-300'
                      : 'text-rose-300'
                }`}
              >
                {r.is_placebo ? 'PLACEBO' : r.hit ? 'HIT' : 'MISS'}
              </span>
            </div>
            <div className="mt-0.5 flex justify-between text-[9px] text-zinc-500">
              <span className="truncate">{r.t_peak}</span>
              <span>
                {r.lead_days != null ? `lead ${Math.round(r.lead_days)}d` : '—'}
                {r.elevated_pre ? ' · pré↑' : ''}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}

function Cell({
  k,
  v,
  tone,
}: {
  k: string
  v: string
  tone: string
}) {
  return (
    <div className="border border-white/10 bg-black/40 px-2 py-1">
      <div className="text-[8px] uppercase tracking-wider text-zinc-500">{k}</div>
      <div className={`tabular-nums ${tone}`}>{v}</div>
    </div>
  )
}

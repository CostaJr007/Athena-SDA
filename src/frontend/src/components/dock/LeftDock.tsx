import { useEffect, useState, type ReactNode } from 'react'
import SidePanel from './SidePanel'
import {
  boardThreat,
  EMPTY_FILTERS,
  filtersActive,
  histogramExcluding,
  matchesFilters,
  sortedBoard,
  THREAT_STYLE,
  ROLE_HEX,
  type BoardFilters,
  type RiskReport,
} from '@/lib/risk-report'
import CountryFlag from '@/components/hud/CountryFlag'

interface LeftDockProps {
  selectedNorad: number | null
  onSelectNorad: (norad: number) => void
  report: RiskReport | null
  reportStatus: 'loading' | 'ready' | 'error'
  reportError?: string | null
  extra?: ReactNode
  /** Ontology cross-filters (role × country × orbit) driving board + globe */
  filters?: BoardFilters
  onFiltersChange?: (f: BoardFilters) => void
  /** Open the object-graph investigation for a NORAD */
  onInvestigate?: (norad: number) => void
}

export default function LeftDock({
  selectedNorad,
  onSelectNorad,
  report,
  reportStatus,
  reportError,
  extra,
  filters = EMPTY_FILTERS,
  onFiltersChange,
  onInvestigate,
}: LeftDockProps) {
  const boardAll = sortedBoard(report)
  const active = filtersActive(filters)
  const board = active ? boardAll.filter((b) => matchesFilters(b, filters)) : boardAll
  const threats = boardAll.map(boardThreat)
  const hostiles = threats.filter((t) => t === 'HOSTILE').length
  const suspects = threats.filter((t) => t === 'SUSPECT').length
  const anomalies = threats.filter((t) => t === 'ANOMALY').length
  const elevated = report?.summary.n_pair_elevated ?? 0

  const toggle = (dim: 'roles' | 'countries' | 'orbits', value: string) => {
    if (!onFiltersChange) return
    const cur = filters[dim]
    const next = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value]
    onFiltersChange({ ...filters, [dim]: next })
  }

  const clearFilters = () => onFiltersChange?.(EMPTY_FILTERS)
  const [filtersOpen, setFiltersOpen] = useState(false)
  useEffect(() => {
    if (!active) return
    const id = window.setTimeout(() => setFiltersOpen(true), 0)
    return () => window.clearTimeout(id)
  }, [active])

  return (
    <SidePanel
      side="left"
      title="Mission board"
      subtitle={
        report
          ? `ML day ${report.day} · ${report.summary.n_scored} scored`
          : 'Fusion scores · priority objects'
      }
      scrollBody={false}
      bodyClassName="flex flex-col"
      footer={
        <div className="grid grid-cols-4 gap-1.5 text-[13px]">
          <StatChip label="HST" value={hostiles} tone="text-rose-300" />
          <StatChip label="SUS" value={suspects} tone="text-amber-300" />
          <StatChip label="ANM" value={anomalies} tone="text-orange-300" />
          <StatChip label="PAIR" value={elevated} tone="text-sky-300" />
        </div>
      }
    >
      {extra && (
        <div className="shrink-0 max-h-[34%] overflow-y-auto border-b border-white/10 px-3 pt-2">
          {extra}
        </div>
      )}

      <section className="flex min-h-0 flex-1 flex-col">
        <div className="shrink-0 space-y-1 px-3 pb-1.5 pt-2">
          <div className="flex items-center justify-between gap-2">
            <div className="text-[12px] uppercase tracking-[0.18em] text-zinc-400">
              Priority tracks{active ? ` · ${board.length}` : ` · ${boardAll.length}`}
            </div>
            <div className="flex items-center gap-1.5">
              {active && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="border border-white/15 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-zinc-300 hover:border-emerald-400/50 hover:text-emerald-200"
                >
                  Clear
                </button>
              )}
              <button
                type="button"
                onClick={() => setFiltersOpen((v) => !v)}
                className="border border-white/15 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-zinc-400 hover:border-emerald-400/40 hover:text-zinc-200"
              >
                Filters {filtersOpen ? '▾' : '▸'}
              </button>
            </div>
          </div>
          {report && (
            <p className="truncate text-[11px] text-zinc-500">
              anom {report.summary.n_anomalies} · mil{' '}
              {report.summary.n_military_detections ?? '—'} · thr{' '}
              {report.summary.threshold.toFixed(2)}
              {report.top_pairs?.[0]
                ? ` · ${report.top_pairs[0].suspect_name} → ${report.top_pairs[0].asset_name} ${report.top_pairs[0].min_distance_km.toFixed(0)} km`
                : ''}
            </p>
          )}
          {filtersOpen && (
            <div className="border border-white/10 bg-black/50 px-2 py-1.5">
              <FilterHistogram
                label="Role"
                values={histogramExcluding(boardAll, filters, 'roles', (b) => b.role)}
                selected={filters.roles}
                onToggle={(v) => toggle('roles', v)}
                hex={(v) => ROLE_HEX[v] ?? '#a1a1aa'}
              />
              <FilterHistogram
                label="Country"
                values={histogramExcluding(
                  boardAll,
                  filters,
                  'countries',
                  (b) => b.country,
                )}
                selected={filters.countries}
                onToggle={(v) => toggle('countries', v)}
              />
              <FilterHistogram
                label="Orbit"
                values={histogramExcluding(
                  boardAll,
                  filters,
                  'orbits',
                  (b) => b.orbit_class,
                )}
                selected={filters.orbits}
                onToggle={(v) => toggle('orbits', v)}
              />
            </div>
          )}
        </div>

        <div className="athena-scroll min-h-0 flex-1 space-y-1 overflow-y-auto px-3 pb-3">
          {reportStatus === 'loading' && (
            <div className="border border-dashed border-white/15 px-3 py-4 text-center text-[14px] text-zinc-400">
              Loading risk_report…
            </div>
          )}

          {reportStatus === 'error' && (
            <div className="border border-rose-400/30 bg-rose-500/10 px-3 py-3 text-[14px] text-rose-200">
              Risk report unavailable
              {reportError ? `: ${reportError}` : ''}. Run{' '}
              <code className="text-rose-100">scripts/sync_frontend_data.sh</code>
            </div>
          )}

          {reportStatus === 'ready' && board.length === 0 && (
            <div className="border border-dashed border-white/15 px-3 py-4 text-center text-[14px] text-zinc-400">
              Empty board
            </div>
          )}

          {board.map((t) => {
            const threat = boardThreat(t)
            const style = THREAT_STYLE[threat]
            const selected = selectedNorad === t.norad_id
            const attPct = Math.max(0, Math.min(100, t.attention_score * 100))
            return (
              <div
                key={t.norad_id}
                role="button"
                tabIndex={0}
                onClick={() => onSelectNorad(t.norad_id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSelectNorad(t.norad_id)
                  }
                }}
                className={`w-full cursor-pointer border px-2 py-1 text-left transition-colors ${
                  selected
                    ? 'border-emerald-400/50 bg-emerald-400/10'
                    : `${style.border} ${style.bg} hover:bg-white/[0.04]`
                }`}
                title={`${t.object_name} · att ${t.attention_score.toFixed(2)} · anom ${t.anomaly_score.toFixed(2)}${
                  t.pair
                    ? ` · → ${t.pair.asset_name} ${t.pair.min_distance_km.toFixed(0)} km`
                    : ''
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <CountryFlag code={t.country} size={14} />
                  <span className="shrink-0 text-[12px] font-semibold tabular-nums text-zinc-100">
                    #{t.norad_id}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[12px] text-zinc-200">
                    {t.object_name}
                  </span>
                  {t.is_military_detection && (
                    <span className="shrink-0 text-[9px] uppercase tracking-wider text-amber-200">
                      mil
                    </span>
                  )}
                  <span
                    className={`shrink-0 border px-1 py-px text-[9px] tracking-wider ${style.border} ${style.color}`}
                  >
                    {style.label}
                  </span>
                </div>
                <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-zinc-500">
                  <span className="min-w-0 flex-1 truncate">
                    {t.attention_score.toFixed(2)}/{t.anomaly_score.toFixed(2)}
                    {t.pair ? ` · ${t.pair.min_distance_km.toFixed(0)} km` : ''}
                    {t.pair?.pc != null ? ` · Pc` : ''}
                    {t.triage && t.triage !== 'OPEN' ? ` · ${t.triage}` : ''}
                  </span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      onInvestigate?.(t.norad_id)
                    }}
                    className="shrink-0 border border-violet-400/30 px-1 py-px text-[9px] uppercase tracking-wider text-violet-200 hover:bg-violet-400/10"
                    title="Open object-graph investigation"
                  >
                    Graph
                  </button>
                  <a
                    href={`${import.meta.env.BASE_URL}reports/quant_${t.norad_id}_latest.html`}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="shrink-0 border border-emerald-400/30 px-1 py-px text-[9px] uppercase tracking-wider text-emerald-300/90 hover:bg-emerald-400/10"
                    title="Quant report (new tab)"
                  >
                    Quant
                  </a>
                </div>
                <div className="mt-0.5 h-0.5 overflow-hidden bg-black">
                  <div
                    className={`h-full ${style.bar}`}
                    style={{ width: `${attPct}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      </section>
    </SidePanel>
  )
}

function StatChip({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: string
}) {
  return (
    <div className="border border-white/10 bg-black/60 px-1.5 py-1.5 text-center">
      <div className="text-zinc-400">{label}</div>
      <div className={`mt-0.5 text-sm tabular-nums ${tone}`}>{value}</div>
    </div>
  )
}

interface FilterHistogramProps {
  label: string
  values: Array<{ value: string; count: number }>
  selected: string[]
  onToggle: (value: string) => void
  hex?: (value: string) => string
}

/** Histogram bars that regenerate after sibling filters (Palantir 011). */
function FilterHistogram({ label, values, selected, onToggle, hex }: FilterHistogramProps) {
  const max = Math.max(1, ...values.map((v) => v.count))
  if (values.length === 0) return null
  return (
    <div className="mt-1">
      <div className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className="mt-0.5 space-y-0.5">
        {values.map(({ value, count }) => {
          const on = selected.includes(value)
          const color = hex ? hex(value) : '#34d399'
          return (
            <button
              key={value}
              type="button"
              onClick={() => onToggle(value)}
              title={`${label}: ${value} (${count})`}
              className={`flex w-full items-center gap-2 px-1 py-0.5 text-left text-[11px] tabular-nums ${
                on ? 'bg-emerald-400/12 text-emerald-100' : 'text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200'
              }`}
            >
              <span className="w-[4.5rem] shrink-0 truncate">{value}</span>
              <span className="relative h-2 min-w-0 flex-1 bg-black/80">
                <span
                  className="absolute inset-y-0 left-0"
                  style={{
                    width: `${Math.round((count / max) * 100)}%`,
                    background: color,
                    opacity: on ? 0.9 : 0.45,
                  }}
                />
              </span>
              <span className="w-5 shrink-0 text-right text-[10px] text-zinc-500">{count}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

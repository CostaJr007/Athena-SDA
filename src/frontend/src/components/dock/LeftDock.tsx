import type { ReactNode } from 'react'
import SidePanel from './SidePanel'
import {
  boardHistogram,
  boardThreat,
  EMPTY_FILTERS,
  filtersActive,
  matchesFilters,
  sortedBoard,
  THREAT_HEX,
  THREAT_STYLE,
  ROLE_HEX,
  type BoardFilters,
  type RiskReport,
} from '@/lib/risk-report'
import { countryLabel } from '@/lib/country-flag'
import CountryFlag from '@/components/hud/CountryFlag'

interface LeftDockProps {
  selectedNorad: number | null
  onSelectNorad: (norad: number) => void
  report: RiskReport | null
  reportStatus: 'loading' | 'ready' | 'error'
  reportError?: string | null
  extra?: ReactNode
  /** Open in-app walk-forward PoC panel (globe HUD tab) */
  onOpenPoc?: () => void
  pocOpen?: boolean
  /** Ontology cross-filters (role × country × orbit) driving board + globe */
  filters?: BoardFilters
  onFiltersChange?: (f: BoardFilters) => void
}

export default function LeftDock({
  selectedNorad,
  onSelectNorad,
  report,
  reportStatus,
  reportError,
  extra,
  onOpenPoc,
  pocOpen = false,
  filters = EMPTY_FILTERS,
  onFiltersChange,
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

  return (
    <SidePanel
      side="left"
      title="Mission board"
      subtitle={
        report
          ? `ML day ${report.day} · ${report.summary.n_scored} scored`
          : 'Fusion scores · priority objects'
      }
      footer={
        <div className="grid grid-cols-4 gap-1.5 text-[13px]">
          <StatChip label="HST" value={hostiles} tone="text-rose-300" />
          <StatChip label="SUS" value={suspects} tone="text-amber-300" />
          <StatChip label="ANM" value={anomalies} tone="text-orange-300" />
          <StatChip label="PAIR" value={elevated} tone="text-sky-300" />
        </div>
      }
    >
      <div className="space-y-4">
        {extra}

        <section className="border border-emerald-400/25 bg-emerald-500/5 px-2.5 py-2">
          <div className="text-[13px] uppercase tracking-[0.2em] text-emerald-300/90">
            ML proof of concept
          </div>
          <p className="mt-1.5 text-[13px] leading-relaxed text-zinc-400">
            Walk-forward validation: GEO interest 5/5 hard hits vs civil EO placebos 0/7
            (Claims A+B). Opens as a panel on this console.
          </p>
          <button
            type="button"
            onClick={() => onOpenPoc?.()}
            className={`mt-2 inline-flex w-full items-center justify-center gap-1.5 border px-2 py-1.5 text-[12px] font-medium uppercase tracking-[0.12em] transition-colors ${
              pocOpen
                ? 'border-emerald-300/70 bg-emerald-400/20 text-emerald-100'
                : 'border-emerald-400/35 bg-black/40 text-emerald-300 hover:border-emerald-300/60 hover:text-emerald-200'
            }`}
          >
            {pocOpen ? 'PoC panel open' : 'Open PoC panel'}
          </button>
        </section>

        {report && (
          <section className="border border-white/10 bg-black/50 px-2.5 py-2">
            <div className="text-[13px] uppercase tracking-[0.2em] text-zinc-400">
              Risk report
            </div>
            <div className="mt-1.5 grid grid-cols-2 gap-1.5 text-[14px]">
              <Meta k="Anomalies" v={String(report.summary.n_anomalies)} />
              <Meta
                k="Mil detect"
                v={String(report.summary.n_military_detections ?? '—')}
              />
              <Meta k="Pairs" v={String(report.summary.n_pairs)} />
              <Meta k="Elevated" v={String(report.summary.n_pair_elevated)} />
              <Meta k="Thr" v={report.summary.threshold.toFixed(2)} />
              <Meta k="Scored" v={String(report.summary.n_scored)} />
            </div>
            {report.doctrine && (
              <p className="mt-1.5 text-[11px] uppercase tracking-wider text-zinc-500">
                {report.doctrine.replace(/_/g, ' ')}
              </p>
            )}
            {report.top_pairs?.[0] && (
              <p className="mt-2 text-[13px] leading-relaxed text-zinc-400">
                Top pair:{' '}
                <span className="text-zinc-200">
                  {report.top_pairs[0].suspect_name}
                </span>{' '}
                → {report.top_pairs[0].asset_name} ·{' '}
                {report.top_pairs[0].min_distance_km.toFixed(0)} km ·{' '}
                {report.top_pairs[0].risk_level}
              </p>
            )}
            <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1 border-t border-white/10 pt-2 text-[12px] text-zinc-400">
              {(
                [
                  ['HOSTILE', THREAT_HEX.HOSTILE],
                  ['SUSPECT', THREAT_HEX.SUSPECT],
                  ['ANOMALY', THREAT_HEX.ANOMALY],
                  ['NOMINAL', THREAT_HEX.NOMINAL],
                  ['asset', ROLE_HEX.asset],
                ] as const
              ).map(([label, hex]) => (
                <span key={label} className="inline-flex items-center gap-1">
                  <span
                    className="inline-block h-1.5 w-1.5"
                    style={{ background: hex }}
                  />
                  {label}
                </span>
              ))}
            </div>
          </section>
        )}

        <section className="border border-white/10 bg-black/50 px-2.5 py-2">
          <div className="flex items-center justify-between">
            <div className="text-[13px] uppercase tracking-[0.2em] text-zinc-400">
              Cross-filters
            </div>
            {active && (
              <button
                type="button"
                onClick={clearFilters}
                className="border border-white/15 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-zinc-300 hover:border-emerald-400/50 hover:text-emerald-200"
              >
                Clear
              </button>
            )}
          </div>
          <p className="mt-1 text-[11px] uppercase tracking-wider text-zinc-500">
            role · country · orbit (histogram drill-down)
          </p>
          <FilterHistogram
            label="Role"
            values={boardHistogram(boardAll, (b) => b.role)}
            selected={filters.roles}
            onToggle={(v) => toggle('roles', v)}
            hex={(v) => ROLE_HEX[v] ?? '#a1a1aa'}
          />
          <FilterHistogram
            label="Country"
            values={boardHistogram(boardAll, (b) => b.country)}
            selected={filters.countries}
            onToggle={(v) => toggle('countries', v)}
          />
          <FilterHistogram
            label="Orbit"
            values={boardHistogram(boardAll, (b) => b.orbit_class)}
            selected={filters.orbits}
            onToggle={(v) => toggle('orbits', v)}
          />
          {active && (
            <p className="mt-1.5 text-[12px] text-emerald-300/90">
              {board.length} of {boardAll.length} objects shown
            </p>
          )}
        </section>

        <section>
          <div className="mb-2 text-[13px] uppercase tracking-[0.2em] text-zinc-400">
            Priority tracks{active ? ` · ${board.length}` : ''}
          </div>

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

          <div className="space-y-1.5">
            {board.map((t) => {
              const threat = boardThreat(t)
              const style = THREAT_STYLE[threat]
              const active = selectedNorad === t.norad_id
              const attPct = Math.max(0, Math.min(100, t.attention_score * 100))
              return (
                <button
                  key={t.norad_id}
                  type="button"
                  onClick={() => onSelectNorad(t.norad_id)}
                  className={`w-full border px-2.5 py-2 text-left transition-colors ${
                    active
                      ? 'border-emerald-400/50 bg-emerald-400/10'
                      : `${style.border} ${style.bg} hover:bg-white/[0.04]`
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[14px] font-semibold text-zinc-100">
                      #{t.norad_id}
                    </span>
                    <span
                      className={`border px-1.5 py-0.5 text-[12px] tracking-wider ${style.border} ${style.color}`}
                    >
                      {style.label}
                    </span>
                  </div>
                  <div className="mt-0.5 flex min-w-0 items-center gap-2">
                    <CountryFlag code={t.country} size={18} />
                    <span className="min-w-0 flex-1 truncate text-sm text-zinc-300">
                      {t.object_name}
                    </span>
                    <a
                      href={`${import.meta.env.BASE_URL}reports/quant_${t.norad_id}_latest.html`}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="shrink-0 border border-emerald-400/30 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-emerald-300/90 hover:bg-emerald-400/10"
                      title="Quant report (new tab)"
                    >
                      Quant
                    </a>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[13px] text-zinc-400">
                    <span>
                      att {t.attention_score.toFixed(2)} · anom{' '}
                      {t.anomaly_score.toFixed(2)}
                    </span>
                    <span className="text-zinc-400">
                      {t.role} · {countryLabel(t.country)}
                    </span>
                  </div>
                  {(t.is_military_detection ||
                    t.is_platform_health_flag ||
                    t.is_calibration_object) && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {t.is_military_detection && (
                        <span className="border border-amber-400/40 bg-amber-400/10 px-1 py-0.5 text-[10px] uppercase tracking-wider text-amber-200">
                          mil detect
                        </span>
                      )}
                      {t.is_platform_health_flag && (
                        <span className="border border-sky-400/40 bg-sky-400/10 px-1 py-0.5 text-[10px] uppercase tracking-wider text-sky-200">
                          asset health
                        </span>
                      )}
                      {t.is_calibration_object && (
                        <span className="border border-zinc-500/40 bg-zinc-500/10 px-1 py-0.5 text-[10px] uppercase tracking-wider text-zinc-400">
                          calibration
                        </span>
                      )}
                    </div>
                  )}
                  {t.pair && (
                    <div className="mt-1 truncate text-[13px] text-zinc-400">
                      → {t.pair.asset_name} · {t.pair.min_distance_km.toFixed(0)} km ·{' '}
                      {t.pair.risk_level}
                    </div>
                  )}
                  <div className="mt-1.5 h-1 overflow-hidden bg-black">
                    <div
                      className={`h-full ${style.bar}`}
                      style={{ width: `${attPct}%` }}
                    />
                  </div>
                </button>
              )
            })}
          </div>
        </section>
      </div>
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

function Meta({ k, v }: { k: string; v: string }) {
  return (
    <div className="border border-white/10 bg-black/40 px-2 py-1">
      <div className="text-[12px] uppercase tracking-wider text-zinc-400">{k}</div>
      <div className="tabular-nums text-zinc-100">{v}</div>
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

/** One histogram row (Palantir 011 drill-down): click a bar to toggle a filter. */
function FilterHistogram({ label, values, selected, onToggle, hex }: FilterHistogramProps) {
  const max = Math.max(1, ...values.map((v) => v.count))
  if (values.length === 0) return null
  return (
    <div className="mt-2">
      <div className="text-[11px] uppercase tracking-wider text-zinc-500">{label}</div>
      <div className="mt-1 flex flex-wrap gap-1">
        {values.map(({ value, count }) => {
          const on = selected.includes(value)
          const color = hex ? hex(value) : undefined
          return (
            <button
              key={value}
              type="button"
              onClick={() => onToggle(value)}
              title={`${label}: ${value} (${count})`}
              className={`group relative flex h-6 min-w-[26px] items-center justify-center border px-1 text-[11px] tabular-nums transition-colors ${
                on
                  ? 'border-emerald-300/70 bg-emerald-400/20 text-emerald-100'
                  : 'border-white/12 text-zinc-400 hover:border-white/30 hover:text-zinc-200'
              }`}
            >
              <span
                className="absolute inset-x-0 bottom-0 opacity-25"
                style={{ background: color ?? 'currentColor', height: `${Math.round((count / max) * 100)}%` }}
              />
              <span className="relative">{value}</span>
              <span className="relative ml-0.5 text-[9px] opacity-70">{count}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

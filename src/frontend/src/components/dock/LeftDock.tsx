import type { ReactNode } from 'react'
import SidePanel from './SidePanel'
import {
  boardThreat,
  sortedBoard,
  THREAT_HEX,
  ROLE_HEX,
  type RiskReport,
  type Threat,
} from '@/lib/risk-report'
import { countryLabel } from '@/lib/country-flag'
import CountryFlag from '@/components/hud/CountryFlag'

const THREAT_STYLE: Record<
  Threat,
  { label: string; color: string; bg: string; border: string; bar: string }
> = {
  HOSTILE: {
    label: 'HOSTILE',
    color: 'text-rose-300',
    bg: 'bg-rose-500/10',
    border: 'border-rose-400/35',
    bar: 'bg-rose-400/90',
  },
  SUSPECT: {
    label: 'SUSPECT',
    color: 'text-amber-300',
    bg: 'bg-amber-500/10',
    border: 'border-amber-400/35',
    bar: 'bg-amber-400/90',
  },
  ANOMALY: {
    label: 'ANOMALY',
    color: 'text-orange-300',
    bg: 'bg-orange-500/10',
    border: 'border-orange-400/35',
    bar: 'bg-orange-400/90',
  },
  NOMINAL: {
    label: 'NOMINAL',
    color: 'text-emerald-300',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-400/35',
    bar: 'bg-emerald-400/80',
  },
}

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
}: LeftDockProps) {
  const board = sortedBoard(report)
  const threats = board.map(boardThreat)
  const hostiles = threats.filter((t) => t === 'HOSTILE').length
  const suspects = threats.filter((t) => t === 'SUSPECT').length
  const anomalies = threats.filter((t) => t === 'ANOMALY').length
  const elevated = report?.summary.n_pair_elevated ?? 0

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

        <section>
          <div className="mb-2 text-[13px] uppercase tracking-[0.2em] text-zinc-400">
            Priority tracks
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

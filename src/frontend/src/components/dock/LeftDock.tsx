import type { ReactNode } from 'react'
import SidePanel from './SidePanel'
import LayerPanel from '@/components/hud/LayerPanel'
import WalkforwardPanel from '@/components/hud/WalkforwardPanel'
import {
  boardThreat,
  sortedBoard,
  THREAT_HEX,
  ROLE_HEX,
  type RiskReport,
  type Threat,
} from '@/lib/risk-report'
import type { WalkforwardSummary } from '@/lib/walkforward'

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
  counts: number[]
  groupVisible: boolean[]
  onToggleGroup: (index: number) => void
  selectedNorad: number | null
  onSelectNorad: (norad: number) => void
  report: RiskReport | null
  reportStatus: 'loading' | 'ready' | 'error'
  reportError?: string | null
  walkforward?: WalkforwardSummary | null
  walkforwardStatus?: 'loading' | 'ready' | 'error'
  extra?: ReactNode
}

export default function LeftDock({
  counts,
  groupVisible,
  onToggleGroup,
  selectedNorad,
  onSelectNorad,
  report,
  reportStatus,
  reportError,
  walkforward = null,
  walkforwardStatus = 'error',
  extra,
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
        <div className="grid grid-cols-4 gap-1.5 text-[10px]">
          <StatChip label="HST" value={hostiles} tone="text-rose-300" />
          <StatChip label="SUS" value={suspects} tone="text-amber-300" />
          <StatChip label="ANM" value={anomalies} tone="text-orange-300" />
          <StatChip label="PAIR" value={elevated} tone="text-sky-300" />
        </div>
      }
    >
      <div className="space-y-4">
        {extra}

        {report && (
          <section className="border border-white/10 bg-black/50 px-2.5 py-2">
            <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              Risk report
            </div>
            <div className="mt-1.5 grid grid-cols-2 gap-1.5 text-[11px]">
              <Meta k="Anomalies" v={String(report.summary.n_anomalies)} />
              <Meta k="Pairs" v={String(report.summary.n_pairs)} />
              <Meta k="Elevated" v={String(report.summary.n_pair_elevated)} />
              <Meta k="Thr" v={report.summary.threshold.toFixed(2)} />
            </div>
            {report.top_pairs?.[0] && (
              <p className="mt-2 text-[10px] leading-relaxed text-zinc-400">
                Top pair:{' '}
                <span className="text-zinc-200">
                  {report.top_pairs[0].suspect_name}
                </span>{' '}
                → {report.top_pairs[0].asset_name} ·{' '}
                {report.top_pairs[0].min_distance_km.toFixed(0)} km ·{' '}
                {report.top_pairs[0].risk_level}
              </p>
            )}
            <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1 border-t border-white/10 pt-2 text-[9px] text-zinc-500">
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
          <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Validation · lead-time
          </div>
          <WalkforwardPanel
            summary={walkforward}
            status={walkforwardStatus}
            onSelectNorad={onSelectNorad}
          />
        </section>

        <section>
          <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Priority tracks
          </div>

          {reportStatus === 'loading' && (
            <div className="border border-dashed border-white/15 px-3 py-4 text-center text-[11px] text-zinc-500">
              Loading risk_report…
            </div>
          )}

          {reportStatus === 'error' && (
            <div className="border border-rose-400/30 bg-rose-500/10 px-3 py-3 text-[11px] text-rose-200">
              Risk report unavailable
              {reportError ? `: ${reportError}` : ''}. Run{' '}
              <code className="text-rose-100">scripts/sync_frontend_data.sh</code>
            </div>
          )}

          {reportStatus === 'ready' && board.length === 0 && (
            <div className="border border-dashed border-white/15 px-3 py-4 text-center text-[11px] text-zinc-500">
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
                    <span className="text-[11px] font-semibold text-zinc-100">
                      #{t.norad_id}
                    </span>
                    <span
                      className={`border px-1.5 py-0.5 text-[9px] tracking-wider ${style.border} ${style.color}`}
                    >
                      {style.label}
                    </span>
                  </div>
                  <div className="mt-0.5 truncate text-xs text-zinc-300">
                    {t.object_name}
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[10px] text-zinc-500">
                    <span>
                      att {t.attention_score.toFixed(2)} · anom{' '}
                      {t.anomaly_score.toFixed(2)}
                    </span>
                    <span className="text-zinc-400">
                      {t.role} · {t.country}
                    </span>
                  </div>
                  {t.pair && (
                    <div className="mt-1 truncate text-[10px] text-zinc-500">
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

        <section>
          <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Catalog layers
          </div>
          <div className="border border-white/10 bg-black/50 px-1 py-1.5">
            <LayerPanel
              counts={counts}
              visible={groupVisible}
              onToggle={onToggleGroup}
              variant="bare"
            />
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
      <div className="text-zinc-500">{label}</div>
      <div className={`mt-0.5 text-sm tabular-nums ${tone}`}>{value}</div>
    </div>
  )
}

function Meta({ k, v }: { k: string; v: string }) {
  return (
    <div className="border border-white/10 bg-black/40 px-2 py-1">
      <div className="text-[9px] uppercase tracking-wider text-zinc-500">{k}</div>
      <div className="tabular-nums text-zinc-100">{v}</div>
    </div>
  )
}

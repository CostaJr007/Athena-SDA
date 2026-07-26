import type { ReactNode } from 'react'
import SidePanel from './SidePanel'
import LayerPanel from '@/components/hud/LayerPanel'
import { TRACKS, type Threat } from '@/lib/athena-tracks'

const THREAT_STYLE: Record<
  Threat,
  { label: string; color: string; bg: string; border: string }
> = {
  HOSTILE: {
    label: 'HOSTILE',
    color: 'text-rose-300',
    bg: 'bg-rose-500/10',
    border: 'border-rose-400/35',
  },
  SUSPECT: {
    label: 'SUSPECT',
    color: 'text-amber-300',
    bg: 'bg-amber-500/10',
    border: 'border-amber-400/35',
  },
  ANOMALY: {
    label: 'ANOMALY',
    color: 'text-orange-300',
    bg: 'bg-orange-500/10',
    border: 'border-orange-400/35',
  },
  NOMINAL: {
    label: 'NOMINAL',
    color: 'text-emerald-300',
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-400/35',
  },
}

interface LeftDockProps {
  counts: number[]
  groupVisible: boolean[]
  onToggleGroup: (index: number) => void
  selectedNorad: number | null
  onSelectNorad: (norad: number) => void
  extra?: ReactNode
}

export default function LeftDock({
  counts,
  groupVisible,
  onToggleGroup,
  selectedNorad,
  onSelectNorad,
  extra,
}: LeftDockProps) {
  const hostiles = TRACKS.filter((t) => t.threat === 'HOSTILE').length
  const suspects = TRACKS.filter((t) => t.threat === 'SUSPECT').length
  const anomalies = TRACKS.filter((t) => t.threat === 'ANOMALY').length

  const sorted = [...TRACKS].sort((a, b) => {
    const rank: Record<Threat, number> = {
      HOSTILE: 0,
      SUSPECT: 1,
      ANOMALY: 2,
      NOMINAL: 3,
    }
    return rank[a.threat] - rank[b.threat] || b.conf - a.conf
  })

  return (
    <SidePanel
      side="left"
      title="Mission board"
      subtitle="Fusion scores · priority objects"
      footer={
        <div className="grid grid-cols-3 gap-1.5 text-[10px]">
          <StatChip label="HST" value={hostiles} tone="text-rose-300" />
          <StatChip label="SUS" value={suspects} tone="text-amber-300" />
          <StatChip label="ANM" value={anomalies} tone="text-orange-300" />
        </div>
      }
    >
      <div className="space-y-4">
        {extra}

        <section>
          <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Priority tracks
          </div>
          <div className="space-y-1.5">
            {sorted.map((t) => {
              const style = THREAT_STYLE[t.threat]
              const active = selectedNorad === Number(t.id)
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => onSelectNorad(Number(t.id))}
                  className={`w-full border px-2.5 py-2 text-left transition-colors ${
                    active
                      ? 'border-emerald-400/50 bg-emerald-400/10'
                      : `${style.border} ${style.bg} hover:bg-white/[0.04]`
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[11px] font-semibold text-zinc-100">
                      #{t.id}
                    </span>
                    <span
                      className={`border px-1.5 py-0.5 text-[9px] tracking-wider ${style.border} ${style.color}`}
                    >
                      {style.label}
                    </span>
                  </div>
                  <div className="mt-0.5 truncate text-xs text-zinc-300">{t.name}</div>
                  <div className="mt-1.5 flex items-center justify-between text-[10px] text-zinc-500">
                    <span>
                      H {t.ent.toFixed(2)} · conf {(t.conf * 100).toFixed(0)}%
                    </span>
                    <span className="text-zinc-400">{t.country}</span>
                  </div>
                  <div className="mt-1.5 h-1 overflow-hidden bg-black">
                    <div
                      className="h-full bg-emerald-400/80"
                      style={{ width: `${t.conf * 100}%` }}
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
    <div className="border border-white/10 bg-black/60 px-2 py-1.5 text-center">
      <div className="text-zinc-500">{label}</div>
      <div className={`mt-0.5 text-sm tabular-nums ${tone}`}>{value}</div>
    </div>
  )
}

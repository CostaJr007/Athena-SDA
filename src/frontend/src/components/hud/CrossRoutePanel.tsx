import type { ReactNode } from 'react'
import type { SatInfo } from '@/lib/satellites'
import type { CrossAnalysis } from '@/lib/orbit-crossing'
import { formatEta, formatRange } from '@/lib/orbit-crossing'

export type CompareSlot = 'A' | 'B'

interface CrossRoutePanelProps {
  enabled: boolean
  onToggle: (on: boolean) => void
  pickSlot: CompareSlot
  onPickSlot: (slot: CompareSlot) => void
  satA: SatInfo | null
  satB: SatInfo | null
  onClearSlot: (slot: CompareSlot) => void
  onClearAll: () => void
  onUseSelectedAs: (slot: CompareSlot) => void
  hasPrimarySelection: boolean
  analysis: CrossAnalysis | null
  nowMs: number
  computing: boolean
}

export default function CrossRoutePanel({
  enabled,
  onToggle,
  pickSlot,
  onPickSlot,
  satA,
  satB,
  onClearSlot,
  onClearAll,
  onUseSelectedAs,
  hasPrimarySelection,
  analysis,
  nowMs,
  computing,
}: CrossRoutePanelProps) {
  return (
    <section className="border border-white/12 bg-black/55 p-2.5">
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Conjunction lab
          </div>
          <div className="mt-0.5 text-[11px] text-zinc-400">
            Two tracks · orbit path + TCA
          </div>
        </div>
        <button
          type="button"
          onClick={() => onToggle(!enabled)}
          className={`px-2.5 py-1 text-[10px] tracking-wider ${
            enabled ? 'athena-btn athena-btn-warn' : 'athena-btn'
          }`}
        >
          {enabled ? 'ON' : 'OFF'}
        </button>
      </div>

      {enabled && (
        <div className="mt-3 space-y-3">
          <div className="grid grid-cols-2 gap-1.5">
            <SlotButton
              slot="A"
              active={pickSlot === 'A'}
              sat={satA}
              accent="a"
              onPick={() => onPickSlot('A')}
              onClear={() => onClearSlot('A')}
            />
            <SlotButton
              slot="B"
              active={pickSlot === 'B'}
              sat={satB}
              accent="b"
              onPick={() => onPickSlot('B')}
              onClear={() => onClearSlot('B')}
            />
          </div>

          <p className="text-[10px] leading-relaxed text-zinc-500">
            Click globe / search to fill{' '}
            <span className={pickSlot === 'A' ? 'text-teal-300' : 'text-orange-300'}>
              slot {pickSlot}
            </span>
            , or:
          </p>

          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              disabled={!hasPrimarySelection}
              onClick={() => onUseSelectedAs('A')}
              className="athena-btn px-2 py-1 text-[10px] disabled:opacity-30"
            >
              Sel → A
            </button>
            <button
              type="button"
              disabled={!hasPrimarySelection}
              onClick={() => onUseSelectedAs('B')}
              className="athena-btn px-2 py-1 text-[10px] disabled:opacity-30"
            >
              Sel → B
            </button>
            <button type="button" onClick={onClearAll} className="athena-btn px-2 py-1 text-[10px]">
              Clear
            </button>
          </div>

          {computing && (
            <div className="text-[10px] text-amber-200/90">Computing closest approach…</div>
          )}

          {analysis && satA && satB && !computing && (
            <div className="space-y-2 border-t border-white/10 pt-2">
              <div className="text-[10px] uppercase tracking-[0.18em] text-zinc-500">
                Results
              </div>

              {analysis.temporal && (
                <ResultCard
                  title="Time-synced TCA"
                  subtitle="Min range next ~3h (same clock)"
                  primary={formatRange(analysis.temporal.rangeKm)}
                  secondary={
                    <>
                      {formatEta(analysis.temporal.tcaMs, nowMs)}
                      <span className="text-zinc-600"> · </span>
                      {new Date(analysis.temporal.tcaMs)
                        .toISOString()
                        .replace('T', ' ')
                        .slice(0, 19)}
                      Z
                    </>
                  }
                  tone={
                    analysis.temporal.rangeKm < 50
                      ? 'danger'
                      : analysis.temporal.rangeKm < 200
                        ? 'warn'
                        : 'ok'
                  }
                />
              )}

              {analysis.geometry && (
                <ResultCard
                  title="Orbit-path proximity"
                  subtitle="Closest points on the two rings"
                  primary={formatRange(analysis.geometry.rangeKm)}
                  secondary="Amber link = min path separation"
                  tone="neutral"
                />
              )}

              <div className="flex items-center gap-3 text-[9px] text-zinc-500">
                <LegendDot color="#5eead4" label="Orbit A" />
                <LegendDot color="#fb923c" label="Orbit B" />
                <LegendDot color="#fbbf24" label="TCA" />
              </div>
            </div>
          )}

          {enabled && satA && satB && !analysis && !computing && (
            <div className="text-[11px] text-rose-300/90">
              Could not propagate one or both objects (decayed TLE?).
            </div>
          )}
        </div>
      )}
    </section>
  )
}

function SlotButton({
  slot,
  active,
  sat,
  accent,
  onPick,
  onClear,
}: {
  slot: CompareSlot
  active: boolean
  sat: SatInfo | null
  accent: 'a' | 'b'
  onPick: () => void
  onClear: () => void
}) {
  const border =
    accent === 'a'
      ? active
        ? 'border-teal-400/55 bg-teal-400/10'
        : 'border-teal-400/25 bg-black/40'
      : active
        ? 'border-orange-400/55 bg-orange-400/10'
        : 'border-orange-400/25 bg-black/40'
  const label = accent === 'a' ? 'text-teal-300' : 'text-orange-300'

  return (
    <div className={`border px-2 py-2 ${border}`}>
      <div className="flex items-center justify-between gap-1">
        <button
          type="button"
          onClick={onPick}
          className={`text-[10px] font-semibold tracking-wider ${label}`}
        >
          {slot} {active ? '◀' : ''}
        </button>
        {sat && (
          <button
            type="button"
            onClick={onClear}
            className="text-[9px] text-zinc-500 hover:text-zinc-200"
          >
            ✕
          </button>
        )}
      </div>
      {sat ? (
        <div className="mt-1 min-w-0">
          <div className="truncate text-[11px] text-zinc-100">{sat.name}</div>
          <div className="text-[10px] text-zinc-500">NORAD {sat.norad}</div>
        </div>
      ) : (
        <div className="mt-1 text-[10px] text-zinc-600">empty</div>
      )}
    </div>
  )
}

function ResultCard({
  title,
  subtitle,
  primary,
  secondary,
  tone,
}: {
  title: string
  subtitle: string
  primary: string
  secondary: ReactNode
  tone: 'danger' | 'warn' | 'ok' | 'neutral'
}) {
  const primaryColor =
    tone === 'danger'
      ? 'text-rose-300'
      : tone === 'warn'
        ? 'text-amber-300'
        : tone === 'ok'
          ? 'text-emerald-300'
          : 'text-zinc-50'

  return (
    <div className="border border-white/10 bg-black/50 px-2.5 py-2">
      <div className="text-[9px] uppercase tracking-[0.16em] text-zinc-500">{title}</div>
      <div className={`mt-0.5 text-lg tabular-nums ${primaryColor}`}>{primary}</div>
      <div className="mt-0.5 text-[10px] text-zinc-400">{secondary}</div>
      <div className="mt-1 text-[9px] text-zinc-600">{subtitle}</div>
    </div>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span className="inline-block h-1.5 w-1.5" style={{ background: color }} />
      {label}
    </span>
  )
}

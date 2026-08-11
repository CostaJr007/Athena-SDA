import { useEffect, useRef, useState } from 'react'
import SidePanel from './SidePanel'
import type { SatInfo } from '@/lib/satellites'
import { UI_GROUPS, formatUtc } from '@/lib/satellites'
import type { Telemetry } from '@/lib/satellites'
import {
  bobBrief,
  boardThreat,
  formatOnsetDate,
  THREAT_STYLE,
  type BoardEntry,
} from '@/lib/risk-report'
import { countryLabel } from '@/lib/country-flag'
import CountryFlag from '@/components/hud/CountryFlag'

interface RightDockProps {
  sat: SatInfo | null
  boardEntry: BoardEntry | null
  telemetry: Telemetry | null
  showOrbit: boolean
  showFoot: boolean
  follow: boolean
  onToggleOrbit: () => void
  onToggleFoot: () => void
  onToggleFollow: () => void
  onClose: () => void
  totalTracked: number
  fps: number
  reportDay?: string | null
}

export default function RightDock({
  sat,
  boardEntry,
  telemetry,
  showOrbit,
  showFoot,
  follow,
  onToggleOrbit,
  onToggleFoot,
  onToggleFollow,
  onClose,
  totalTracked,
  fps,
  reportDay,
}: RightDockProps) {
  const [chatInput, setChatInput] = useState('')
  const [chatLog, setChatLog] = useState<
    { role: 'op' | 'bob'; text: string }[]
  >([
    {
      role: 'bob',
      text: 'Cmdr. Bob online. Select a watchlist track for a quant briefing (scores only — no invented threat).',
    },
  ])
  const [tasking, setTasking] = useState<'IDLE' | 'DRAFT' | 'VALIDATED' | 'APPROVED'>('IDLE')

  const group = sat ? UI_GROUPS[sat.group] : null
  const threat = boardEntry ? boardThreat(boardEntry) : null

  const lastBriefedRef = useRef<number | null>(null)
  useEffect(() => {
    if (!boardEntry) return
    const norad = boardEntry.norad_id
    if (lastBriefedRef.current === norad) return
    lastBriefedRef.current = norad
    const brief = bobBrief(boardEntry)
    // Defer the append so the setState is not synchronous inside the effect
    // (react-hooks/set-state-in-effect rule).
    const id = window.setTimeout(() => {
      setChatLog((prev) => {
        if (prev[prev.length - 1]?.role === 'bob' && prev[prev.length - 1].text === brief) {
          return prev
        }
        return [...prev, { role: 'bob' as const, text: brief }].slice(-12)
      })
    }, 0)
    return () => clearTimeout(id)
  }, [boardEntry])

  const sendChat = (e: React.FormEvent) => {
    e.preventDefault()
    const q = chatInput.trim()
    if (!q) return
    let reply: string
    if (boardEntry) {
      reply = bobBrief(boardEntry)
    } else if (sat) {
      reply = `Track #${sat.norad} (${sat.name}): no row in risk_report for this NORAD — orbital telemetry only. Watchlist objects carry IF/pair scores.`
    } else {
      reply =
        'No object selected. Open a priority track on the mission board or click a satellite on the globe.'
    }
    setChatLog((prev) => [...prev, { role: 'op', text: q }, { role: 'bob', text: reply }])
    setChatInput('')
  }

  return (
    <SidePanel
      side="right"
      title="Track intel"
      subtitle={
        reportDay
          ? `Telemetry · ML ${reportDay} · Bob`
          : 'Telemetry · fusion · Bob'
      }
      footer={
        <div className="flex items-center justify-between text-[13px] text-zinc-400">
          <span>{totalTracked.toLocaleString()} catalog</span>
          <span className="tabular-nums text-zinc-400">{fps} fps</span>
        </div>
      }
    >
      <div className="flex h-full min-h-[420px] flex-col gap-4">
        <section>
          <div className="mb-2 flex items-center justify-between">
            <div className="text-[13px] uppercase tracking-[0.2em] text-zinc-400">
              Selected object
            </div>
            {sat && (
              <div className="flex items-center gap-1.5">
                {boardEntry && (
                  <button
                    type="button"
                    onClick={() => {
                      const url = `${import.meta.env.BASE_URL}reports/quant_${boardEntry.norad_id}_latest.html`
                      window.open(url, '_blank', 'noopener,noreferrer')
                    }}
                    className="athena-btn athena-btn-active px-2 py-0.5 text-[12px]"
                    title="Open quant report in a new tab"
                  >
                    Quant
                  </button>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className="athena-btn px-2 py-0.5 text-[13px]"
                >
                  Clear
                </button>
              </div>
            )}
          </div>

          {!sat ? (
            <div className="border border-dashed border-white/15 bg-black/40 px-3 py-6 text-center">
              <div className="text-sm text-zinc-300">No satellite selected</div>
              <p className="mt-2 text-[14px] leading-relaxed text-zinc-400">
                Click the globe, search by NORAD, or pick a priority track.
              </p>
            </div>
          ) : (
            <div className="border border-white/12 bg-black/50 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] uppercase tracking-[0.18em] text-zinc-400">
                    {boardEntry?.role ?? group?.label ?? 'Unknown'}
                    {boardEntry?.orbit_class ? ` · ${boardEntry.orbit_class}` : ''}
                  </div>
                  {/* Flag + name (same CountryFlag as Mission board) */}
                  <div className="mt-1.5 flex min-w-0 items-center gap-2">
                    <CountryFlag
                      code={boardEntry?.country ?? null}
                      size={22}
                    />
                    <span className="min-w-0 truncate text-base font-semibold text-zinc-50">
                      {boardEntry?.object_name ?? sat.name}
                    </span>
                  </div>
                  <div className="mt-0.5 text-[14px] text-zinc-400">
                    NORAD {sat.norad}
                    {boardEntry?.country
                      ? ` · ${countryLabel(boardEntry.country)}`
                      : ''}
                  </div>
                </div>
                {threat && (
                  <span
                    className={`shrink-0 border px-1.5 py-0.5 text-[12px] tracking-wider ${THREAT_STYLE[threat].border} ${THREAT_STYLE[threat].color} ${THREAT_STYLE[threat].bg}`}
                  >
                    {threat}
                  </span>
                )}
              </div>

              {telemetry ? (
                <div className="mt-3 grid grid-cols-2 gap-1.5">
                  {(
                    [
                      ['Altitude', `${telemetry.alt.toFixed(1)} km`],
                      ['Speed', `${telemetry.speed.toFixed(2)} km/s`],
                      ['Lat', `${telemetry.lat.toFixed(2)}°`],
                      ['Lon', `${telemetry.lon.toFixed(2)}°`],
                      ['Period', `${telemetry.period.toFixed(1)} min`],
                      ['Incl', `${telemetry.incl.toFixed(2)}°`],
                    ] as const
                  ).map(([k, v]) => (
                    <div key={k} className="border border-white/10 bg-black/60 px-2 py-1.5">
                      <div className="text-[12px] uppercase tracking-wider text-zinc-400">
                        {k}
                      </div>
                      <div className="mt-0.5 text-[15px] tabular-nums text-zinc-100">
                        {v}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-3 text-sm text-zinc-400">Propagation unavailable.</div>
              )}

              {boardEntry?.anomaly_onset && (
                <div className="mt-3 border border-sky-400/25 bg-sky-500/10 px-2.5 py-2">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-sky-200/90">
                    Series noise · onset
                  </div>
                  {formatOnsetDate(boardEntry.anomaly_onset.first_elevated_at) ? (
                    <div className="mt-1 text-[14px] text-zinc-100">
                      Elevated since ~{' '}
                      <span className="font-semibold tabular-nums text-sky-100">
                        {formatOnsetDate(boardEntry.anomaly_onset.first_elevated_at)}
                      </span>
                    </div>
                  ) : (
                    <div className="mt-1 text-[13px] text-zinc-400">
                      No onset detected in scan (
                      {boardEntry.anomaly_onset.method ?? '—'})
                    </div>
                  )}
                  <div className="mt-1 text-[12px] leading-relaxed text-zinc-400">
                    Method:{' '}
                    <span className="text-zinc-300">
                      {boardEntry.anomaly_onset.method ?? '—'}
                    </span>
                    {boardEntry.anomaly_onset.sma_change_at && (
                      <>
                        {' '}
                        · SMA break ~{' '}
                        {formatOnsetDate(boardEntry.anomaly_onset.sma_change_at)}
                      </>
                    )}
                    {boardEntry.score_delta_1d != null && (
                      <>
                        {' '}
                        · Δ1d{' '}
                        {boardEntry.score_delta_1d >= 0 ? '+' : ''}
                        {boardEntry.score_delta_1d.toFixed(3)}
                      </>
                    )}
                  </div>
                  <p className="mt-1.5 text-[11px] leading-relaxed text-zinc-500">
                    {boardEntry.anomaly_onset.note ??
                      'TLE-window estimate — not a maneuver clock.'}
                  </p>
                </div>
              )}

              <div className="mt-2 text-[13px] text-zinc-500">
                TLE {sat.epochMs ? formatUtc(sat.epochMs) : 'unknown'}
              </div>

              <div className="mt-3 flex gap-1.5">
                {(
                  [
                    ['Orbit', showOrbit, onToggleOrbit],
                    ['Foot', showFoot, onToggleFoot],
                    ['Follow', follow, onToggleFollow],
                  ] as const
                ).map(([label, val, fn]) => (
                  <button
                    key={label}
                    type="button"
                    onClick={fn}
                    className={`flex-1 border px-2 py-1.5 text-[13px] tracking-wider transition-colors ${
                      val
                        ? 'border-emerald-400/45 bg-emerald-400/12 text-emerald-200'
                        : 'border-white/10 text-zinc-400 hover:bg-white/5 hover:text-zinc-200'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {boardEntry && (
                <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
                  <div className="text-[13px] uppercase tracking-[0.18em] text-zinc-400">
                    Athena quant · risk_report
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 text-[14px]">
                    <Metric k="Attention" v={boardEntry.attention_score.toFixed(3)} />
                    <Metric k="Anomaly" v={boardEntry.anomaly_score.toFixed(3)} />
                    <Metric k="Status" v={boardEntry.status} />
                    <Metric
                      k="Mil detect"
                      v={boardEntry.is_military_detection ? 'YES' : 'no'}
                    />
                    <Metric
                      k="DQ"
                      v={
                        boardEntry.data_quality.reliable
                          ? `${(boardEntry.data_quality.score * 100).toFixed(0)}%`
                          : 'UNRELIABLE'
                      }
                    />
                    <Metric
                      k="Kelly"
                      v={
                        boardEntry.kelly_allocation != null
                          ? `${(boardEntry.kelly_allocation * 100).toFixed(1)}%`
                          : '—'
                      }
                    />
                    <Metric
                      k="DFA α"
                      v={
                        boardEntry.features_snapshot.dfa_hurst_sma != null
                          ? boardEntry.features_snapshot.dfa_hurst_sma.toFixed(3)
                          : '—'
                      }
                    />
                    <Metric
                      k="Shannon H"
                      v={
                        boardEntry.features_snapshot.shannon_entropy_sma_30d != null
                          ? boardEntry.features_snapshot.shannon_entropy_sma_30d.toFixed(
                              2,
                            )
                          : '—'
                      }
                    />
                    <Metric k="Purpose" v={boardEntry.purpose || '—'} />
                    <Metric
                      k="F10.7"
                      v={
                        boardEntry.features_snapshot.f10_7 != null
                          ? String(boardEntry.features_snapshot.f10_7)
                          : '—'
                      }
                    />
                  </div>
                  {boardEntry.pair && (
                    <div className="border border-amber-400/25 bg-amber-500/10 px-2.5 py-2 text-[14px] leading-relaxed text-zinc-200">
                      <div className="text-[12px] uppercase tracking-wider text-amber-200/80">
                        Pair · {boardEntry.pair.risk_level}
                      </div>
                      <div className="mt-1">
                        vs {boardEntry.pair.asset_name} (#{boardEntry.pair.asset_norad})
                      </div>
                      <div className="mt-0.5 text-zinc-400">
                        dist {boardEntry.pair.min_distance_km.toFixed(1)} km · coint p=
                        {boardEntry.pair.cointegration_pvalue.toExponential(2)} · risk{' '}
                        {boardEntry.pair.pair_risk.toFixed(3)}
                      </div>
                    </div>
                  )}

                  {boardEntry.evidence && (
                    <div className="mt-2 border border-violet-400/25 bg-violet-500/10 px-2.5 py-2">
                      <div className="text-[12px] uppercase tracking-wider text-violet-200/80">
                        Evidential fusion · Dempster-Shafer
                      </div>
                      <div className="mt-1.5 space-y-1">
                        <EvidenceBar
                          label="Belief"
                          pct={boardEntry.evidence.belief_anomalous}
                          hex="#a78bfa"
                        />
                        <EvidenceBar
                          label="Plausibility"
                          pct={boardEntry.evidence.plausibility_anomalous}
                          hex="#c4b5fd"
                        />
                      </div>
                      <div className="mt-1 text-[12px] text-zinc-400">
                        Conflict K ={' '}
                        <span className="tabular-nums text-zinc-300">
                          {boardEntry.evidence.conflict_K?.toFixed(3) ?? '—'}
                        </span>{' '}
                        (disagreeing detectors = odd state)
                      </div>
                    </div>
                  )}

                  <div className="mt-2 border border-white/10 bg-black/40 px-2.5 py-2">
                    <div className="flex items-center justify-between">
                      <div className="text-[12px] uppercase tracking-wider text-zinc-400">
                        Sensor tasking
                      </div>
                      <span
                        className={`border px-1.5 py-0.5 text-[10px] tracking-wider ${
                          tasking === 'APPROVED'
                            ? 'border-emerald-400/50 text-emerald-200'
                            : tasking === 'VALIDATED'
                              ? 'border-sky-400/50 text-sky-200'
                              : tasking === 'DRAFT'
                                ? 'border-amber-400/50 text-amber-200'
                                : 'border-white/15 text-zinc-500'
                        }`}
                      >
                        {tasking}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        setTasking((s) =>
                          s === 'IDLE'
                            ? 'DRAFT'
                            : s === 'DRAFT'
                              ? 'VALIDATED'
                              : s === 'VALIDATED'
                                ? 'APPROVED'
                                : 'IDLE',
                        )
                      }
                      className="mt-1.5 w-full border border-emerald-400/35 bg-black/50 px-2 py-1.5 text-[12px] font-medium uppercase tracking-[0.12em] text-emerald-300 transition-colors hover:border-emerald-300/70 hover:text-emerald-100"
                      title="TaskSatellite action — $validateOnly, no execution without approval"
                    >
                      {tasking === 'IDLE'
                        ? 'Task sensor (validate)'
                        : tasking === 'DRAFT'
                          ? 'Validate order'
                          : tasking === 'VALIDATED'
                            ? 'Approve execution'
                            : 'Reset'}
                    </button>
                    <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">
                      Action <span className="text-zinc-400">TaskSatellite</span> —
                      validate-only semantics (ontology action type); never
                      executes without operator approval.
                    </p>
                  </div>
                </div>
              )}

              {sat && !boardEntry && (
                <div className="mt-3 border border-white/10 bg-black/40 px-2.5 py-2 text-[14px] text-zinc-400">
                  Not on today&apos;s watchlist board — catalog telemetry only.
                </div>
              )}
            </div>
          )}
        </section>

        <section className="flex min-h-0 flex-1 flex-col">
          <div className="mb-2 text-[13px] uppercase tracking-[0.2em] text-zinc-400">
            Bob · tactical copilot
          </div>
          <div className="flex min-h-[160px] flex-1 flex-col border border-white/12 bg-black/60">
            <div className="athena-scroll min-h-[120px] flex-1 space-y-2 overflow-y-auto p-2.5">
              {chatLog.map((m, i) => (
                <div
                  key={i}
                  className={`px-2.5 py-2 text-[14px] leading-relaxed ${
                    m.role === 'bob'
                      ? 'border border-emerald-400/25 bg-emerald-400/10 text-zinc-100'
                      : 'border border-white/10 bg-white/[0.03] text-zinc-300'
                  }`}
                >
                  <div className="mb-0.5 text-[12px] uppercase tracking-wider text-zinc-400">
                    {m.role === 'bob' ? 'BOB' : 'CMDR'}
                  </div>
                  {m.text}
                </div>
              ))}
            </div>
            <form
              onSubmit={sendChat}
              className="flex gap-1.5 border-t border-white/10 p-2"
            >
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask Bob about this track…"
                className="athena-input min-w-0 flex-1 px-2.5 py-1.5 text-[14px]"
              />
              <button
                type="submit"
                className="athena-btn athena-btn-active px-2.5 py-1.5 text-[13px]"
              >
                Send
              </button>
            </form>
          </div>
          <p className="mt-1.5 text-[12px] text-zinc-500">
            Local quant brief · watsonx optional later
          </p>
        </section>
      </div>
    </SidePanel>
  )
}

function Metric({ k, v }: { k: string; v: string }) {
  return (
    <div className="border border-white/10 bg-black/50 px-2 py-1.5">
      <div className="text-[12px] uppercase tracking-wider text-zinc-400">{k}</div>
      <div className="mt-0.5 truncate text-zinc-100">{v}</div>
    </div>
  )
}

function EvidenceBar({ label, pct, hex }: { label: string; pct?: number; hex: string }) {
  const p = pct == null ? 0 : Math.max(0, Math.min(1, pct))
  return (
    <div className="flex items-center gap-2 text-[12px] text-zinc-400">
      <span className="w-20 shrink-0 uppercase tracking-wider">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden bg-black/70">
        <div className="h-full" style={{ width: `${p * 100}%`, background: hex }} />
      </div>
      <span className="w-12 shrink-0 text-right tabular-nums text-zinc-300">
        {p.toFixed(2)}
      </span>
    </div>
  )
}

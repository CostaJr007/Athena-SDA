import { useState } from 'react'
import SidePanel from './SidePanel'
import type { SatInfo } from '@/lib/satellites'
import { UI_GROUPS, formatUtc } from '@/lib/satellites'
import type { Telemetry } from '@/components/hud/DetailPanel'
import { getTrack, type Threat } from '@/lib/athena-tracks'

const THREAT_COLOR: Record<Threat, string> = {
  HOSTILE: 'text-rose-300 border-rose-400/40 bg-rose-500/10',
  SUSPECT: 'text-amber-300 border-amber-400/40 bg-amber-500/10',
  ANOMALY: 'text-orange-300 border-orange-400/40 bg-orange-500/10',
  NOMINAL: 'text-emerald-300 border-emerald-400/40 bg-emerald-500/10',
}

interface RightDockProps {
  sat: SatInfo | null
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
}

export default function RightDock({
  sat,
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
}: RightDockProps) {
  const [chatInput, setChatInput] = useState('')
  const [chatLog, setChatLog] = useState<
    { role: 'op' | 'bob'; text: string }[]
  >([
    {
      role: 'bob',
      text: 'Cmdr. Bob online. Select a track or ask about active hostiles.',
    },
  ])

  const athena = sat ? getTrack(String(sat.norad)) : null
  const group = sat ? UI_GROUPS[sat.group] : null

  const sendChat = (e: React.FormEvent) => {
    e.preventDefault()
    const q = chatInput.trim()
    if (!q) return
    setChatLog((prev) => [
      ...prev,
      { role: 'op', text: q },
      {
        role: 'bob',
        text: sat
          ? `Track #${sat.norad} (${sat.name}): ${
              athena
                ? `${athena.threat} · conf ${(athena.conf * 100).toFixed(0)}% · H=${athena.ent.toFixed(2)}. ${athena.notes.slice(0, 120)}…`
                : 'No Athena fusion score yet — orbital telemetry only.'
            }`
          : 'No object selected. Open a priority track or click a satellite on the globe.',
      },
    ])
    setChatInput('')
  }

  return (
    <SidePanel
      side="right"
      title="Track intel"
      subtitle="Telemetry · fusion · Bob"
      footer={
        <div className="flex items-center justify-between text-[10px] text-zinc-500">
          <span>{totalTracked.toLocaleString()} catalog</span>
          <span className="tabular-nums text-zinc-400">{fps} fps</span>
        </div>
      }
    >
      <div className="flex h-full min-h-[420px] flex-col gap-4">
        <section>
          <div className="mb-2 flex items-center justify-between">
            <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500">
              Selected object
            </div>
            {sat && (
              <button
                type="button"
                onClick={onClose}
                className="athena-btn px-2 py-0.5 text-[10px]"
              >
                Clear
              </button>
            )}
          </div>

          {!sat ? (
            <div className="border border-dashed border-white/15 bg-black/40 px-3 py-6 text-center">
              <div className="text-xs text-zinc-300">No satellite selected</div>
              <p className="mt-2 text-[11px] leading-relaxed text-zinc-500">
                Click the globe, search by NORAD, or pick a priority track.
              </p>
            </div>
          ) : (
            <div className="border border-white/12 bg-black/50 p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div
                    className="text-[10px] uppercase tracking-[0.18em] text-zinc-400"
                  >
                    {group?.label ?? 'Unknown'}
                  </div>
                  <div className="mt-1 truncate text-sm font-semibold text-zinc-50">
                    {sat.name}
                  </div>
                  <div className="mt-0.5 text-[11px] text-zinc-500">
                    NORAD {sat.norad}
                  </div>
                </div>
                {athena && (
                  <span
                    className={`shrink-0 border px-1.5 py-0.5 text-[9px] tracking-wider ${THREAT_COLOR[athena.threat]}`}
                  >
                    {athena.threat}
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
                      <div className="text-[9px] uppercase tracking-wider text-zinc-500">
                        {k}
                      </div>
                      <div className="mt-0.5 text-[12px] tabular-nums text-zinc-100">
                        {v}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-3 text-xs text-zinc-500">Propagation unavailable.</div>
              )}

              <div className="mt-2 text-[10px] text-zinc-600">
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
                    className={`flex-1 border px-2 py-1.5 text-[10px] tracking-wider transition-colors ${
                      val
                        ? 'border-emerald-400/45 bg-emerald-400/12 text-emerald-200'
                        : 'border-white/10 text-zinc-500 hover:bg-white/5 hover:text-zinc-200'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {athena && (
                <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-zinc-500">
                    Athena fusion
                  </div>
                  <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                    <Metric k="Entropy H" v={athena.ent.toFixed(2)} />
                    <Metric k="Conf" v={`${(athena.conf * 100).toFixed(0)}%`} />
                    <Metric k="Country" v={athena.country} />
                    <Metric k="Purpose" v={athena.purpose} />
                  </div>
                  <p className="text-[11px] leading-relaxed text-zinc-400">
                    {athena.notes}
                  </p>
                </div>
              )}
            </div>
          )}
        </section>

        <section className="flex min-h-0 flex-1 flex-col">
          <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-zinc-500">
            Bob · tactical copilot
          </div>
          <div className="flex min-h-[160px] flex-1 flex-col border border-white/12 bg-black/60">
            <div className="athena-scroll min-h-0 flex-1 space-y-2 overflow-y-auto p-2.5">
              {chatLog.map((m, i) => (
                <div
                  key={i}
                  className={`px-2.5 py-2 text-[11px] leading-relaxed ${
                    m.role === 'bob'
                      ? 'border border-emerald-400/25 bg-emerald-400/10 text-zinc-100'
                      : 'border border-white/10 bg-white/[0.03] text-zinc-300'
                  }`}
                >
                  <div className="mb-0.5 text-[9px] uppercase tracking-wider text-zinc-500">
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
                className="athena-input min-w-0 flex-1 px-2.5 py-1.5 text-[11px]"
              />
              <button type="submit" className="athena-btn athena-btn-active px-2.5 py-1.5 text-[10px]">
                Send
              </button>
            </form>
          </div>
          <p className="mt-1.5 text-[9px] text-zinc-600">
            Stub replies · connect watsonx / Bob backend next
          </p>
        </section>
      </div>
    </SidePanel>
  )
}

function Metric({ k, v }: { k: string; v: string }) {
  return (
    <div className="border border-white/10 bg-black/50 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wider text-zinc-500">{k}</div>
      <div className="mt-0.5 truncate text-zinc-100">{v}</div>
    </div>
  )
}

/**
 * EventReplayPanel — temporal replay of a walk-forward event curve.
 *
 * Palantir US 12,450,265 B2 (time-related geospatial data): the per-event
 * anomaly_score(t) series is a "temporal tile" — scrub along the timeline
 * with a slider while the public event anchor (t_peak) and the hit/lead
 * metrics stay annotated. Data comes from public/data/walkforward/wf_*.json
 * (synced by scripts/sync_frontend_data.sh|.ps1).
 */
import { useEffect, useMemo, useState } from 'react'

interface WfFold {
  asof: string
  targets: Record<string, { ok?: boolean; anomaly_score?: number }>
}

interface WfEvent {
  event_id: string
  t_start?: string
  t_peak?: string
  t_end?: string
  norad_ids?: number[]
  sources?: string[]
  folds?: WfFold[]
  metrics?: Record<string, { hit?: boolean; lead_time_days?: number | null; max_score?: number }>
}

interface EventReplayPanelProps {
  eventId: string
  threshold?: number
}

export default function EventReplayPanel({ eventId, threshold = 0.5 }: EventReplayPanelProps) {
  const [data, setData] = useState<WfEvent | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [cursor, setCursor] = useState(0)

  useEffect(() => {
    let cancelled = false
    // Reset state deferred (react-hooks/set-state-in-effect): no synchronous
    // setState inside the effect body.
    const boot = window.setTimeout(() => {
      if (cancelled) return
      setData(null)
      setError(null)
      setCursor(0)
    }, 0)
    const url = `${import.meta.env.BASE_URL}data/walkforward/wf_${eventId}.json`
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json() as Promise<WfEvent>
      })
      .then((d) => {
        if (cancelled) return
        setData(d)
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      })
    return () => {
      cancelled = true
      clearTimeout(boot)
    }
  }, [eventId])

  const series = useMemo(() => {
    if (!data?.folds?.length) return []
    const norad = data.norad_ids?.[0] ?? Object.keys(data.folds[0]?.targets ?? {})[0]
    if (!norad) return []
    return data.folds
      .map((f) => ({
        asof: f.asof,
        score: f.targets[norad]?.anomaly_score ?? null,
      }))
      .filter((p) => p.score != null) as Array<{ asof: string; score: number }>
  }, [data])

  const norad = data?.norad_ids?.[0]
  const metrics = norad != null ? data?.metrics?.[String(norad)] : null
  const idx = Math.min(cursor, Math.max(0, series.length - 1))
  const current = series[idx] ?? null

  // SVG chart geometry (viewBox 0 0 600 170)
  const W = 600
  const H = 170
  const PAD = { l: 34, r: 8, t: 10, b: 22 }
  const iw = W - PAD.l - PAD.r
  const ih = H - PAD.t - PAD.b
  const xAt = (i: number) =>
    series.length > 1 ? PAD.l + (i / (series.length - 1)) * iw : PAD.l + iw / 2
  const yAt = (s: number) => PAD.t + ih - Math.min(Math.max(s, 0), 1) * ih
  const tPeakX = data?.t_peak ? xAt(series.findIndex((p) => p.asof.slice(0, 10) >= data.t_peak!.slice(0, 10))) : null

  const points = series.map((p, i) => `${xAt(i).toFixed(1)},${yAt(p.score).toFixed(1)}`).join(' ')
  const area =
    series.length > 1
      ? `${PAD.l},${PAD.t + ih} ${points} ${xAt(series.length - 1).toFixed(1)},${PAD.t + ih}`
      : ''

  return (
    <div className="border border-white/12 bg-black/50 p-2.5">
      <div className="flex items-center justify-between">
        <div className="text-[12px] uppercase tracking-[0.16em] text-zinc-400">
          Event replay · {eventId}
        </div>
        {metrics && (
          <div className="flex gap-1">
            {metrics.hit ? (
              <span className="border border-emerald-400/50 bg-emerald-400/10 px-1.5 py-0.5 text-[10px] tracking-wider text-emerald-200">
                HIT
              </span>
            ) : (
              <span className="border border-rose-400/40 bg-rose-500/10 px-1.5 py-0.5 text-[10px] tracking-wider text-rose-200">
                MISS
              </span>
            )}
            {metrics.lead_time_days != null && (
              <span className="border border-sky-400/40 bg-sky-500/10 px-1.5 py-0.5 text-[10px] tracking-wider text-sky-200">
                lead {metrics.lead_time_days.toFixed(0)}d
              </span>
            )}
            {metrics.max_score != null && (
              <span className="border border-white/15 px-1.5 py-0.5 text-[10px] tracking-wider text-zinc-300">
                max {metrics.max_score.toFixed(2)}
              </span>
            )}
          </div>
        )}
      </div>

      {error ? (
        <p className="mt-2 text-[13px] text-rose-300">
          replay unavailable: {error} — run walk-forward + sync, or the event
          file is missing.
        </p>
      ) : !data ? (
        <p className="mt-2 text-[13px] text-zinc-400">loading {eventId}…</p>
      ) : series.length < 2 ? (
        <p className="mt-2 text-[13px] text-zinc-400">no score series for this event.</p>
      ) : (
        <>
          <svg
            viewBox={`0 0 ${W} ${H}`}
            className="mt-2 h-auto w-full"
            role="img"
            aria-label={`anomaly score curve for ${eventId}`}
          >
            {/* threshold */}
            <line
              x1={PAD.l}
              x2={W - PAD.r}
              y1={yAt(threshold)}
              y2={yAt(threshold)}
              stroke="#fbbf24"
              strokeDasharray="3 3"
              strokeWidth={1}
              opacity={0.7}
            />
            {/* t_peak anchor */}
            {tPeakX != null && (
              <line
                x1={tPeakX}
                x2={tPeakX}
                y1={PAD.t}
                y2={PAD.t + ih}
                stroke="#fb7185"
                strokeDasharray="5 3"
                strokeWidth={1}
              />
            )}
            {/* area + curve */}
            {series.length > 1 && <polygon points={area} fill="rgba(52,211,153,0.10)" />}
            <polyline
              points={points}
              fill="none"
              stroke="#34d399"
              strokeWidth={1.5}
              strokeLinejoin="round"
            />
            {/* cursor */}
            <line
              x1={xAt(idx)}
              x2={xAt(idx)}
              y1={PAD.t}
              y2={PAD.t + ih}
              stroke="#fafafa"
              strokeWidth={1.2}
            />
            <circle cx={xAt(idx)} cy={yAt(current?.score ?? 0)} r={3} fill="#fafafa" />
            {/* labels */}
            <text x={PAD.l} y={PAD.t - 2} fill="#a1a1aa" fontSize={9}>
              score
            </text>
            {tPeakX != null && (
              <text x={tPeakX + 4} y={PAD.t + 8} fill="#fb7185" fontSize={9}>
                t_peak
              </text>
            )}
          </svg>
          <input
            type="range"
            min={0}
            max={Math.max(0, series.length - 1)}
            value={idx}
            onChange={(e) => setCursor(Number(e.target.value))}
            className="mt-1 w-full"
            aria-label="timeline scrubber"
          />
          <div className="mt-1 flex items-center justify-between text-[12px] tabular-nums text-zinc-400">
            <span>{series[0]?.asof.slice(0, 10)}</span>
            <span className="text-zinc-200">
              {current?.asof.slice(0, 10)} · score {current?.score.toFixed(3)}
            </span>
            <span>{series[series.length - 1]?.asof.slice(0, 10)}</span>
          </div>
          {data.t_peak && (
            <p className="mt-1.5 text-[12px] text-zinc-500">
              Public anchor <span className="text-zinc-300">t_peak {data.t_peak.slice(0, 10)}</span>
              {data.t_start ? ` · window ${data.t_start.slice(0, 10)}` : ''}
              {data.t_end ? ` → ${data.t_end.slice(0, 10)}` : ''}
            </p>
          )}
          {data.sources && data.sources.length > 0 && (
            <ul className="mt-1.5 space-y-0.5">
              {data.sources.slice(0, 3).map((s, i) => (
                <li key={i} className="text-[11px] leading-relaxed text-zinc-500">
                  · {s}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  )
}

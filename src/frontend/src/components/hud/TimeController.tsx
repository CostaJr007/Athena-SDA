import type { SimClock } from '@/hooks/useSimClock'

const SPEEDS = [-240, -60, -10, 10, 60, 240]

interface TimeControllerProps {
  clock: SimClock
}

export default function TimeController({ clock }: TimeControllerProps) {
  const live = clock.playing && clock.speed === 1
  return (
    <div className="athena-panel pointer-events-auto flex w-max max-w-full items-center gap-0.5 overflow-hidden p-1">
      {SPEEDS.map((s) => {
        const active = clock.playing && clock.speed === s
        return (
          <button
            key={s}
            onClick={() => clock.setSpeed(s)}
            className={`shrink-0 px-2 py-1.5 text-[11px] tabular-nums transition-colors ${
              active
                ? 'bg-emerald-400/20 text-emerald-200'
                : 'text-zinc-500 hover:bg-white/5 hover:text-zinc-200'
            }`}
          >
            {s > 0 ? `+${s}×` : `${s}×`}
          </button>
        )
      })}
      <button
        onClick={() => (clock.playing ? clock.pause() : clock.resume())}
        title={clock.playing ? 'Pause' : 'Resume'}
        className="ml-0.5 flex h-7 w-7 shrink-0 items-center justify-center text-zinc-300 hover:bg-white/5"
      >
        {clock.playing ? (
          <svg viewBox="0 0 12 12" className="h-3 w-3 fill-current">
            <rect x="1.5" y="1" width="3.2" height="10" rx="0.6" />
            <rect x="7.3" y="1" width="3.2" height="10" rx="0.6" />
          </svg>
        ) : (
          <svg viewBox="0 0 12 12" className="h-3 w-3 fill-current">
            <path d="M3 1.4v9.2c0 .8.9 1.3 1.6.9l7-4.6c.6-.4.6-1.4 0-1.8l-7-4.6c-.7-.4-1.6.1-1.6.9z" />
          </svg>
        )}
      </button>
      <button
        onClick={() => clock.goNow()}
        className={`ml-0.5 flex shrink-0 items-center gap-1.5 px-2.5 py-1.5 text-[11px] tracking-wider transition-colors ${
          live
            ? 'bg-emerald-400 text-black'
            : 'border border-emerald-400/40 text-emerald-300 hover:bg-emerald-400/10'
        }`}
      >
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${
            live ? 'bg-black' : 'bg-emerald-400'
          }`}
        />
        LIVE
      </button>
    </div>
  )
}

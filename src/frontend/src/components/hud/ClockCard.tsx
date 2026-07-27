import { useEffect, useState } from 'react'
import type { SimClock } from '@/hooks/useSimClock'
import { formatClockDate, formatClockTime } from '@/lib/satellites'

interface ClockCardProps {
  clock: SimClock
}

export default function ClockCard({ clock }: ClockCardProps) {
  const [tick, setTick] = useState({ sim: 0, wall: 0 })

  useEffect(() => {
    const id = setInterval(() => setTick({ sim: clock.getTime(), wall: Date.now() }), 200)
    return () => clearInterval(id)
  }, [clock])

  const now = tick.sim
  const live =
    clock.playing && clock.speed === 1 && now > 0 && Math.abs(now - tick.wall) < 2500

  return (
    <div className="athena-panel pointer-events-auto flex items-center gap-3 px-3.5 py-2.5 md:gap-4 md:px-4">
      <div>
        <div className="text-[12px] uppercase tracking-[0.14em] text-zinc-400">Sim UTC</div>
        <div className="text-xl font-medium tabular-nums tracking-wider text-zinc-50 md:text-2xl">
          {now > 0 ? formatClockTime(now) : '--:--:--'}
        </div>
      </div>
      <div className="h-9 w-px bg-white/10" />
      <div className="text-right">
        <div className="text-[14px] tracking-wide text-zinc-300">
          {now > 0 ? formatClockDate(now) : ''}
        </div>
        {!clock.playing ? (
          <div className="mt-0.5 text-[13px] tracking-wider text-zinc-400">PAUSED</div>
        ) : live ? (
          <div className="mt-0.5 flex items-center justify-end gap-1.5 text-[13px] tracking-wider text-emerald-400">
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_6px_#34d399]" />
            LIVE FEED
          </div>
        ) : (
          <div className="mt-0.5 flex items-center justify-end gap-1.5 text-[13px] tracking-wider text-amber-300">
            <span className="inline-block h-2 w-2 rounded-full bg-amber-400" />
            {clock.speed > 0 ? '+' : ''}
            {clock.speed}× WARP
          </div>
        )}
      </div>
    </div>
  )
}

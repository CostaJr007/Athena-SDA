interface IdentityBlockProps {
  total: number
  /** ML risk_report day when available */
  mlDay?: string | null
  watchlistN?: number | null
}

export default function IdentityBlock({
  total,
  mlDay = null,
  watchlistN = null,
}: IdentityBlockProps) {
  return (
    <div className="athena-panel pointer-events-none select-none px-3 py-2">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center border border-emerald-400/50 bg-black text-[10px] font-bold text-emerald-400">
          A
        </div>
        <div>
          <h1 className="text-sm font-semibold tracking-[0.18em] text-zinc-50 md:text-base">
            ATHENA<span className="text-emerald-400">-SDA</span>
          </h1>
          <p className="mt-0.5 text-[9px] uppercase tracking-[0.14em] text-zinc-500 md:text-[10px]">
            Space Domain Awareness
          </p>
        </div>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-0.5 border-t border-white/10 pt-1.5 text-[9px] uppercase tracking-wider text-zinc-500">
        <span className="text-emerald-400/90">● LIVE</span>
        <span className="text-zinc-600">|</span>
        <span className="tabular-nums text-zinc-300">
          {total.toLocaleString()} objects
        </span>
        {watchlistN != null && (
          <>
            <span className="text-zinc-600">|</span>
            <span className="text-amber-200/90">{watchlistN} watchlist</span>
          </>
        )}
        {mlDay && (
          <>
            <span className="text-zinc-600">|</span>
            <span className="text-sky-300/90">ML {mlDay}</span>
          </>
        )}
        <span className="hidden text-zinc-600 md:inline">|</span>
        <span className="hidden text-zinc-500 md:inline">CelesTrak · SGP4 · IF</span>
      </div>
    </div>
  )
}

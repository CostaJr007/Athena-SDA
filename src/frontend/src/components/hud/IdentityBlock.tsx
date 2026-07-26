interface IdentityBlockProps {
  total: number
}

export default function IdentityBlock({ total }: IdentityBlockProps) {
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
      <div className="mt-2 flex items-center gap-2 border-t border-white/10 pt-1.5 text-[9px] uppercase tracking-wider text-zinc-500">
        <span className="text-emerald-400/90">● LIVE</span>
        <span className="text-zinc-600">|</span>
        <span className="tabular-nums text-zinc-300">
          {total.toLocaleString()} objects
        </span>
        <span className="hidden text-zinc-600 md:inline">|</span>
        <span className="hidden text-zinc-500 md:inline">CelesTrak · SGP4</span>
      </div>
    </div>
  )
}

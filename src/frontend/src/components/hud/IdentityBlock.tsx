import type { PaperClaims } from '@/hooks/usePaperValidation'

interface IdentityBlockProps {
  total: number
  /** ML risk_report day when available */
  mlDay?: string | null
  watchlistN?: number | null
  claims?: PaperClaims | null
  onOpenProof?: () => void
}

export default function IdentityBlock({
  total,
  mlDay = null,
  watchlistN = null,
  claims = null,
  onOpenProof,
}: IdentityBlockProps) {
  const p =
    claims?.pValue == null
      ? null
      : claims.pValue < 0.001
        ? 'p<0.001'
        : `p≈${claims.pValue.toFixed(3)}`

  return (
    <div className="athena-panel select-none px-3.5 py-2">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center border border-emerald-400/50 bg-black text-[14px] font-bold text-emerald-400">
          A
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-[0.12em] text-zinc-50 md:text-xl">
            ATHENA<span className="text-emerald-400">-SDA</span>
          </h1>
          <p className="mt-0.5 text-[12px] uppercase tracking-[0.1em] text-zinc-400">
            Space Domain Awareness
          </p>
        </div>
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 border-t border-white/10 pt-1.5 text-[12px] uppercase tracking-wider text-zinc-400">
        <span className="text-emerald-400/90">● LIVE</span>
        <span className="text-zinc-500">|</span>
        <span className="tabular-nums text-zinc-200">
          {total.toLocaleString()} objects
        </span>
        {watchlistN != null && (
          <>
            <span className="text-zinc-500">|</span>
            <span className="text-amber-200/90">{watchlistN} watchlist</span>
          </>
        )}
        {mlDay && (
          <>
            <span className="text-zinc-500">|</span>
            <span className="text-sky-300/90">ML {mlDay}</span>
          </>
        )}
      </div>
      {claims && (
        <button
          type="button"
          onClick={onOpenProof}
          title="Open walk-forward proof (Claims A+B)"
          className="pointer-events-auto mt-1.5 flex w-full flex-wrap items-baseline gap-x-2 border border-emerald-400/25 bg-emerald-500/5 px-2 py-1 text-left"
        >
          <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-300/90">
            Unique A+B
          </span>
          <span className="text-[12px] tabular-nums text-emerald-100">
            GEO {claims.geoHits}
          </span>
          <span className="text-[12px] tabular-nums text-zinc-300">
            EO {claims.eoHits}
          </span>
          {p && <span className="text-[11px] text-zinc-500">{p}</span>}
        </button>
      )}
    </div>
  )
}

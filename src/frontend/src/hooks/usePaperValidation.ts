import { useEffect, useState } from 'react'

export interface PaperClaims {
  geoHits: string
  eoHits: string
  geoMeanMax: number
  eoMeanMax: number
  pValue: number | null
  supported: boolean
  dayHint: string
}

/** Headline fallback matches README / paper (re-validated 2026-08). */
const FALLBACK: PaperClaims = {
  geoHits: '5/5',
  eoHits: '0/7',
  geoMeanMax: 0.716,
  eoMeanMax: 0.457,
  pValue: 0.0013,
  supported: true,
  dayHint: 'static',
}

interface PaperFile {
  generated_at?: string
  claim_A_geo_headline?: {
    n_events?: number
    hard_hit_rate?: number
    mean_max_score?: number
    supported?: boolean
  }
  claim_B?: {
    n_events?: number
    hard_hit_rate?: number
    mean_max_score?: number
    supported?: boolean
  }
  claim_B_geo_headline?: {
    n_events?: number
    hard_hit_rate?: number
    mean_max_score?: number
  }
  separation?: {
    mann_whitney_max_scores?: { p_value?: number }
  }
  separation_geo_headline?: {
    mann_whitney_max_scores?: { p_value?: number }
  }
}

function frac(nEvents: number, rate: number): string {
  const hits = Math.round(nEvents * rate)
  return `${hits}/${nEvents}`
}

export function usePaperValidation(): PaperClaims {
  const [claims, setClaims] = useState<PaperClaims>(FALLBACK)

  useEffect(() => {
    const ctrl = new AbortController()
    const url = `${import.meta.env.BASE_URL}data/paper_validation_latest.json`
    void (async () => {
      try {
        const res = await fetch(url, { signal: ctrl.signal })
        if (!res.ok) return
        const data = (await res.json()) as PaperFile
        if (ctrl.signal.aborted) return
        const geo = data.claim_A_geo_headline
        const eo = data.claim_B_geo_headline ?? data.claim_B
        setClaims({
          geoHits:
            geo?.n_events != null && geo.hard_hit_rate != null
              ? frac(geo.n_events, geo.hard_hit_rate)
              : FALLBACK.geoHits,
          eoHits:
            eo?.n_events != null && eo.hard_hit_rate != null
              ? frac(eo.n_events, eo.hard_hit_rate)
              : FALLBACK.eoHits,
          geoMeanMax: geo?.mean_max_score ?? FALLBACK.geoMeanMax,
          eoMeanMax: eo?.mean_max_score ?? FALLBACK.eoMeanMax,
          pValue:
            data.separation_geo_headline?.mann_whitney_max_scores?.p_value ??
            data.separation?.mann_whitney_max_scores?.p_value ??
            FALLBACK.pValue,
          supported: geo?.supported !== false && (data.claim_B?.supported ?? true),
          dayHint: data.generated_at?.slice(0, 10) ?? 'live',
        })
      } catch {
        /* keep fallback */
      }
    })()
    return () => ctrl.abort()
  }, [])

  return claims
}

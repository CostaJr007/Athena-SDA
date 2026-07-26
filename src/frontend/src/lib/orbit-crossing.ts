/**
 * Dual-orbit geometry helpers for route-cross visualization.
 * Units: SGP4 ECI km → scene unit-Earth (divide by EARTH_R).
 */
import * as satellite from 'satellite.js'

export const EARTH_R_KM = 6371

export interface Vec3 {
  x: number
  y: number
  z: number
}

export interface ClosestGeometry {
  /** Minimum 3D separation between the two closed orbit rings (km). */
  rangeKm: number
  pointA: Vec3
  pointB: Vec3
  /** Midpoint between A and B (scene units, for markers). */
  mid: Vec3
}

export interface TemporalClosest {
  /** Epoch of closest approach in the search window. */
  tcaMs: number
  rangeKm: number
  pointA: Vec3
  pointB: Vec3
  mid: Vec3
}

export interface CrossAnalysis {
  geometry: ClosestGeometry | null
  temporal: TemporalClosest | null
  /** Full closed rings in scene units (xyz interleaved, includes closing vertex). */
  ringA: Float32Array
  ringB: Float32Array
}

function eciFromPv(
  pv: satellite.EciVec3<number> | false | undefined,
): Vec3 | null {
  if (!pv || !isFinite(pv.x)) return null
  return { x: pv.x, y: pv.y, z: pv.z }
}

function toScene(v: Vec3): Vec3 {
  return {
    x: v.x / EARTH_R_KM,
    y: v.y / EARTH_R_KM,
    z: v.z / EARTH_R_KM,
  }
}

function distKm(a: Vec3, b: Vec3): number {
  const dx = a.x - b.x
  const dy = a.y - b.y
  const dz = a.z - b.z
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
}

function midScene(a: Vec3, b: Vec3): Vec3 {
  const sa = toScene(a)
  const sb = toScene(b)
  return {
    x: (sa.x + sb.x) * 0.5,
    y: (sa.y + sb.y) * 0.5,
    z: (sa.z + sb.z) * 0.5,
  }
}

/** Sample one full orbital period as a closed ring (scene units). */
export function sampleOrbitRing(
  rec: satellite.SatRec,
  epochMs: number,
  samples = 128,
): Float32Array | null {
  const meanMotion = rec.no // rad/min
  if (!meanMotion || !isFinite(meanMotion) || meanMotion <= 0) return null
  const periodMs = ((2 * Math.PI) / meanMotion) * 60 * 1000
  const n = samples
  const out = new Float32Array((n + 1) * 3)
  let last: Vec3 | null = null
  for (let i = 0; i <= n; i++) {
    const t = epochMs + (periodMs * i) / n
    try {
      const pv = satellite.propagate(rec, new Date(t))
      const p = eciFromPv(pv?.position as satellite.EciVec3<number> | false)
      if (p) last = p
    } catch {
      /* keep last */
    }
    if (!last) return null
    const s = toScene(last)
    out[i * 3] = s.x
    out[i * 3 + 1] = s.y
    out[i * 3 + 2] = s.z
  }
  return out
}

/** Closest points between two sampled rings (geometry of paths, not time-synced). */
export function closestOnRings(
  ringA: Float32Array,
  ringB: Float32Array,
): ClosestGeometry | null {
  const nA = Math.floor(ringA.length / 3) - 1 // exclude closing dup for search
  const nB = Math.floor(ringB.length / 3) - 1
  if (nA < 4 || nB < 4) return null

  let best = Infinity
  let ia = 0
  let ib = 0
  for (let i = 0; i < nA; i++) {
    const ax = ringA[i * 3] * EARTH_R_KM
    const ay = ringA[i * 3 + 1] * EARTH_R_KM
    const az = ringA[i * 3 + 2] * EARTH_R_KM
    for (let j = 0; j < nB; j++) {
      const bx = ringB[j * 3] * EARTH_R_KM
      const by = ringB[j * 3 + 1] * EARTH_R_KM
      const bz = ringB[j * 3 + 2] * EARTH_R_KM
      const dx = ax - bx
      const dy = ay - by
      const dz = az - bz
      const d = Math.sqrt(dx * dx + dy * dy + dz * dz)
      if (d < best) {
        best = d
        ia = i
        ib = j
      }
    }
  }

  const pointA = {
    x: ringA[ia * 3] * EARTH_R_KM,
    y: ringA[ia * 3 + 1] * EARTH_R_KM,
    z: ringA[ia * 3 + 2] * EARTH_R_KM,
  }
  const pointB = {
    x: ringB[ib * 3] * EARTH_R_KM,
    y: ringB[ib * 3 + 1] * EARTH_R_KM,
    z: ringB[ib * 3 + 2] * EARTH_R_KM,
  }
  return {
    rangeKm: best,
    pointA,
    pointB,
    mid: midScene(pointA, pointB),
  }
}

/**
 * Time-synced closest approach over a window (TCA-style).
 * Default: next 3 hours @ 20s steps (~540 samples — fine on main thread).
 */
export function findTemporalClosest(
  recA: satellite.SatRec,
  recB: satellite.SatRec,
  startMs: number,
  durationMs = 3 * 3600 * 1000,
  stepMs = 20_000,
): TemporalClosest | null {
  let best = Infinity
  let tBest = startMs
  let paBest: Vec3 | null = null
  let pbBest: Vec3 | null = null

  const end = startMs + durationMs
  for (let t = startMs; t <= end; t += stepMs) {
    try {
      const a = eciFromPv(
        satellite.propagate(recA, new Date(t))?.position as
          | satellite.EciVec3<number>
          | false,
      )
      const b = eciFromPv(
        satellite.propagate(recB, new Date(t))?.position as
          | satellite.EciVec3<number>
          | false,
      )
      if (!a || !b) continue
      const d = distKm(a, b)
      if (d < best) {
        best = d
        tBest = t
        paBest = a
        pbBest = b
      }
    } catch {
      /* skip */
    }
  }

  if (!paBest || !pbBest || !isFinite(best)) return null
  return {
    tcaMs: tBest,
    rangeKm: best,
    pointA: paBest,
    pointB: pbBest,
    mid: midScene(paBest, pbBest),
  }
}

/** Full analysis for UI + engine. */
export function analyzeOrbitCross(
  recA: satellite.SatRec,
  recB: satellite.SatRec,
  epochMs: number,
): CrossAnalysis | null {
  const ringA = sampleOrbitRing(recA, epochMs, 120)
  const ringB = sampleOrbitRing(recB, epochMs, 120)
  if (!ringA || !ringB) return null
  return {
    ringA,
    ringB,
    geometry: closestOnRings(ringA, ringB),
    temporal: findTemporalClosest(recA, recB, epochMs),
  }
}

export function formatRange(km: number): string {
  if (km < 1) return `${(km * 1000).toFixed(0)} m`
  if (km < 100) return `${km.toFixed(2)} km`
  return `${km.toFixed(1)} km`
}

export function formatEta(tcaMs: number, nowMs: number): string {
  const dt = tcaMs - nowMs
  const abs = Math.abs(dt)
  const sign = dt < 0 ? '−' : '+'
  const h = Math.floor(abs / 3_600_000)
  const m = Math.floor((abs % 3_600_000) / 60_000)
  const s = Math.floor((abs % 60_000) / 1000)
  if (h > 0) return `T${sign}${h}h ${m.toString().padStart(2, '0')}m`
  if (m > 0) return `T${sign}${m}m ${s.toString().padStart(2, '0')}s`
  return `T${sign}${s}s`
}

/**
 * Ramer-Douglas-Peucker polyline simplification.
 *
 * Palantir US 12,450,265 B2 (time-related geospatial data): trajectory
 * compression keeps the payload constant across zoom/temporal levels. Here
 * it reduces the per-satellite orbit ring points (SGP4 propagation cost on
 * the main thread) while preserving the shape.
 */

export interface RdpPoint {
  x: number
  y: number
  z: number
}

function perpDistance(p: RdpPoint, a: RdpPoint, b: RdpPoint): number {
  const abx = b.x - a.x
  const aby = b.y - a.y
  const abz = b.z - a.z
  const lenSq = abx * abx + aby * aby + abz * abz
  if (lenSq === 0) {
    const dx = p.x - a.x
    const dy = p.y - a.y
    const dz = p.z - a.z
    return Math.sqrt(dx * dx + dy * dy + dz * dz)
  }
  const t = ((p.x - a.x) * abx + (p.y - a.y) * aby + (p.z - a.z) * abz) / lenSq
  const cx = a.x + t * abx
  const cy = a.y + t * aby
  const cz = a.z + t * abz
  const dx = p.x - cx
  const dy = p.y - cy
  const dz = p.z - cz
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
}

/**
 * Iterative RDP simplification of a closed/ordered 3D polyline.
 * `epsilon` is in the same units as the points (globe radii here).
 * Returns the array of kept indices.
 */
export function rdpIndices(points: RdpPoint[], epsilon: number): number[] {
  const n = points.length
  if (n < 3 || epsilon <= 0) return points.map((_, i) => i)

  const keep = new Uint8Array(n)
  keep[0] = 1
  keep[n - 1] = 1
  const stack: Array<[number, number]> = [[0, n - 1]]

  while (stack.length) {
    const [start, end] = stack.pop()!
    let maxDist = 0
    let maxIdx = -1
    const a = points[start]
    const b = points[end]
    for (let i = start + 1; i < end; i++) {
      const d = perpDistance(points[i], a, b)
      if (d > maxDist) {
        maxDist = d
        maxIdx = i
      }
    }
    if (maxDist > epsilon && maxIdx !== -1) {
      keep[maxIdx] = 1
      stack.push([start, maxIdx])
      stack.push([maxIdx, end])
    }
  }

  const out: number[] = []
  for (let i = 0; i < n; i++) if (keep[i]) out.push(i)
  return out
}

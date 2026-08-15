import { fingerprintAxes } from '@/lib/investigation'
import type { BoardEntry } from '@/lib/risk-report'

interface QuantFingerprintProps {
  entry: BoardEntry
  size?: 'sm' | 'md'
}

/**
 * Polar identity of the quantitative noise vector.
 * This glyph is the product signature: every axis is a cited detector,
 * not a decoration.
 */
export default function QuantFingerprint({ entry, size = 'md' }: QuantFingerprintProps) {
  const axes = fingerprintAxes(entry)
  const dim = size === 'sm' ? 160 : 232
  const cx = dim / 2
  const cy = dim / 2
  const r = size === 'sm' ? 44 : 68
  const n = axes.length
  const angle = (i: number) => -Math.PI / 2 + (i * 2 * Math.PI) / n
  const pt = (i: number, u: number) => {
    const a = angle(i)
    return [cx + Math.cos(a) * r * u, cy + Math.sin(a) * r * u] as const
  }
  const poly = axes.map((ax, i) => pt(i, ax.unit).map((v) => v.toFixed(1)).join(',')).join(' ')
  const rings = [0.25, 0.5, 0.75, 1]

  return (
    <div>
      <svg
        viewBox={`0 0 ${dim} ${dim}`}
        preserveAspectRatio="xMidYMid meet"
        className="mx-auto block aspect-square h-auto w-full max-w-[232px]"
        role="img"
        aria-label="Quantitative noise fingerprint"
      >
        {rings.map((u) => (
          <polygon
            key={u}
            points={axes
              .map((_, i) => pt(i, u).map((v) => v.toFixed(1)).join(','))
              .join(' ')}
            fill="none"
            stroke="rgba(255,255,255,0.10)"
            strokeWidth={1}
          />
        ))}
        {axes.map((_, i) => {
          const [x, y] = pt(i, 1)
          return (
            <line
              key={i}
              x1={cx}
              y1={cy}
              x2={x}
              y2={y}
              stroke="rgba(255,255,255,0.10)"
              strokeWidth={1}
            />
          )
        })}
        <polygon
          points={poly}
          fill="rgba(52,211,153,0.18)"
          stroke="#34d399"
          strokeWidth={1.6}
          strokeLinejoin="round"
        />
        {axes.map((ax, i) => {
          const [x, y] = pt(i, ax.unit)
          return <circle key={ax.key} cx={x} cy={y} r={2.2} fill="#ecfdf5" />
        })}
        {axes.map((ax, i) => {
          const [x, y] = pt(i, 1.28)
          return (
            <text
              key={ax.key}
              x={x}
              y={y}
              textAnchor="middle"
              dominantBaseline="middle"
              fill="#a1a1aa"
              fontSize={size === 'sm' ? 8 : 10}
              fontFamily="IBM Plex Sans, sans-serif"
            >
              {ax.label}
            </text>
          )
        })}
      </svg>
      {size === 'md' && (
        <div className="mt-1 grid grid-cols-4 gap-x-2 gap-y-0.5 text-[10px] tabular-nums text-zinc-500">
          {axes.map((ax) => (
            <div key={ax.key} title={ax.hint}>
              <span className="text-zinc-400">{ax.label}</span>{' '}
              {ax.raw == null ? '—' : ax.raw.toFixed(2)}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

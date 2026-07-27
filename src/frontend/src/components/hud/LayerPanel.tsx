import { UI_GROUPS } from '@/lib/satellites'

interface LayerPanelProps {
  counts: number[]
  visible: boolean[]
  onToggle: (index: number) => void
  variant?: 'card' | 'bare'
}

export default function LayerPanel({
  counts,
  visible,
  onToggle,
  variant = 'card',
}: LayerPanelProps) {
  const list = (
    <div className="space-y-0.5">
      {UI_GROUPS.map((g, i) => (
        <button
          key={g.key}
          onClick={() => onToggle(i)}
          className={`flex min-h-[32px] w-full items-center gap-2.5 px-2 py-1 text-left transition-opacity hover:bg-white/[0.05] ${
            visible[i] ? '' : 'opacity-35'
          }`}
        >
          <span
            className="h-[7px] w-[7px] shrink-0"
            style={{ background: g.color, boxShadow: `0 0 5px ${g.color}66` }}
          />
          <span className="flex-1 truncate text-sm text-zinc-300">{g.label}</span>
          <span className="text-[14px] tabular-nums text-zinc-400">
            {(counts[i] ?? 0).toLocaleString()}
          </span>
        </button>
      ))}
    </div>
  )

  if (variant === 'bare') return list

  return (
    <div className="athena-panel pointer-events-auto w-[248px] px-3 py-3 max-md:w-full">
      <div className="mb-2 text-[13px] uppercase tracking-[0.2em] text-zinc-400">Layers</div>
      {list}
    </div>
  )
}

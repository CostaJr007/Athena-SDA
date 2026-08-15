import { useEffect, useMemo, useRef, useState } from 'react'
import { boardThreat, type BoardEntry } from '@/lib/risk-report'

export interface PaletteAction {
  id: string
  group: 'action' | 'filter' | 'object'
  label: string
  hint?: string
  run: () => void
}

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
  board: BoardEntry[]
  onSelectNorad: (norad: number) => void
  actions: PaletteAction[]
}

/**
 * Operator command palette (Ctrl/Cmd+K) — jump to objects, filters, surfaces.
 */
export default function CommandPalette({
  open,
  onClose,
  board,
  onSelectNorad,
  actions,
}: CommandPaletteProps) {
  const [q, setQ] = useState('')
  const [idx, setIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const items = useMemo(() => {
    const needle = q.trim().toLowerCase()
    const objectCmds: PaletteAction[] = board.map((b) => ({
      id: `obj-${b.norad_id}`,
      group: 'object',
      label: `${b.object_name}  #${b.norad_id}`,
      hint: `${boardThreat(b)} · ${b.role} · ${b.country} · ${b.orbit_class}`,
      run: () => onSelectNorad(b.norad_id),
    }))
    const all = [...actions, ...objectCmds]
    if (!needle) return all
    return all.filter(
      (c) =>
        c.label.toLowerCase().includes(needle) ||
        (c.hint ?? '').toLowerCase().includes(needle) ||
        c.group.includes(needle),
    )
  }, [q, board, actions, onSelectNorad])

  useEffect(() => {
    if (!open) return
    const t = window.setTimeout(() => {
      setQ('')
      setIdx(0)
      inputRef.current?.focus()
    }, 0)
    return () => clearTimeout(t)
  }, [open])

  if (!open) return null

  const choose = (i: number) => {
    const item = items[i]
    if (!item) return
    item.run()
    onClose()
  }

  return (
    <>
      <button
        type="button"
        aria-label="Close command palette"
        className="pointer-events-auto absolute inset-0 z-[45] cursor-default border-0 bg-black/70"
        onClick={onClose}
      />
      <div
        className="athena-panel pointer-events-auto absolute left-1/2 top-[18%] z-[46] w-[min(520px,calc(100vw-1.5rem))] -translate-x-1/2 overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
      >
        <input
          ref={inputRef}
          value={q}
          onChange={(e) => {
            setQ(e.target.value)
            setIdx(0)
          }}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault()
              setIdx((v) => Math.min(items.length - 1, v + 1))
            } else if (e.key === 'ArrowUp') {
              e.preventDefault()
              setIdx((v) => Math.max(0, v - 1))
            } else if (e.key === 'Enter') {
              e.preventDefault()
              choose(idx)
            } else if (e.key === 'Escape') {
              e.preventDefault()
              onClose()
            }
          }}
          placeholder="Jump to object, filter, or surface…"
          className="athena-input w-full rounded-none border-0 border-b border-white/10 px-3 py-2.5 text-[14px]"
        />
        <div className="athena-scroll max-h-[min(420px,55vh)] overflow-y-auto">
          {items.length === 0 && (
            <div className="px-3 py-4 text-[13px] text-zinc-500">No matches</div>
          )}
          {items.map((c, i) => (
            <button
              key={c.id}
              type="button"
              onMouseEnter={() => setIdx(i)}
              onClick={() => choose(i)}
              className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left ${
                i === idx ? 'bg-emerald-400/12' : 'hover:bg-white/[0.04]'
              }`}
            >
              <div className="min-w-0">
                <div className="truncate text-[13px] text-zinc-100">{c.label}</div>
                {c.hint && (
                  <div className="truncate text-[11px] text-zinc-500">{c.hint}</div>
                )}
              </div>
              <span className="shrink-0 text-[10px] uppercase tracking-wider text-zinc-600">
                {c.group}
              </span>
            </button>
          ))}
        </div>
        <div className="border-t border-white/10 px-3 py-1.5 text-[10px] uppercase tracking-wider text-zinc-600">
          ↑↓ move · enter open · esc close · ctrl+k
        </div>
      </div>
    </>
  )
}

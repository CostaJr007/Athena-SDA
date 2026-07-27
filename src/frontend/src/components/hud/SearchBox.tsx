import { useMemo, useRef, useState } from 'react'
import type { SatInfo } from '@/lib/satellites'

interface SearchBoxProps {
  sats: SatInfo[]
  onSelect: (index: number) => void
}

function fuzzy(name: string, q: string): boolean {
  let i = 0
  for (const ch of name) {
    if (ch === q[i]) i++
    if (i >= q.length) return true
  }
  return false
}

export default function SearchBox({ sats, onSelect }: SearchBoxProps) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const results = useMemo(() => {
    const q = query.trim().toUpperCase()
    if (q.length < 2) return []
    const exact: number[] = []
    const prefix: number[] = []
    const nameHits: number[] = []
    const fuzzyHits: number[] = []
    const isNum = /^\d+$/.test(q)
    for (let i = 0; i < sats.length; i++) {
      const s = sats[i]
      if (isNum) {
        const id = String(s.norad)
        if (id === q) exact.push(i)
        else if (id.startsWith(q)) prefix.push(i)
      }
      const nm = s.name.toUpperCase()
      if (nm.includes(q)) nameHits.push(i)
      else if (!isNum && fuzzy(nm, q)) fuzzyHits.push(i)
      if (exact.length + prefix.length + nameHits.length + fuzzyHits.length >= 24) break
    }
    return [...exact, ...prefix, ...nameHits, ...fuzzyHits].slice(0, 8)
  }, [query, sats])

  const choose = (index: number) => {
    onSelect(index)
    setQuery('')
    setOpen(false)
    inputRef.current?.blur()
  }

  return (
    <div className="pointer-events-auto relative">
      <svg
        viewBox="0 0 16 16"
        className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 stroke-zinc-500"
        fill="none"
        strokeWidth="1.6"
      >
        <circle cx="7" cy="7" r="5" />
        <path d="M11 11l3.5 3.5" />
      </svg>
      <input
        ref={inputRef}
        value={query}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && results.length > 0) choose(results[0])
          if (e.key === 'Escape') {
            if (query) setQuery('')
            else inputRef.current?.blur()
            setOpen(false)
          }
        }}
        placeholder="NORAD / name…"
        className="athena-input w-full py-2.5 pl-9 pr-3 text-sm tracking-wide"
      />
      {open && results.length > 0 && (
        <div className="athena-panel absolute left-0 right-0 top-full z-30 mt-1 overflow-hidden">
          {results.map((i) => (
            <button
              key={sats[i].norad}
              onClick={() => choose(i)}
              className="flex min-h-[36px] w-full items-center justify-between gap-2 border-b border-white/5 px-3 py-1.5 text-left last:border-0 hover:bg-white/[0.06]"
            >
              <span className="truncate text-sm text-zinc-100">{sats[i].name}</span>
              <span className="shrink-0 text-[13px] tabular-nums text-zinc-400">
                #{sats[i].norad}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

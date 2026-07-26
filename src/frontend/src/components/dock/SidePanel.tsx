import type { ReactNode } from 'react'

interface SidePanelProps {
  title: string
  subtitle?: string
  side: 'left' | 'right'
  children: ReactNode
  footer?: ReactNode
  className?: string
}

export default function SidePanel({
  title,
  subtitle,
  side,
  children,
  footer,
  className = '',
}: SidePanelProps) {
  return (
    <aside
      className={`athena-panel athena-space-bg pointer-events-auto flex h-full min-h-0 flex-col overflow-hidden ${className}`}
      data-side={side}
    >
      <header className="athena-panel-header relative z-[2] shrink-0 px-3 py-2.5">
        <div className="flex items-center gap-2">
          <span className="inline-block h-1.5 w-1.5 bg-emerald-400 shadow-[0_0_8px_#34d399]" />
          <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-zinc-100">
            {title}
          </div>
        </div>
        {subtitle && (
          <div className="mt-1 pl-3.5 text-[10px] tracking-wide text-zinc-500">
            {subtitle}
          </div>
        )}
      </header>
      <div className="athena-scroll relative z-[2] min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-2.5 py-2.5 text-zinc-200">
        {children}
      </div>
      {footer && (
        <footer className="relative z-[2] shrink-0 border-t border-white/10 bg-black/60 px-2.5 py-2">
          {footer}
        </footer>
      )}
    </aside>
  )
}

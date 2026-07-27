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
      <header className="athena-panel-header relative z-[2] shrink-0 px-3.5 py-3">
        <div className="flex items-center gap-2">
          <span className="inline-block h-2 w-2 bg-emerald-400 shadow-[0_0_8px_#34d399]" />
          <div className="text-[15px] font-semibold uppercase tracking-[0.12em] text-zinc-100">
            {title}
          </div>
        </div>
        {subtitle && (
          <div className="mt-1.5 pl-4 text-[13px] leading-snug tracking-wide text-zinc-400">
            {subtitle}
          </div>
        )}
      </header>
      <div className="athena-scroll relative z-[2] min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-3 py-3 text-[14px] leading-snug text-zinc-200">
        {children}
      </div>
      {footer && (
        <footer className="relative z-[2] shrink-0 border-t border-white/10 bg-black/60 px-3 py-2.5 text-[13px]">
          {footer}
        </footer>
      )}
    </aside>
  )
}

import type { ActionName } from '@/hooks/useObjectActions'

interface ObjectActionsProps {
  onAction: (name: ActionName) => void
  last?: { action: string; ts: string } | null
  triage?: string
}

/** Validate-only kinetics (US 12,657,514 Actions). */
export default function ObjectActions({ onAction, last, triage }: ObjectActionsProps) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <button
        type="button"
        className="athena-btn px-2 py-1 text-[11px]"
        onClick={() => onAction('AcknowledgeAlert')}
      >
        ACK
      </button>
      <button
        type="button"
        className="athena-btn px-2 py-1 text-[11px]"
        onClick={() => onAction('ResolveAlert')}
      >
        Resolve
      </button>
      <button
        type="button"
        className="athena-btn px-2 py-1 text-[11px]"
        onClick={() => onAction('SuppressAlert')}
      >
        Suppress
      </button>
      <button
        type="button"
        className="athena-btn px-2 py-1 text-[11px]"
        onClick={() => onAction('OpenCase')}
      >
        Open case
      </button>
      <button
        type="button"
        className="athena-btn px-2 py-1 text-[11px]"
        onClick={() => onAction('TaskSatellite')}
      >
        Task sensor
      </button>
      {triage && (
        <span className="text-[10px] uppercase tracking-wider text-zinc-500">
          {triage}
        </span>
      )}
      {last && (
        <span className="text-[10px] uppercase tracking-wider text-zinc-500">
          {last.action} · {last.ts.slice(11, 16)}Z
        </span>
      )}
    </div>
  )
}

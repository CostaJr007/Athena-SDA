import { useEffect, useMemo, useRef, useState } from 'react'
import {
  answerSituation,
  type ObjectGraph,
  type OntologyExplainPayload,
} from '@/lib/investigation'
import type { BoardEntry } from '@/lib/risk-report'

interface OntologyExplainPanelProps {
  entry: BoardEntry
  graph: ObjectGraph | null
}

interface WebCite {
  title?: string
  url?: string
}

interface ExplainResponse {
  text: string
  model: string
  source: 'groq' | 'fallback' | 'watsonx'
  citations?: WebCite[]
}

interface ChatTurn {
  who: 'op' | 'copilot'
  text: string
  cites?: WebCite[]
}

/**
 * Groq + Tavily column beside the object graph.
 * Never surfaces sidecar / .env / script copy.
 */
export default function OntologyExplainPanel({
  entry,
  graph,
}: OntologyExplainPanelProps) {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [model, setModel] = useState<string>('groq')
  const [source, setSource] = useState<'groq' | 'fallback' | 'loading'>('loading')
  const [question, setQuestion] = useState('')
  const [busy, setBusy] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)
  const seqRef = useRef(0)

  const payload = useMemo<OntologyExplainPayload>(() => {
    const links = (graph?.edges ?? []).map((e) => {
      const target = graph?.nodes.find((n) => n.id === e.to)
      return {
        type: e.label,
        label: target ? `${target.label} · ${target.sub}` : e.to,
      }
    })
    return {
      norad: entry.norad_id,
      object_name: entry.object_name,
      role: entry.role,
      status: entry.status,
      country: entry.country,
      orbit_class: entry.orbit_class,
      scores: {
        attention: entry.attention_score,
        anomaly: entry.anomaly_score,
        belief: entry.evidence?.belief_anomalous ?? null,
      },
      nodes: (graph?.nodes ?? []).map((n) => ({
        kind: n.kind,
        label: n.label,
        sub: n.sub,
      })),
      links,
    }
  }, [entry, graph])

  const applyAnswer = (
    seq: number,
    text: string,
    from: 'groq' | 'fallback',
    remoteModel?: string,
    cites?: WebCite[],
  ) => {
    if (seq !== seqRef.current) return
    setTurns((prev) => [...prev, { who: 'copilot', text, cites }])
    setSource(from)
    if (from === 'groq' && remoteModel) setModel(remoteModel)
    else if (from === 'fallback') setModel('local')
  }

  const run = async (q?: string) => {
    const seq = ++seqRef.current
    const asked = (q ?? '').trim()
    const body = { ...payload, question: asked }
    if (asked) {
      setTurns((prev) => [...prev, { who: 'op', text: asked }])
    }
    setBusy(true)
    setSource('loading')
    try {
      const res = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        applyAnswer(seq, answerSituation(body), 'fallback')
        return
      }
      const data = (await res.json()) as ExplainResponse
      const remote = (data.text ?? '').trim()
      const leakedOps =
        /sidecar|serve_granite|\.env|WATSONX_APIKEY|GROQ_API_KEY|TAVILY_API_KEY/i.test(
          remote,
        )
      const cites = (data.citations ?? []).filter((c) => c.url)
      if (remote && !leakedOps && data.source === 'groq') {
        applyAnswer(seq, remote, 'groq', data.model || 'groq', cites)
        return
      }
      if (remote && !leakedOps) {
        applyAnswer(seq, remote, 'fallback', data.model, cites)
        return
      }
      applyAnswer(seq, answerSituation(body), 'fallback')
    } catch {
      applyAnswer(seq, answerSituation(body), 'fallback')
    } finally {
      if (seq === seqRef.current) setBusy(false)
    }
  }

  useEffect(() => {
    seqRef.current += 1
    const t = window.setTimeout(() => {
      setTurns([])
      void run()
    }, 0)
    return () => {
      window.clearTimeout(t)
      seqRef.current += 1
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entry.norad_id])

  useEffect(() => {
    const el = logRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [turns, busy])

  const onAsk = (e: React.FormEvent) => {
    e.preventDefault()
    const q = question.trim()
    if (!q || busy) return
    setQuestion('')
    void run(q)
  }

  return (
    <section className="flex h-full min-h-0 flex-col border border-sky-400/25 bg-sky-500/[0.04]">
      <div className="flex shrink-0 items-center justify-between gap-2 border-b border-white/10 px-2.5 py-1.5">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-200/90">
            Graph copilot
          </div>
          <p className="mt-0.5 truncate text-[10px] text-zinc-500">
            Plain briefing — numbers stay as computed
          </p>
        </div>
        <span
          className={`shrink-0 border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${
            source === 'groq'
              ? 'border-sky-400/50 text-sky-200'
              : source === 'loading'
                ? 'border-white/15 text-zinc-500'
                : 'border-sky-400/30 text-sky-200/80'
          }`}
        >
          {source === 'loading' ? 'reading…' : source === 'groq' ? model : 'local'}
        </span>
      </div>
      <div
        ref={logRef}
        className="athena-scroll min-h-0 flex-1 space-y-2 overflow-y-auto px-2.5 py-2 text-[13px] leading-relaxed"
      >
        {turns.map((t, i) => (
          <div
            key={`${t.who}-${i}`}
            className={
              t.who === 'op'
                ? 'ml-6 border border-white/10 bg-black/40 px-2 py-1.5 text-zinc-100'
                : 'mr-2 whitespace-pre-wrap text-zinc-200'
            }
          >
            {t.who === 'op' && (
              <div className="mb-0.5 text-[10px] uppercase tracking-wider text-zinc-500">
                You
              </div>
            )}
            {t.text}
            {t.who === 'copilot' && t.cites && t.cites.length > 0 && (
              <ul className="mt-1.5 space-y-0.5 text-[11px] text-sky-200/80">
                {t.cites.slice(0, 3).map((c) => (
                  <li key={c.url} className="truncate">
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="underline decoration-sky-400/40 underline-offset-2"
                    >
                      {c.title || c.url}
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
        {busy && (
          <p className="text-[12px] text-zinc-500">Reading this object…</p>
        )}
      </div>
      <form
        onSubmit={onAsk}
        className="flex shrink-0 gap-1.5 border-t border-white/10 p-2"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask in plain words: what is this? is it dangerous? weather?"
          className="athena-input min-w-0 flex-1 px-2 py-1.5 text-[13px]"
        />
        <button
          type="submit"
          disabled={busy}
          className="athena-btn athena-btn-active px-2.5 py-1.5 text-[12px] disabled:opacity-40"
        >
          Ask
        </button>
      </form>
    </section>
  )
}

import { useEffect, useMemo, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
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
  source: 'deepseek' | 'groq' | 'fallback' | 'watsonx'
  citations?: WebCite[]
}

interface StreamEvent {
  delta?: string
  done?: boolean
  model?: string
  source?: 'deepseek' | 'groq' | 'fallback'
  text?: string
  error?: string
}

interface ChatTurn {
  who: 'op' | 'copilot'
  text: string
  cites?: WebCite[]
}

/**
 * AI Graph Copilot (DeepSeek / Groq) column beside the object graph.
 */
export default function OntologyExplainPanel({
  entry,
  graph,
}: OntologyExplainPanelProps) {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [model, setModel] = useState<string>('ai')
  const [source, setSource] = useState<'deepseek' | 'groq' | 'fallback' | 'loading'>('loading')
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
    from: 'deepseek' | 'groq' | 'fallback',
    remoteModel?: string,
    cites?: WebCite[],
  ) => {
    if (seq !== seqRef.current) return
    setTurns((prev) => [...prev, { who: 'copilot', text, cites }])
    setSource(from)
    if ((from === 'deepseek' || from === 'groq') && remoteModel) setModel(remoteModel)
    else if (from === 'fallback') setModel('local')
  }

  /** Append a delta to the last copilot turn (the live streaming bubble). */
  const appendDelta = (delta: string) => {
    setTurns((prev) => {
      if (!prev.length) return prev
      const next = [...prev]
      const last = next[next.length - 1]
      if (!last || last.who !== 'copilot') return prev
      next[next.length - 1] = { ...last, text: last.text + delta }
      return next
    })
  }

  /** Consume /api/explain-stream (SSE). Returns true when handled. */
  const runStream = async (body: OntologyExplainPayload, seq: number): Promise<boolean> => {
    let res: Response
    try {
      res = await fetch('/api/explain-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok || !res.body) return false
    } catch {
      return false
    }
    setTurns((prev) => [...prev, { who: 'copilot', text: '' }])
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    let finalSource: 'deepseek' | 'groq' | 'fallback' = 'fallback'
    let finalModel: string | undefined
    try {
      for (;;) {
        const { value, done } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        let idx: number
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const raw = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          for (const line of raw.split('\n')) {
            if (!line.startsWith('data:')) continue
            const data = line.slice(5).trim()
            if (!data) continue
            let ev: StreamEvent
            try {
              ev = JSON.parse(data) as StreamEvent
            } catch {
              continue
            }
            if (ev.error) throw new Error(ev.error)
            if (ev.delta) appendDelta(ev.delta)
            if (ev.done) {
              if (ev.source) finalSource = ev.source
              if (ev.model) finalModel = ev.model
              if (ev.text) appendDelta(ev.text)
            }
          }
        }
      }
    } catch {
      // stream broke mid-way: keep whatever already arrived
    }
    if (seq !== seqRef.current) return true
    setSource(finalSource)
    if (finalSource === 'deepseek' || finalSource === 'groq') {
      if (finalModel) setModel(finalModel)
    } else {
      setModel('local')
    }
    // If nothing arrived (e.g. provider failed mid-stream), fill with local answer.
    setTurns((prev) => {
      const last = prev[prev.length - 1]
      if (last && last.who === 'copilot' && !last.text.trim()) {
        const next = [...prev]
        next[next.length - 1] = { ...last, text: answerSituation(body) }
        return next
      }
      return prev
    })
    return true
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
      if (await runStream(body, seq)) return
      // Legacy non-streaming path (older sidecar / stream unavailable).
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
        /sidecar|serve_granite|\.env|WATSONX_APIKEY|GROQ_API_KEY|TAVILY_API_KEY|DEEPSEEK_API_KEY/i.test(
          remote,
        )
      const cites = (data.citations ?? []).filter((c) => c.url)
      if (remote && !leakedOps && (data.source === 'deepseek' || data.source === 'groq')) {
        applyAnswer(seq, remote, data.source, data.model || data.source, cites)
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
            Space Domain Awareness AI — immutable scores
          </p>
        </div>
        <span
          className={`shrink-0 border px-1.5 py-0.5 text-[10px] uppercase tracking-wider ${
            source === 'deepseek' || source === 'groq'
              ? 'border-sky-400/50 bg-sky-500/10 text-sky-200'
              : source === 'loading'
                ? 'border-white/15 text-zinc-500'
                : 'border-sky-400/30 text-sky-200/80'
          }`}
        >
          {source === 'loading' ? 'reading…' : source === 'deepseek' || source === 'groq' ? model : 'local'}
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
                ? 'ml-6 border border-sky-400/30 bg-sky-950/30 px-3 py-2 text-zinc-100'
                : 'mr-1 border border-white/5 bg-black/20 p-2.5 text-zinc-200'
            }
          >
            {t.who === 'op' && (
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-sky-400">
                Operador
              </div>
            )}
            {t.who === 'op' ? (
              <div className="whitespace-pre-wrap text-[13px]">{t.text}</div>
            ) : (
              <div className="copilot-markdown text-[12.5px] leading-relaxed text-zinc-200">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ children }) => (
                      <h1 className="mt-3 mb-2 border-b border-sky-400/30 pb-1 text-[13px] font-bold uppercase tracking-wider text-sky-200">
                        {children}
                      </h1>
                    ),
                    h2: ({ children }) => (
                      <h2 className="mt-3 mb-1.5 text-[12px] font-semibold uppercase tracking-wide text-emerald-300">
                        {children}
                      </h2>
                    ),
                    h3: ({ children }) => (
                      <h3 className="mt-2.5 mb-1 text-[11.5px] font-semibold text-sky-100">
                        {children}
                      </h3>
                    ),
                    p: ({ children }) => (
                      <p className="mb-2 leading-relaxed text-zinc-300">{children}</p>
                    ),
                    ul: ({ children }) => (
                      <ul className="my-1.5 list-disc space-y-1 pl-4 text-zinc-300">
                        {children}
                      </ul>
                    ),
                    ol: ({ children }) => (
                      <ol className="my-1.5 list-decimal space-y-1 pl-4 text-zinc-300">
                        {children}
                      </ol>
                    ),
                    li: ({ children }) => <li className="leading-snug">{children}</li>,
                    blockquote: ({ children }) => (
                      <blockquote className="my-2 border-l-2 border-emerald-400/60 bg-emerald-500/5 px-2.5 py-1.5 text-[11.5px] italic text-zinc-300">
                        {children}
                      </blockquote>
                    ),
                    table: ({ children }) => (
                      <div className="my-2 max-w-full overflow-x-auto rounded border border-white/10 bg-black/40">
                        <table className="min-w-full divide-y divide-white/10 text-left text-[11px]">
                          {children}
                        </table>
                      </div>
                    ),
                    thead: ({ children }) => (
                      <thead className="bg-white/5 font-semibold text-zinc-200">
                        {children}
                      </thead>
                    ),
                    th: ({ children }) => (
                      <th className="px-2.5 py-1.5 font-semibold text-sky-200">
                        {children}
                      </th>
                    ),
                    td: ({ children }) => (
                      <td className="border-t border-white/5 px-2.5 py-1.5 text-zinc-300">
                        {children}
                      </td>
                    ),
                    code: ({ children, className }) => {
                      const isInline = !className
                      return isInline ? (
                        <code className="rounded bg-white/10 px-1 py-0.5 font-mono text-[11px] text-sky-200">
                          {children}
                        </code>
                      ) : (
                        <pre className="my-2 overflow-x-auto rounded border border-white/10 bg-black/60 p-2 font-mono text-[11px] text-emerald-300">
                          <code>{children}</code>
                        </pre>
                      )
                    },
                    hr: () => <hr className="my-2.5 border-white/10" />,
                    strong: ({ children }) => (
                      <strong className="font-semibold text-white">{children}</strong>
                    ),
                  }}
                >
                  {t.text}
                </ReactMarkdown>
              </div>
            )}
            {t.who === 'copilot' && t.cites && t.cites.length > 0 && (
              <ul className="mt-2 space-y-0.5 border-t border-white/5 pt-1.5 text-[11px] text-sky-200/80">
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

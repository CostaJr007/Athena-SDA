import { useEffect, useMemo, useState } from 'react'
import QuantFingerprint from '@/components/hud/QuantFingerprint'
import OntologyExplainPanel from '@/components/hud/OntologyExplainPanel'
import EventReplayPanel from '@/components/hud/EventReplayPanel'
import ObjectActions from '@/components/hud/ObjectActions'
import {
  buildObjectGraph,
  casesForNorad,
  expandNeighbors,
  layoutInvGraph,
  pairsForNorad,
  rectEdgePoint,
  satObjectId,
  searchAround,
  type GraphKind,
  type GraphNode,
  type InvestigationBundle,
} from '@/lib/investigation'
import type { WfCaseHit } from '@/lib/investigation'
import { boardThreat, THREAT_STYLE, type BoardEntry, type RiskReport } from '@/lib/risk-report'
import { useObjectActions } from '@/hooks/useObjectActions'
import { buildDossierHtml, downloadDossier } from '@/lib/dossier'

interface InvestigationCanvasProps {
  open: boolean
  onClose: () => void
  entry: BoardEntry | null
  report: RiskReport | null
  cases: WfCaseHit[]
  onSelectNorad: (norad: number) => void
  onOpenCase: (eventId: string) => void
  investigation?: InvestigationBundle | null
}

const KIND_TAG: Record<GraphKind, string> = {
  satellite: 'SAT',
  asset: 'ASSET',
  alert: 'ALERT',
  case: 'CASE',
  weather: 'WX',
  evidence: 'DS',
  peer: 'PEER',
  document: 'DOC',
}

/**
 * Palantir-style object investigation: linked ontology graph + cited
 * noise fingerprint. This is the surface that is not a sat tracker.
 */
export default function InvestigationCanvas({
  open,
  onClose,
  entry,
  report,
  cases,
  onSelectNorad,
  onOpenCase,
  investigation = null,
}: InvestigationCanvasProps) {
  const extraPairs = useMemo(
    () => (entry ? pairsForNorad(report, entry.norad_id) : []),
    [entry, report],
  )
  const around = useMemo(
    () => (entry ? searchAround(entry, report, cases) : { peers: [], placeboCases: [] }),
    [entry, report, cases],
  )
  const [hops, setHops] = useState(1)
  const graph = useMemo(() => {
    if (!entry) return null
    const startId = satObjectId(entry.norad_id)
    const invObj = investigation?.objects.find((o) => o.id === startId)
    if (investigation && invObj) {
      const nb = expandNeighbors(investigation, startId, hops)
      return layoutInvGraph(invObj, nb)
    }
    return buildObjectGraph(entry, cases, extraPairs, around)
  }, [entry, cases, extraPairs, around, investigation, hops])
  const ownCases = entry ? casesForNorad(cases, entry.norad_id) : []
  const [replayId, setReplayId] = useState<string | null>(null)
  const activeReplay = replayId ?? ownCases[0]?.eventId ?? null
  const { log, record, triage } = useObjectActions(entry?.norad_id ?? null)

  useEffect(() => {
    const id = window.setTimeout(() => setReplayId(null), 0)
    return () => window.clearTimeout(id)
  }, [entry?.norad_id])

  if (!open) return null

  const threat = entry ? boardThreat(entry) : null
  const style = threat ? THREAT_STYLE[threat] : null

  const onNode = (node: GraphNode) => {
    if (node.eventId) {
      setReplayId(node.eventId)
      return
    }
    if (node.norad != null && node.id !== 'sat') {
      onSelectNorad(node.norad)
    }
  }

  const exportDossier = () => {
    if (!entry) return
    const html = buildDossierHtml({ entry, report, graph, cases })
    downloadDossier(html, entry.norad_id, report?.day)
  }

  return (
    <div
      className="athena-panel pointer-events-auto flex h-full min-h-0 flex-col overflow-hidden"
      role="dialog"
      aria-label="Object investigation"
    >
      <header className="athena-panel-header flex shrink-0 items-start justify-between gap-2 px-3 py-2.5">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-300/90">
            Object view · investigation
          </div>
          <div className="mt-0.5 truncate text-[14px] font-semibold text-zinc-50">
            {entry ? entry.object_name : 'No object selected'}
            {entry && (
              <span className="ml-2 font-mono text-[12px] font-normal text-zinc-500">
                #{entry.norad_id}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-[11px] text-zinc-500">
            Ontology links live with the board · US 12,374,011-style object map
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {style && (
            <span
              className={`border px-1.5 py-0.5 text-[11px] tracking-wider ${style.border} ${style.color}`}
            >
              {style.label}
            </span>
          )}
          {entry && (
            <button
              type="button"
              onClick={exportDossier}
              className="athena-btn px-2 py-0.5 text-[12px]"
              title="Export investigation dossier"
            >
              Dossier
            </button>
          )}
          <button type="button" onClick={onClose} className="athena-btn px-2 py-0.5 text-[12px]">
            Close
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-3 py-2.5">
        {!entry ? (
          <div className="border border-dashed border-white/15 bg-black/40 px-3 py-8 text-center">
            <div className="text-sm text-zinc-200">Select a watchlist object</div>
            <p className="mt-2 text-[13px] leading-relaxed text-zinc-400">
              Use the mission board, search, or Ctrl+K.
            </p>
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col gap-3">
            <div className="grid min-h-[300px] shrink-0 grid-cols-1 gap-3 lg:grid-cols-2">
              <section className="flex min-h-[240px] flex-col overflow-hidden border border-white/10 bg-black/40">
                <div className="flex shrink-0 items-center justify-between border-b border-white/10 px-2.5 py-1.5 text-[11px] uppercase tracking-[0.16em] text-zinc-500">
                  <span>Linked objects{investigation ? ' · investigation.v1' : ''}</span>
                  <span className="flex gap-1">
                    {([1, 2, 3] as const).map((h) => (
                      <button
                        key={h}
                        type="button"
                        onClick={() => setHops(h)}
                        className={`px-1.5 py-0.5 text-[10px] ${
                          hops === h ? 'athena-btn athena-btn-active' : 'athena-btn'
                        }`}
                        title={`${h} hop${h > 1 ? 's' : ''}`}
                      >
                        {h}h
                      </button>
                    ))}
                  </span>
                </div>
                <div className="min-h-0 flex-1">
                  {graph && <ObjectGraphView graph={graph} onNode={onNode} />}
                </div>
                <p className="shrink-0 border-t border-white/10 px-2.5 py-1.5 text-[11px] leading-relaxed text-zinc-500">
                  Asset / peer follow the link. Case loads the temporal tile
                  in this fiche (not a new tab).
                </p>
              </section>
              <div className="h-full min-h-[240px]">
                <OntologyExplainPanel entry={entry} graph={graph} />
              </div>
            </div>

            <div className="grid shrink-0 gap-3 lg:grid-cols-2">
              <section className="border border-white/10 bg-black/40 px-2.5 py-2">
                <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">
                  Quant fingerprint
                </div>
                <p className="mt-0.5 text-[10px] leading-snug text-zinc-600">
                  Cited detectors — LZ76 · DFA · CUSUM · DS
                </p>
                <QuantFingerprint entry={entry} size="md" />
              </section>
              <section className="min-h-0 border border-white/10 bg-black/40 px-2 py-2">
                <div className="mb-1 flex items-center justify-between">
                  <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">
                    Temporal tile
                  </div>
                  <div className="flex items-center gap-1">
                    {ownCases.length > 1 && (
                      <select
                        value={activeReplay ?? ''}
                        onChange={(e) => setReplayId(e.target.value || null)}
                        className="athena-input px-1.5 py-0.5 text-[11px]"
                      >
                        {ownCases.map((c) => (
                          <option key={c.eventId} value={c.eventId}>
                            {c.eventId}
                          </option>
                        ))}
                      </select>
                    )}
                    {activeReplay && (
                      <button
                        type="button"
                        className="athena-btn px-1.5 py-0.5 text-[10px]"
                        onClick={() => onOpenCase(activeReplay)}
                      >
                        PoC
                      </button>
                    )}
                  </div>
                </div>
                {activeReplay ? (
                  <EventReplayPanel
                    eventId={activeReplay}
                    norad={entry.norad_id}
                    threshold={report?.summary.threshold ?? 0.5}
                    compact
                  />
                ) : (
                  <p className="text-[12px] text-zinc-500">
                    No walk-forward case on this NORAD.
                  </p>
                )}
              </section>
            </div>

            <div className="shrink-0 border border-white/10 bg-black/50 px-2.5 py-2">
              <div className="mb-1.5 flex items-center justify-between gap-2">
                <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">
                  Actions · validate-only · triage {triage}
                </div>
                <ObjectActions
                  onAction={(name) =>
                    void record(name, {
                      eventId: activeReplay,
                    })
                  }
                  last={log[log.length - 1] ?? null}
                  triage={triage}
                />
              </div>
              <div className="text-[11px] uppercase tracking-[0.16em] text-zinc-500">
                Lineage · insight-first
              </div>
              <div className="mt-1.5 flex flex-wrap items-center gap-1 text-[11px] text-zinc-400">
                {(
                  [
                    'TLE public',
                    'noise features',
                    'IF past-only',
                    'DS fusion',
                    'attention / Kelly',
                  ] as const
                ).map((step, i) => (
                  <span key={step} className="inline-flex items-center gap-1">
                    {i > 0 && <span className="text-zinc-600">→</span>}
                    <span className="border border-white/10 bg-black/60 px-1.5 py-0.5">
                      {step}
                    </span>
                  </span>
                ))}
              </div>
              <p className="mt-1.5 text-[11px] leading-relaxed text-zinc-500">
                {report?.schema ?? 'athena.risk_report.v1'} · day {report?.day ?? '—'} ·{' '}
                {(report?.doctrine ?? 'military_first_sda').replace(/_/g, ' ')}
                {investigation?.provenance ? ' · provenance attached' : ''}
              </p>
              <WhatIfButton norad={entry.norad_id} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function WhatIfButton({ norad }: { norad: number }) {
  const [msg, setMsg] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const run = async () => {
    setBusy(true)
    setMsg(null)
    try {
      const res = await fetch('/api/whatif', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ norad, delta_km: 4.5 }),
      })
      if (!res.ok) {
        setMsg('sidecar offline — python scripts/run_whatif.py')
        return
      }
      const data = (await res.json()) as { fired?: boolean; delta_cusum?: number }
      setMsg(
        data.fired
          ? `injected burn detected (ΔCUSUM ${data.delta_cusum ?? '—'})`
          : 'injected burn did not trip CUSUM/EWMA',
      )
    } catch {
      setMsg('sidecar offline — python scripts/run_whatif.py')
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="mt-1.5 flex items-center gap-2">
      <button
        type="button"
        className="athena-btn px-2 py-0.5 text-[11px]"
        disabled={busy}
        onClick={() => void run()}
        title="Inject a synthetic SMA burn (does not change live scores)"
      >
        What-if burn
      </button>
      {msg && <span className="text-[11px] text-zinc-500">{msg}</span>}
    </div>
  )
}

function ObjectGraphView({
  graph,
  onNode,
}: {
  graph: { nodes: GraphNode[]; edges: { from: string; to: string; label: string }[] }
  onNode: (n: GraphNode) => void
}) {
  const [hoverId, setHoverId] = useState<string | null>(null)
  const byId = useMemo(() => {
    const m = new Map<string, GraphNode>()
    for (const n of graph.nodes) m.set(n.id, n)
    return m
  }, [graph.nodes])

  const drawn = useMemo(() => {
    return graph.edges
      .map((e) => {
        const a = byId.get(e.from)
        const b = byId.get(e.to)
        if (!a || !b) return null
        const p1 = rectEdgePoint(a, b)
        const p2 = rectEdgePoint(b, a)
        const mx = (p1.x + p2.x) / 2
        const my = (p1.y + p2.y) / 2
        const dx = p2.x - p1.x
        const dy = p2.y - p1.y
        const len = Math.hypot(dx, dy) || 1
        const bulge = e.to === 'asset' ? 0 : 2.2
        const cx = mx - (dy / len) * bulge
        const cy = my + (dx / len) * bulge
        const t = 0.56
        const u = 1 - t
        const lx = u * u * p1.x + 2 * u * t * cx + t * t * p2.x
        const ly = u * u * p1.y + 2 * u * t * cy + t * t * p2.y
        return {
          key: `${e.from}-${e.to}`,
          label: e.label,
          d: `M ${p1.x.toFixed(2)} ${p1.y.toFixed(2)} Q ${cx.toFixed(2)} ${cy.toFixed(2)} ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`,
          lx,
          ly,
        }
      })
      .filter((v): v is NonNullable<typeof v> => v != null)
  }, [graph.edges, byId])

  return (
    <div
      className="relative h-full min-h-[220px] w-full"
      style={{
        backgroundImage:
          'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.08) 1px, transparent 0)',
        backgroundSize: '14px 14px',
      }}
    >
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="absolute inset-0 h-full w-full"
        aria-hidden
      >
        {drawn.map((e) => (
          <path
            key={e.key}
            d={e.d}
            fill="none"
            stroke="rgba(212,212,216,0.32)"
            strokeWidth={1.15}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>

      {drawn.map((e) => (
        <span
          key={`lbl-${e.key}`}
          className="pointer-events-none absolute z-[2] hidden -translate-x-1/2 -translate-y-1/2 bg-[#07090d]/90 px-1 text-[9px] uppercase tracking-wider text-zinc-500 md:inline"
          style={{ left: `${e.lx}%`, top: `${e.ly}%` }}
        >
          {e.label}
        </span>
      ))}

      {graph.nodes.map((n) => {
        const hub = n.kind === 'satellite'
        const clickable = !!(n.eventId || (n.norad != null && n.id !== 'sat'))
        const hot = hoverId === n.id
        return (
          <button
            key={n.id}
            type="button"
            onClick={() => {
              if (clickable) onNode(n)
            }}
            onMouseEnter={() => setHoverId(n.id)}
            onMouseLeave={() => setHoverId(null)}
            title={n.sub}
            className={`absolute z-[1] flex -translate-x-1/2 -translate-y-1/2 flex-col justify-center overflow-hidden border bg-[#07090d] px-2 py-1.5 text-left ${
              clickable ? 'cursor-pointer hover:bg-[#0d141c]' : 'cursor-default'
            } ${hot ? 'z-10' : ''}`}
            style={{
              left: `${n.x}%`,
              top: `${n.y}%`,
              width: hub ? '26%' : '21%',
              borderColor: hot || hub ? n.color : `${n.color}88`,
            }}
          >
            <span
              className="mb-0.5 text-[9px] font-semibold uppercase tracking-[0.14em]"
              style={{ color: n.color }}
            >
              {KIND_TAG[n.kind]}
            </span>
            <span className="truncate text-[12px] font-medium leading-tight text-zinc-50">
              {n.label}
            </span>
            <span className="mt-0.5 truncate font-mono text-[10px] leading-tight text-zinc-500">
              {n.sub}
            </span>
          </button>
        )
      })}
    </div>
  )
}

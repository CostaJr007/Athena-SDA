/**
 * Object-graph + quant fingerprint helpers.
 *
 * Palantir US 12,374,011 B2 (interactive data object map): a selected
 * Satellite is the pivot; histogram/board filters and ontology links
 * (threatens / hasAlert / validatedBy) update together.
 *
 * The fingerprint is Athena-specific: no public sat-tracker exposes a
 * cited noise vector (LZ76, DFA, CUSUM, …) as an identity glyph.
 */
import type { BoardEntry, FeaturesSnapshot, RiskReport, TopPair } from '@/lib/risk-report'
import { boardThreat, THREAT_HEX } from '@/lib/risk-report'

export interface FingerAxis {
  key: string
  label: string
  /** Raw value (may be missing). */
  raw: number | null
  /** 0–1 for the radar, clipped to `cap`. */
  unit: number
  cap: number
  hint: string
}

export const FINGERPRINT_AXES: Array<{
  key: keyof FeaturesSnapshot | 'belief'
  label: string
  cap: number
  hint: string
}> = [
  { key: 'lz76_complexity', label: 'LZ76', cap: 2, hint: 'Kaspar–Schuster compressibility' },
  { key: 'dfa_hurst_sma', label: 'DFA α', cap: 1, hint: 'Peng 1994 persistence' },
  { key: 'shannon_entropy_sma_30d', label: 'Shannon', cap: 3.5, hint: 'ΔSMA messiness' },
  { key: 'permutation_entropy', label: 'Perm H', cap: 1, hint: 'Bandt–Pompe ordinal' },
  { key: 'page_cusum_sma', label: 'CUSUM', cap: 1, hint: 'Page ARL regime break' },
  { key: 'ewma_sma', label: 'EWMA', cap: 1, hint: 'Small-shift detector' },
  { key: 'bocpd_change_prob_3d', label: 'BOCPD', cap: 1, hint: 'Bayesian change prob' },
  { key: 'belief', label: 'Belief', cap: 1, hint: 'Dempster–Shafer Bel(anomalous)' },
]

export function fingerprintAxes(entry: BoardEntry): FingerAxis[] {
  const fs = entry.features_snapshot ?? {}
  return FINGERPRINT_AXES.map((ax) => {
    const raw =
      ax.key === 'belief'
        ? (entry.evidence?.belief_anomalous ?? null)
        : (fs[ax.key] ?? null)
    const n = raw == null || !Number.isFinite(raw) ? 0 : Math.max(0, Math.min(1, raw / ax.cap))
    return {
      key: String(ax.key),
      label: ax.label,
      raw: raw == null || !Number.isFinite(raw) ? null : raw,
      unit: n,
      cap: ax.cap,
      hint: ax.hint,
    }
  })
}

export interface WfCaseHit {
  eventId: string
  type: string
  tPeak: string
  norad: number
  name: string
  hit: boolean
  leadDays: number | null
  maxScore: number | null
  isPlacebo: boolean
}

const EVENT_SHORT: Record<string, string> = {
  luch1_intelsat_2015: 'Luch·IS 2015',
  luch1_intelsat_mid2015: 'Luch·IS mid-15',
  luch1_athena_fidus_2018: 'Luch·Fidus 18',
  luch1_geo_ops_2024: 'Luch·GEO 24',
  luch2_geo_ops_2024: 'Luch-2 GEO 24',
  luch2_trailing_2023: 'Luch-2 trail 23',
  sy12_geo_rpo_2021_22: 'SY-12 RPO',
  sy12_interest_2024h2: 'SY-12 24H2',
  shiyan7_experimental_2015: 'SY-7 2015',
  yaogan29_recon_2020: 'YG-29 2020',
  yaogan29_sso_2025q1: 'YG-29 SSO 25',
  yaogan3_recon_2016: 'YG-3 2016',
  tianhe_css_assembly_2021: 'Tianhe 2021',
  cosmos2550_military_leo_2022: 'C2550 2022',
  beidou3_m11_meo_2019: 'Beidou M11',
  placebo_terra_2015: 'TERRA 2015',
  placebo_terra_2018: 'TERRA 2018',
  placebo_terra_2024h2: 'TERRA 24H2',
  placebo_aqua_2015: 'AQUA 2015',
  placebo_aqua_2020: 'AQUA 2020',
  placebo_landsat8_2018: 'L8 2018',
  placebo_noaa18_2021: 'NOAA-18 21',
  placebo_noaa20_2023: 'NOAA-20 23',
  placebo_noaa20_2024h2: 'NOAA-20 24',
  placebo_gps_meo_2018: 'GPS 2018',
  placebo_starlink_2023: 'Starlink 23',
}

export function shortEventLabel(eventId: string): string {
  return EVENT_SHORT[eventId] ?? eventId.replace(/_/g, ' ')
}

export function casesForNorad(cases: WfCaseHit[], norad: number): WfCaseHit[] {
  return cases.filter((c) => c.norad === norad)
}

export function pairsForNorad(report: RiskReport | null, norad: number): TopPair[] {
  if (!report?.top_pairs) return []
  return report.top_pairs.filter(
    (p) => p.suspect_norad === norad || p.asset_norad === norad,
  )
}

/** Gotham Graph search-around: same-asset suspects + same-t_peak placebos. */
export interface SearchAround {
  peers: Array<{ norad: number; name: string; pairRisk?: number }>
  placeboCases: WfCaseHit[]
}

export function searchAround(
  entry: BoardEntry,
  report: RiskReport | null,
  cases: WfCaseHit[],
): SearchAround {
  const asset =
    entry.pair?.asset_norad ?? (entry.role === 'asset' ? entry.norad_id : null)
  const peers: SearchAround['peers'] = []
  const seen = new Set<number>()
  if (asset != null && report?.top_pairs) {
    for (const p of report.top_pairs) {
      if (p.asset_norad !== asset) continue
      if (p.suspect_norad === entry.norad_id || seen.has(p.suspect_norad)) continue
      seen.add(p.suspect_norad)
      peers.push({
        norad: p.suspect_norad,
        name: p.suspect_name,
        pairRisk: p.pair_risk,
      })
    }
  }
  const ownPeaks = new Set(
    casesForNorad(cases, entry.norad_id)
      .map((c) => c.tPeak.slice(0, 10))
      .filter(Boolean),
  )
  const placeboCases = cases.filter(
    (c) =>
      c.isPlacebo &&
      c.norad !== entry.norad_id &&
      ownPeaks.has(c.tPeak.slice(0, 10)),
  )
  return { peers: peers.slice(0, 2), placeboCases: placeboCases.slice(0, 1) }
}

export interface OntologyExplainPayload {
  norad: number
  object_name: string
  role: string
  status: string
  country?: string | null
  orbit_class?: string | null
  scores: {
    attention: number | null
    anomaly: number | null
    belief: number | null
  }
  nodes: Array<{ kind: string; label: string; sub: string }>
  links: Array<{ type: string; label: string }>
  question?: string
}

function linkOf(payload: OntologyExplainPayload, type: string) {
  return payload.links.find((l) => l.type === type)
}

function fmtScore(n: number | null | undefined, digits = 3): string {
  return n == null || !Number.isFinite(n) ? '—' : n.toFixed(digits)
}

/** Situation brief for the selected object — not a type-system lecture. */
export function situationBrief(payload: OntologyExplainPayload): string {
  const name = payload.object_name || 'This object'
  const role = payload.role || 'unknown'
  const status = payload.status || '—'
  const orbit = payload.orbit_class || '—'
  const country = payload.country || '—'
  const pair = linkOf(payload, 'threatens')
  const alert = linkOf(payload, 'hasAlert')
  const wx = linkOf(payload, 'weather')
  const ev = linkOf(payload, 'fusedAs')
  const wf = linkOf(payload, 'validatedBy')

  const lines = [
    `${name} (#${payload.norad}) · ${role} · ${orbit} · ${country} · status ${status}.`,
    `Attention ${fmtScore(payload.scores.attention)} · anomaly ${fmtScore(payload.scores.anomaly)} · DS belief ${fmtScore(payload.scores.belief)}.`,
  ]
  if (pair) lines.push(`Pair: ${pair.label}.`)
  if (alert) lines.push(`Alert: ${alert.label}.`)
  if (wx) lines.push(`Weather window: ${wx.label}.`)
  if (ev) lines.push(`Evidence: ${ev.label}.`)
  if (wf) lines.push(`Walk-forward case: ${wf.label}.`)
  lines.push('Ask about the pair, alert, weather, or scores. This panel does not change them.')
  return lines.join('\n')
}

/** Answer an operator question from the current graph payload. */
export function answerSituation(payload: OntologyExplainPayload): string {
  const q = (payload.question ?? '').trim().toLowerCase()
  if (!q) return situationBrief(payload)

  const pair = linkOf(payload, 'threatens')
  const alert = linkOf(payload, 'hasAlert')
  const wx = linkOf(payload, 'weather')
  const ev = linkOf(payload, 'fusedAs')
  const wf = linkOf(payload, 'validatedBy')

  if (/threaten|pair|asset|shadow|proxim|dist/.test(q)) {
    if (!pair) {
      return `${payload.object_name} has no pair link on this board. Attention is from its own series, not a named asset.`
    }
    return `Pair on this object: ${pair.label}. That link ranks attention toward a protected asset. It is not a statement of intent.`
  }
  if (/alert|anom|hostile|mil|flag|status/.test(q)) {
    if (!alert) {
      return `${payload.object_name} has no alert node on this graph. Status ${payload.status}. Anomaly ${fmtScore(payload.scores.anomaly)}.`
    }
    return `Alert on this object: ${alert.label}. Status ${payload.status}. Anomaly ${fmtScore(payload.scores.anomaly)}.`
  }
  if (/weather|f10|storm|ap\b|kp\b|sun|drag/.test(q)) {
    if (!wx) return 'No weather node on this graph.'
    return `Weather on this window: ${wx.label}. Use it to separate drag from a control change — it does not set the IF score by itself.`
  }
  if (/score|belief|attention|anomal|ds |fusion|kelly/.test(q)) {
    return [
      `Immutable scores for ${payload.object_name}:`,
      `attention ${fmtScore(payload.scores.attention)} · anomaly ${fmtScore(payload.scores.anomaly)} · DS belief ${fmtScore(payload.scores.belief)}.`,
      ev ? `Fusion node: ${ev.label}.` : '',
    ]
      .filter(Boolean)
      .join('\n')
  }
  if (/case|walk|valid|proof|peak/.test(q)) {
    if (!wf) {
      return `${payload.object_name} has no walk-forward case attached on this graph.`
    }
    return `Walk-forward case: ${wf.label}. Public t_peak is an open-source anchor, not classified ground truth.`
  }

  return `${situationBrief(payload)}\n\nQuestion: ${payload.question}`
}

export type GraphKind =
  | 'satellite'
  | 'asset'
  | 'alert'
  | 'case'
  | 'weather'
  | 'evidence'
  | 'peer'
  | 'document'

export interface GraphNode {
  id: string
  kind: GraphKind
  x: number
  y: number
  label: string
  sub: string
  color: string
  norad?: number
  eventId?: string
}

export interface GraphEdge {
  from: string
  to: string
  label: string
}

export interface ObjectGraph {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const KIND_COLOR: Record<GraphKind, string> = {
  satellite: '#34d399',
  asset: '#38bdf8',
  alert: '#fb7185',
  case: '#a78bfa',
  weather: '#fbbf24',
  evidence: '#c4b5fd',
  peer: '#94a3b8',
  document: '#e2e8f0',
}

/** Percent-space canvas (0–100). HTML cards sit on these points; SVG edges share the same space. */
export const GRAPH_NODE_HW = 10.5
export const GRAPH_NODE_HH = 9.5
export const GRAPH_HUB_HW = 13
export const GRAPH_HUB_HH = 10.5

const SLOTS: Record<string, { x: number; y: number }> = {
  sat: { x: 50, y: 50 },
  asset: { x: 50, y: 87 },
  alert: { x: 15.5, y: 18 },
  wx: { x: 15.5, y: 82 },
  case0: { x: 84.5, y: 16 },
  case1: { x: 84.5, y: 40 },
  ev: { x: 84.5, y: 82 },
  peer0: { x: 28, y: 48 },
  peer1: { x: 72, y: 58 },
  placebo: { x: 72, y: 28 },
}

function shortStatus(status: string): string {
  if (status === 'UNRELIABLE_DATA') return 'UNRELIABLE'
  if (status === 'PAIR_ELEVATED') return 'PAIR ↑'
  if (status === 'ASSET_REGIME_NOISE') return 'REGIME'
  if (status === 'CALIBRATION_BASELINE') return 'CAL'
  if (status === 'CHANGE_RELEVANT') return 'CHANGE'
  return status
}

/**
 * Hub-and-spoke object map. Coordinates are percentages of a 16:10 canvas
 * so cards keep a constant aspect (no SVG stretch).
 */
export function buildObjectGraph(
  entry: BoardEntry,
  cases: WfCaseHit[],
  extraPairs: TopPair[],
  around?: SearchAround,
): ObjectGraph {
  const threat = boardThreat(entry)
  const nodes: GraphNode[] = [
    {
      id: 'sat',
      kind: 'satellite',
      ...SLOTS.sat,
      label: entry.object_name,
      sub: `#${entry.norad_id} · ${entry.role}`,
      color: THREAT_HEX[threat],
      norad: entry.norad_id,
    },
  ]
  const edges: GraphEdge[] = []

  const pair = entry.pair
  if (pair) {
    nodes.push({
      id: 'asset',
      kind: 'asset',
      ...SLOTS.asset,
      label: pair.asset_name,
      sub: `#${pair.asset_norad} · ${pair.risk_level} · ${pair.min_distance_km.toFixed(0)} km`,
      color: KIND_COLOR.asset,
      norad: pair.asset_norad,
    })
    edges.push({ from: 'sat', to: 'asset', label: 'threatens' })
  }

  if (entry.is_anomaly || entry.is_military_detection || entry.status !== 'NOMINAL') {
    nodes.push({
      id: 'alert',
      kind: 'alert',
      ...SLOTS.alert,
      label: entry.is_military_detection ? 'MIL DETECT' : shortStatus(entry.status),
      sub: `att ${entry.attention_score.toFixed(2)} · IF ${entry.anomaly_score.toFixed(2)}`,
      color: KIND_COLOR.alert,
    })
    edges.push({ from: 'sat', to: 'alert', label: 'hasAlert' })
  }

  const ownCases = casesForNorad(cases, entry.norad_id).slice(0, 2)
  ownCases.forEach((c, i) => {
    const id = `case-${c.eventId}`
    const slot = i === 0 ? SLOTS.case0 : SLOTS.case1
    nodes.push({
      id,
      kind: 'case',
      ...slot,
      label: shortEventLabel(c.eventId),
      sub: `${c.isPlacebo ? 'placebo' : 'interest'} · ${c.hit ? 'HIT' : 'miss'}${
        c.leadDays != null ? ` · ${c.leadDays.toFixed(0)}d` : ''
      }`,
      color: c.isPlacebo ? '#64748b' : KIND_COLOR.case,
      eventId: c.eventId,
      norad: c.norad,
    })
    edges.push({ from: 'sat', to: id, label: 'validatedBy' })
  })

  const fs = entry.features_snapshot ?? {}
  const storm = (fs.geomagnetic_storm ?? 0) >= 0.5
  nodes.push({
    id: 'wx',
    kind: 'weather',
    ...SLOTS.wx,
    label: storm ? 'STORM' : 'Quiet Sun',
    sub: `F10.7 ${fs.f10_7 ?? '—'} · Ap ${fs.ap_index ?? '—'}`,
    color: KIND_COLOR.weather,
  })
  edges.push({ from: 'sat', to: 'wx', label: 'weather' })

  if (entry.evidence) {
    nodes.push({
      id: 'ev',
      kind: 'evidence',
      ...SLOTS.ev,
      label: 'DS fusion',
      sub: `Bel ${entry.evidence.belief_anomalous?.toFixed(2) ?? '—'} · K ${
        entry.evidence.conflict_K?.toFixed(2) ?? '—'
      }`,
      color: KIND_COLOR.evidence,
    })
    edges.push({ from: 'sat', to: 'ev', label: 'fusedAs' })
  }

  if (!pair && extraPairs[0]) {
    const p = extraPairs[0]
    const otherNorad = p.suspect_norad === entry.norad_id ? p.asset_norad : p.suspect_norad
    const otherName = p.suspect_norad === entry.norad_id ? p.asset_name : p.suspect_name
    nodes.push({
      id: 'asset',
      kind: 'asset',
      ...SLOTS.asset,
      label: otherName,
      sub: `#${otherNorad} · ${p.risk_level}`,
      color: KIND_COLOR.asset,
      norad: otherNorad,
    })
    edges.push({ from: 'sat', to: 'asset', label: 'threatens' })
  }

  around?.peers.forEach((peer, i) => {
    const slot = i === 0 ? SLOTS.peer0 : SLOTS.peer1
    const id = `peer-${peer.norad}`
    nodes.push({
      id,
      kind: 'peer',
      ...slot,
      label: peer.name,
      sub: `#${peer.norad}${peer.pairRisk != null ? ` · r ${peer.pairRisk.toFixed(2)}` : ''}`,
      color: KIND_COLOR.peer,
      norad: peer.norad,
    })
    edges.push({
      from: 'sat',
      to: id,
      label: entry.role === 'asset' ? 'threatenedBy' : 'sameAsset',
    })
  })

  const placebo = around?.placeboCases[0]
  if (placebo && !nodes.some((n) => n.eventId === placebo.eventId)) {
    nodes.push({
      id: `case-${placebo.eventId}`,
      kind: 'case',
      ...SLOTS.placebo,
      label: shortEventLabel(placebo.eventId),
      sub: `placebo · ${placebo.hit ? 'HIT' : 'miss'} · #${placebo.norad}`,
      color: '#64748b',
      eventId: placebo.eventId,
      norad: placebo.norad,
    })
    edges.push({ from: 'sat', to: `case-${placebo.eventId}`, label: 'samePeak' })
  }

  return { nodes, edges }
}

export function nodeHalf(kind: GraphKind): { hw: number; hh: number } {
  if (kind === 'satellite') return { hw: GRAPH_HUB_HW, hh: GRAPH_HUB_HH }
  return { hw: GRAPH_NODE_HW, hh: GRAPH_NODE_HH }
}

/** Intersection of center→target with the node's rectangle (percent space). */
export function rectEdgePoint(
  from: GraphNode,
  to: GraphNode,
): { x: number; y: number } {
  const { hw, hh } = nodeHalf(from.kind)
  const dx = to.x - from.x
  const dy = to.y - from.y
  const ax = Math.abs(dx)
  const ay = Math.abs(dy)
  if (ax < 1e-6 && ay < 1e-6) return { x: from.x, y: from.y }
  const t = Math.min(hw / (ax || 1e-6), hh / (ay || 1e-6))
  return { x: from.x + dx * t, y: from.y + dy * t }
}

export interface InvLink {
  type: string
  target: string
  label?: string
  norad?: number
  event_id?: string
}

export interface InvObject {
  id: string
  kind: string
  gotham_category?: string
  norad?: number
  label?: string
  role?: string
  status?: string
  country?: string
  orbit_class?: string
  scores?: { attention?: number | null; anomaly?: number | null; belief?: number | null }
  links?: InvLink[]
  triage?: { status?: string; updated_at?: string; operator?: string }
  t_peak?: string
}

export interface InvestigationBundle {
  schema: string
  generated_at?: string
  day?: string
  objects: InvObject[]
  object_sets?: Array<{ id: string; label?: string; ids: string[] }>
  provenance?: Record<string, unknown>
  lineage?: Record<string, unknown>
}

export function satObjectId(norad: number): string {
  return `sat:${norad}`
}

export function expandNeighbors(
  bundle: InvestigationBundle,
  startId: string,
  hops: number,
): { nodes: InvObject[]; edges: Array<{ from: string; to: string; type: string; label?: string }> } {
  const depth = Math.max(1, Math.min(3, hops))
  const byId = new Map(bundle.objects.map((o) => [o.id, o]))
  const start = byId.get(startId)
  if (!start) return { nodes: [], edges: [] }
  const seen = new Set<string>([startId])
  let frontier = [startId]
  const nodes: InvObject[] = [start]
  const edges: Array<{ from: string; to: string; type: string; label?: string }> = []
  for (let h = 0; h < depth; h++) {
    const next: string[] = []
    for (const oid of frontier) {
      const obj = byId.get(oid)
      for (const link of obj?.links ?? []) {
        if (!link.target) continue
        edges.push({
          from: oid,
          to: link.target,
          type: link.type,
          label: link.label,
        })
        if (seen.has(link.target)) continue
        seen.add(link.target)
        const tgt = byId.get(link.target)
        if (tgt) {
          nodes.push(tgt)
          next.push(link.target)
        }
      }
    }
    frontier = next
    if (!frontier.length) break
  }
  return { nodes, edges }
}

export function layoutInvGraph(
  start: InvObject,
  around: { nodes: InvObject[]; edges: Array<{ from: string; to: string; type: string; label?: string }> },
): ObjectGraph {
  const others = around.nodes.filter((n) => n.id !== start.id)
  const nodes: GraphNode[] = [
    {
      id: start.id,
      kind: kindOf(start),
      x: 50,
      y: 50,
      label: start.label || start.id,
      sub: subOf(start),
      color: KIND_COLOR[kindOf(start)],
      norad: start.norad,
    },
  ]
  const n = Math.max(1, others.length)
  others.forEach((o, i) => {
    const ang = (2 * Math.PI * i) / n - Math.PI / 2
    const r = 34
    nodes.push({
      id: o.id,
      kind: kindOf(o),
      x: 50 + r * Math.cos(ang),
      y: 50 + r * Math.sin(ang),
      label: o.label || o.id,
      sub: subOf(o),
      color: KIND_COLOR[kindOf(o)] ?? '#94a3b8',
      norad: o.norad,
      eventId: o.id.startsWith('case:') ? o.id.slice(5) : undefined,
    })
  })
  const idSet = new Set(nodes.map((x) => x.id))
  const edges: GraphEdge[] = around.edges
    .filter((e) => idSet.has(e.from) && idSet.has(e.to))
    .map((e) => ({ from: e.from, to: e.to, label: e.type }))
  return { nodes, edges }
}

function kindOf(o: InvObject): GraphKind {
  if (o.kind === 'alert') return 'alert'
  if (o.kind === 'case') return 'case'
  if (o.kind === 'weather') return 'weather'
  if (o.kind === 'evidence') return 'evidence'
  if (o.kind === 'document') return 'document'
  if (o.role === 'asset') return 'asset'
  if (o.kind === 'peer') return 'peer'
  return 'satellite'
}

function subOf(o: InvObject): string {
  const bits = [
    o.norad != null ? `#${o.norad}` : '',
    o.role || o.kind,
    o.triage?.status && o.triage.status !== 'OPEN' ? o.triage.status : '',
  ].filter(Boolean)
  return bits.join(' · ')
}

export function isTextTarget(el: EventTarget | null): boolean {
  if (!(el instanceof HTMLElement)) return false
  const tag = el.tagName
  return (
    tag === 'INPUT' ||
    tag === 'TEXTAREA' ||
    tag === 'SELECT' ||
    el.isContentEditable
  )
}

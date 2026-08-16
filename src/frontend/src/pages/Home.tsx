import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as satellite from 'satellite.js'
import { GlobeEngine } from '@/lib/globe-engine'
import { rdpIndices } from '@/lib/rdp'
import { UI_GROUPS, formatUtc } from '@/lib/satellites'
import type { SatInfo } from '@/lib/satellites'
import { useSimClock } from '@/hooks/useSimClock'
import { useTleData } from '@/hooks/useTleData'
import { usePropagator } from '@/hooks/usePropagator'
import { useRiskReport } from '@/hooks/useRiskReport'
import {
  boardByNorad,
  boardColor,
  boardThreat,
  EMPTY_FILTERS,
  filtersActive,
  matchesFilters,
  type BoardFilters,
} from '@/lib/risk-report'
import IdentityBlock from '@/components/hud/IdentityBlock'
import ClockCard from '@/components/hud/ClockCard'
import TimeController from '@/components/hud/TimeController'
import SearchBox from '@/components/hud/SearchBox'
import type { Telemetry } from '@/lib/satellites'
import FallbackTable from '@/components/FallbackTable'
import LeftDock from '@/components/dock/LeftDock'
import RightDock from '@/components/dock/RightDock'
import CatalogPanel from '@/components/hud/CatalogPanel'
import type { CatalogFocus } from '@/components/hud/CatalogPanel'
import CrossRoutePanel from '@/components/hud/CrossRoutePanel'
import type { CompareSlot } from '@/components/hud/CrossRoutePanel'
import type { PaletteAction } from '@/components/hud/CommandPalette'
import { usePaperValidation } from '@/hooks/usePaperValidation'
import { useWalkforwardIndex } from '@/hooks/useWalkforwardIndex'
import { useInvestigation } from '@/hooks/useInvestigation'
import { useOperatorHotkeys } from '@/hooks/useOperatorHotkeys'

const InvestigationCanvas = lazy(() => import('@/components/hud/InvestigationCanvas'))
const CommandPalette = lazy(() => import('@/components/hud/CommandPalette'))
import {
  analyzeOrbitCross,
  sampleOrbitRing,
  EARTH_R_KM,
  type CrossAnalysis,
} from '@/lib/orbit-crossing'

const POC_HTML = `${import.meta.env.BASE_URL}reports/walkforward_poc.html`

const POC_HASH: Record<string, string> = {
  luch1_intelsat_mid2015: '#case-luch-mid2015',
  luch1_intelsat_2015: '#case-luch-2015',
  luch1_athena_fidus_2018: '#case-athena-fidus',
  sy12_geo_rpo_2021_22: '#case-sy12',
  luch2_trailing_2023: '#case-luch2',
}

const EARTH_R = 6371
const EMPTY_SATS: SatInfo[] = []
const DEEP_LINK_SPEEDS = [-240, -60, -10, 1, 10, 60, 240]

interface HoverState {
  index: number
  x: number
  y: number
}

function detectWebGL(): boolean {
  try {
    const c = document.createElement('canvas')
    return !!(c.getContext('webgl2') || c.getContext('webgl'))
  } catch {
    return false
  }
}

function setUrlSat(norad: number | null) {
  const url = new URL(window.location.href)
  if (norad === null) url.searchParams.delete('sat')
  else url.searchParams.set('sat', String(norad))
  url.searchParams.delete('view')
  window.history.replaceState(null, '', url)
}

export default function Home() {
  const mountRef = useRef<HTMLDivElement>(null)
  const engineRef = useRef<GlobeEngine | null>(null)
  const clock = useSimClock()
  const { status, dataset, error } = useTleData()
  const {
    status: riskStatus,
    report: riskReport,
    error: riskError,
  } = useRiskReport()
  const boardMap = useMemo(() => boardByNorad(riskReport), [riskReport])

  const [webglOk] = useState(detectWebGL)
  const [ctxLost, setCtxLost] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [selectedNorad, setSelectedNorad] = useState<number | null>(null)
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null)
  const [hover, setHover] = useState<HoverState | null>(null)
  const [groupVisible, setGroupVisible] = useState<boolean[]>(() =>
    UI_GROUPS.map(() => true),
  )
  const [showOrbit, setShowOrbit] = useState(true)
  const [showFoot, setShowFoot] = useState(true)
  const [follow, setFollow] = useState(false)
  const [fps, setFps] = useState(0)
  const [leftOpen, setLeftOpen] = useState(true)
  const [rightOpen, setRightOpen] = useState(false)
  const [catalogOpen, setCatalogOpen] = useState(false)
  const [catalogFocus, setCatalogFocus] = useState<CatalogFocus>('all')
  const [boardFilters, setBoardFilters] = useState<BoardFilters>(EMPTY_FILTERS)
  const [graphOpen, setGraphOpen] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const paperClaims = usePaperValidation()
  const wfCases = useWalkforwardIndex()
  const investigation = useInvestigation()

  // Dual-route compare
  const [compareOn, setCompareOn] = useState(false)
  const [pickSlot, setPickSlot] = useState<CompareSlot>('A')
  const [compareNoradA, setCompareNoradA] = useState<number | null>(null)
  const [compareNoradB, setCompareNoradB] = useState<number | null>(null)
  const [crossAnalysis, setCrossAnalysis] = useState<CrossAnalysis | null>(null)
  const [crossComputing, setCrossComputing] = useState(false)

  const satsRef = useRef<SatInfo[]>(EMPTY_SATS)
  const noradMapRef = useRef(new Map<number, number>())
  const recCache = useRef(new Map<number, satellite.SatRec>())
  const groupVisibleRef = useRef(groupVisible)
  const selectedNoradRef = useRef<number | null>(null)
  const compareOnRef = useRef(compareOn)
  const pickSlotRef = useRef(pickSlot)
  const urlInitRef = useRef(false)

  // Sync ref mirrors via effects (react-hooks/refs: no writes during render).
  useEffect(() => {
    groupVisibleRef.current = groupVisible
  }, [groupVisible])
  useEffect(() => {
    selectedNoradRef.current = selectedNorad
  }, [selectedNorad])
  useEffect(() => {
    compareOnRef.current = compareOn
  }, [compareOn])
  useEffect(() => {
    pickSlotRef.current = pickSlot
  }, [pickSlot])

  const sats = dataset?.sats ?? EMPTY_SATS

  // norad -> dataset index, derived during render (memoized) so render-time
  // lookups (compare selection, tooltip) never touch the ref.
  const noradMap = useMemo(() => {
    const m = new Map<number, number>()
    sats.forEach((s, i) => m.set(s.norad, i))
    return m
  }, [sats])

  const getRec = useCallback((index: number): satellite.SatRec | null => {
    const cached = recCache.current.get(index)
    if (cached) return cached
    const s = satsRef.current[index]
    if (!s) return null
    try {
      const rec = satellite.twoline2satrec(s.l1, s.l2)
      recCache.current.set(index, rec)
      return rec
    } catch {
      return null
    }
  }, [])

  // ---- direct SGP4 providers for the selected satellite (exact sim time) ----
  const orbitProvider = useCallback(
    (index: number, simMs: number, past: Float32Array, future: Float32Array) => {
      const rec = getRec(index)
      if (!rec) return 0
      const periodMs = ((2 * Math.PI) / rec.no) * 60 * 1000
      const n = past.length / 3
      const fill = (out: Float32Array, startMs: number, endMs: number): number => {
        // RDP decimation (patent 12,450,265 trajectory compression): propagate
        // the full ring, then keep only shape-defining points (~30% of SGP4
        // calls on the main thread) and write the kept subset.
        const raw: Array<{ x: number; y: number; z: number }> = []
        let lx = 0
        let ly = 0
        let lz = 0
        for (let i = 0; i < n; i++) {
          const t = startMs + ((endMs - startMs) * i) / (n - 1)
          try {
            const pv = satellite.propagate(rec, new Date(t))
            const p = pv?.position
            if (p && isFinite(p.x)) {
              lx = p.x / EARTH_R
              ly = p.y / EARTH_R
              lz = p.z / EARTH_R
            }
          } catch {
            /* keep last */
          }
          raw.push({ x: lx, y: ly, z: lz })
        }
        const kept = rdpIndices(raw, 0.01)
        for (let j = 0; j < kept.length; j++) {
          const p = raw[kept[j]]
          out.set([p.x, p.y, p.z], j * 3)
        }
        return kept.length
      }
      const usedPast = fill(past, simMs - periodMs / 2, simMs)
      const usedFuture = fill(future, simMs, simMs + periodMs / 2)
      return Math.max(usedPast, usedFuture)
    },
    [getRec],
  )

  const footprintProvider = useCallback(
    (index: number, simMs: number) => {
      const rec = getRec(index)
      if (!rec) return null
      try {
        const pv = satellite.propagate(rec, new Date(simMs))
        const p = pv?.position
        if (!p || !isFinite(p.x)) return null
        const r = Math.sqrt(p.x * p.x + p.y * p.y + p.z * p.z)
        if (r - EARTH_R < 50) return null
        return { x: p.x / r, y: p.y / r, z: p.z / r, ang: Math.acos(EARTH_R / r) }
      } catch {
        return null
      }
    },
    [getRec],
  )

  const ensureGroupVisible = useCallback((group: number) => {
    if (!groupVisibleRef.current[group]) {
      setGroupVisible((prev) => {
        const next = [...prev]
        next[group] = true
        return next
      })
      engineRef.current?.setGroupVisible(group, true)
    }
  }, [])

  // ---- selection (NORAD-stable) ----
  const selectSat = useCallback(
    (index: number | null) => {
      // In compare mode, globe/search picks fill A/B slots first
      if (compareOnRef.current && index !== null) {
        const s = satsRef.current[index]
        if (!s) return
        ensureGroupVisible(s.group)
        if (pickSlotRef.current === 'A') {
          setCompareNoradA(s.norad)
          setPickSlot('B')
        } else {
          setCompareNoradB(s.norad)
        }
        setSelectedIndex(index)
        setSelectedNorad(s.norad)
        {
          const entry = boardMap.get(s.norad)
          const selColor = entry ? boardColor(entry) : UI_GROUPS[s.group]?.color
          engineRef.current?.setSelected(index, selColor)
        }
        setUrlSat(s.norad)
        setRightOpen(true)
        return
      }

      if (index === null) {
        setSelectedIndex(null)
        setSelectedNorad(null)
        engineRef.current?.setSelected(null)
        setUrlSat(null)
        return
      }
      const s = satsRef.current[index]
      if (!s) return
      ensureGroupVisible(s.group)
      setSelectedIndex(index)
      setSelectedNorad(s.norad)
      {
        const entry = boardMap.get(s.norad)
        const selColor = entry ? boardColor(entry) : UI_GROUPS[s.group]?.color
        engineRef.current?.setSelected(index, selColor)
      }
      setUrlSat(s.norad)
    },
    [ensureGroupVisible, boardMap],
  )

  // ---- engine lifecycle (created once) ----
  useEffect(() => {
    if (!webglOk || !mountRef.current) return
    let engine: GlobeEngine | null = null
    let failTimer: number | undefined = undefined
    try {
      engine = new GlobeEngine(mountRef.current, {
        getSimTime: clock.getTime,
        onSelect: (idx) => selectSat(idx),
        onHover: (idx, x, y) =>
          setHover(idx !== null ? { index: idx, x, y } : null),
        onContextLost: () => setCtxLost(true),
        onContextRestored: () => setCtxLost(false),
        onFps: (v) => setFps(v),
        orbitProvider,
        footprintProvider,
      })
      engineRef.current = engine
    } catch (err) {
      console.error('GlobeEngine init failed', err)
      failTimer = window.setTimeout(() => setCtxLost(true), 0)
    }
    return () => {
      if (failTimer !== undefined) clearTimeout(failTimer)
      engine?.dispose()
      engineRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [webglOk])

  // ---- dataset -> engine (hot swap; preserves UI state) ----
  useEffect(() => {
    if (!dataset) return
    satsRef.current = dataset.sats
    recCache.current.clear()
    const map = new Map<number, number>()
    dataset.sats.forEach((s, i) => map.set(s.norad, i))
    noradMapRef.current = map

    engineRef.current?.buildSatellites(
      UI_GROUPS.map((g, i) => ({
        color: g.color,
        size: g.size,
        count: dataset.counts[i],
      })),
    )
    groupVisibleRef.current.forEach((v, i) =>
      engineRef.current?.setGroupVisible(i, v),
    )

    // re-resolve selection by NORAD identity
    const norad = selectedNoradRef.current
    if (norad !== null) {
      const idx = map.get(norad)
      if (idx === undefined) {
        setSelectedIndex(null)
        setSelectedNorad(null)
        engineRef.current?.setSelected(null)
        setUrlSat(null)
      } else {
        setSelectedIndex(idx)
        const entry = boardMap.get(norad)
        const selColor = entry
          ? boardColor(entry)
          : UI_GROUPS[dataset.sats[idx].group]?.color
        engineRef.current?.setSelected(idx, selColor)
      }
    }

    // initial deep link ?sat=25544&speed=60
    if (!urlInitRef.current) {
      urlInitRef.current = true
      const params = new URLSearchParams(window.location.search)
      const sp = parseInt(params.get('speed') ?? '', 10)
      if (DEEP_LINK_SPEEDS.includes(sp)) clock.setSpeed(sp)
      const p = params.get('sat')
      if (p) {
        const idx = map.get(parseInt(p, 10))
        if (idx !== undefined) selectSat(idx)
      }
      // Never auto-open investigation / PoC on boot — even if a leftover
      // ?view=graph is in the address bar.
      if (params.has('view')) {
        const clean = new URL(window.location.href)
        clean.searchParams.delete('view')
        window.history.replaceState(null, '', clean)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataset])

  // Paint watchlist sats + optional focus filter (watchlist / military only)
  useEffect(() => {
    if (!dataset) return
    const colors = new Map<number, string>()
    const sizes = new Map<number, number>()

    const focusNorads = new Set<number>()
    if (riskReport) {
      for (const b of riskReport.board) {
        if (catalogFocus === 'military') {
          if (b.role === 'asset' || b.role === 'suspect') focusNorads.add(b.norad_id)
        } else if (catalogFocus === 'watchlist') {
          focusNorads.add(b.norad_id)
        }
      }
    }

    // Hide non-focus sats when not "all"
    if (catalogFocus !== 'all' && focusNorads.size > 0) {
      dataset.sats.forEach((s, i) => {
        if (!focusNorads.has(s.norad)) sizes.set(i, 0)
      })
    }

    // Ontology cross-filters: dim watchlist objects that do not match
    const filterActive = filtersActive(boardFilters)
    const matchingNorads = new Set<number>()
    if (filterActive && riskReport) {
      for (const b of riskReport.board) {
        if (matchesFilters(b, boardFilters)) matchingNorads.add(b.norad_id)
      }
    }

    if (riskReport) {
      for (const b of riskReport.board) {
        if (catalogFocus === 'military' && b.role !== 'asset' && b.role !== 'suspect') {
          continue
        }
        if (filterActive && !matchingNorads.has(b.norad_id)) {
          // non-matching: de-emphasize on the globe (size 0, no threat color)
          const idxD = noradMapRef.current.get(b.norad_id)
          if (idxD !== undefined) sizes.set(idxD, 0)
          continue
        }
        const idx = noradMapRef.current.get(b.norad_id)
        if (idx === undefined) continue
        colors.set(idx, boardColor(b))
        const threat = boardThreat(b)
        const boost =
          threat === 'HOSTILE'
            ? 3.4
            : threat === 'SUSPECT'
              ? 2.8
              : threat === 'ANOMALY'
                ? 2.4
                : 2.0
        sizes.set(idx, boost)
      }
    }

    const apply = () => engineRef.current?.applyIndexColors(colors, sizes)
    apply()
    const t = window.setTimeout(apply, 400)
    const t2 = window.setTimeout(apply, 1200)
    return () => {
      clearTimeout(t)
      clearTimeout(t2)
    }
  }, [dataset, riskReport, catalogFocus, boardFilters])

  const { degraded } = usePropagator(dataset, engineRef, clock)

  // ---- telemetry for the selected satellite (direct SGP4 at exact sim time) ----
  useEffect(() => {
    if (selectedIndex === null) {
      const id = window.setTimeout(() => setTelemetry(null), 0)
      return () => clearTimeout(id)
    }
    const update = () => {
      const rec = getRec(selectedIndex)
      if (!rec) return
      try {
        const simMs = clock.getTime()
        const pv = satellite.propagate(rec, new Date(simMs))
        const p = pv?.position
        const v = pv?.velocity
        if (!p || !v || !isFinite(p.x)) return
        const gmst = satellite.gstime(new Date(simMs))
        const geo = satellite.eciToGeodetic(p, gmst)
        setTelemetry({
          lat: satellite.degreesLat(geo.latitude),
          lon: satellite.degreesLong(geo.longitude),
          alt: geo.height,
          speed: Math.sqrt(v.x * v.x + v.y * v.y + v.z * v.z),
          period: (2 * Math.PI) / rec.no,
          incl: (rec.inclo * 180) / Math.PI,
        })
      } catch {
        /* decayed */
      }
    }
    update()
    const id = setInterval(update, 250)
    return () => clearInterval(id)
  }, [selectedIndex, getRec, clock])

  // ---- engine-side option sync ----
  useEffect(() => {
    engineRef.current?.setShowOrbit(showOrbit)
  }, [showOrbit])
  useEffect(() => {
    engineRef.current?.setShowFootprint(showFoot)
  }, [showFoot])
  useEffect(() => {
    engineRef.current?.setFollow(follow)
  }, [follow])

  const openPoc = useCallback((eventId?: string) => {
    const hash = eventId ? (POC_HASH[eventId] ?? '#cases') : ''
    window.open(`${POC_HTML}${hash}`, '_blank', 'noopener,noreferrer')
  }, [])

  const openGraph = useCallback(() => {
    setGraphOpen(true)
    setCatalogOpen(false)
  }, [])

  const investigateNorad = useCallback(
    (norad: number) => {
      const idx = noradMapRef.current.get(norad)
      if (idx !== undefined) selectSat(idx)
      else setUrlSat(norad)
      setRightOpen(true)
      openGraph()
    },
    [selectSat, openGraph],
  )

  useOperatorHotkeys({
    selectSat,
    graphOpen,
    setGraphOpen,
    catalogOpen,
    setCatalogOpen,
    paletteOpen,
    setPaletteOpen,
    setLeftOpen,
    setRightOpen,
    openPoc,
  })

  const toggleGroup = (i: number) => {
    setGroupVisible((prev) => {
      const next = prev.map((v, j) => (j === i ? !v : v))
      engineRef.current?.setGroupVisible(i, next[i])
      return next
    })
  }

  /** Select by NORAD (threat board / deep link). Opens right dock. */
  const selectByNorad = useCallback(
    (norad: number) => {
      const idx = noradMapRef.current.get(norad)
      if (idx !== undefined) {
        selectSat(idx)
        setRightOpen(true)
        return
      }
      setUrlSat(norad)
      setRightOpen(true)
    },
    [selectSat],
  )

  const satA = compareNoradA !== null ? (sats[noradMap.get(compareNoradA) ?? -1] ?? null) : null
  const satB = compareNoradB !== null ? (sats[noradMap.get(compareNoradB) ?? -1] ?? null) : null
  const idxA = compareNoradA !== null ? (noradMap.get(compareNoradA) ?? null) : null
  const idxB = compareNoradB !== null ? (noradMap.get(compareNoradB) ?? null) : null

  const applyCrossToEngine = useCallback(
    (result: CrossAnalysis, liveA: number | null, liveB: number | null) => {
      const markers: number[] = []
      let link: Float32Array | null = null

      if (result.geometry) {
        const g = result.geometry
        markers.push(
          g.pointA.x / EARTH_R_KM,
          g.pointA.y / EARTH_R_KM,
          g.pointA.z / EARTH_R_KM,
          g.pointB.x / EARTH_R_KM,
          g.pointB.y / EARTH_R_KM,
          g.pointB.z / EARTH_R_KM,
          g.mid.x,
          g.mid.y,
          g.mid.z,
        )
        link = new Float32Array([
          g.pointA.x / EARTH_R_KM,
          g.pointA.y / EARTH_R_KM,
          g.pointA.z / EARTH_R_KM,
          g.pointB.x / EARTH_R_KM,
          g.pointB.y / EARTH_R_KM,
          g.pointB.z / EARTH_R_KM,
        ])
      }
      if (result.temporal) {
        const t = result.temporal
        markers.push(t.mid.x, t.mid.y, t.mid.z)
        markers.push(
          t.pointA.x / EARTH_R_KM,
          t.pointA.y / EARTH_R_KM,
          t.pointA.z / EARTH_R_KM,
          t.pointB.x / EARTH_R_KM,
          t.pointB.y / EARTH_R_KM,
          t.pointB.z / EARTH_R_KM,
        )
      }

      engineRef.current?.setCompareRoutes(
        result.ringA,
        result.ringB,
        markers.length ? new Float32Array(markers) : null,
        link,
        liveA,
        liveB,
      )
    },
    [],
  )

  // Draw single orbit while only one slot filled
  useEffect(() => {
    if (!compareOn) {
      const id = window.setTimeout(() => setCrossAnalysis(null), 0)
      engineRef.current?.clearCompareRoutes()
      return () => clearTimeout(id)
    }
    if (compareNoradA === null && compareNoradB === null) {
      const id = window.setTimeout(() => setCrossAnalysis(null), 0)
      engineRef.current?.clearCompareRoutes()
      return () => clearTimeout(id)
    }
    // Wait for both before full analysis; show single ring if only one
    if (compareNoradA === null || compareNoradB === null) {
      const id = window.setTimeout(() => setCrossAnalysis(null), 0)
      const onlyIdx = idxA ?? idxB
      const rec = onlyIdx !== null ? getRec(onlyIdx) : null
      if (!rec) {
        engineRef.current?.clearCompareRoutes()
        return () => clearTimeout(id)
      }
      const ring = sampleOrbitRing(rec, clock.getTime(), 120)
      engineRef.current?.setCompareRoutes(
        idxA !== null ? ring : null,
        idxB !== null ? ring : null,
        null,
        null,
        idxA,
        idxB,
      )
      return () => clearTimeout(id)
    }
    if (compareNoradA === compareNoradB) {
      const id = window.setTimeout(() => setCrossAnalysis(null), 0)
      engineRef.current?.clearCompareRoutes()
      return () => clearTimeout(id)
    }

    const recA = idxA !== null ? getRec(idxA) : null
    const recB = idxB !== null ? getRec(idxB) : null
    if (!recA || !recB) {
      const id = window.setTimeout(() => setCrossAnalysis(null), 0)
      engineRef.current?.clearCompareRoutes()
      return () => clearTimeout(id)
    }

    let cancelled = false
    const computingTimer = window.setTimeout(() => setCrossComputing(true), 0)

    const handle = window.setTimeout(() => {
      const result = analyzeOrbitCross(recA, recB, clock.getTime())
      if (cancelled) return
      setCrossAnalysis(result)
      setCrossComputing(false)
      if (!result) {
        engineRef.current?.clearCompareRoutes()
        return
      }
      applyCrossToEngine(result, idxA, idxB)
    }, 30)

    return () => {
      cancelled = true
      clearTimeout(handle)
      clearTimeout(computingTimer)
    }
  }, [
    compareOn,
    compareNoradA,
    compareNoradB,
    idxA,
    idxB,
    getRec,
    dataset,
    clock,
    applyCrossToEngine,
  ])

  // Refresh dual analysis periodically (sim clock / TLE age)
  useEffect(() => {
    if (!compareOn || compareNoradA === null || compareNoradB === null) return
    if (compareNoradA === compareNoradB) return
    const id = window.setInterval(() => {
      const recA = idxA !== null ? getRec(idxA) : null
      const recB = idxB !== null ? getRec(idxB) : null
      if (!recA || !recB) return
      const result = analyzeOrbitCross(recA, recB, clock.getTime())
      if (!result) return
      setCrossAnalysis(result)
      applyCrossToEngine(result, idxA, idxB)
    }, 15_000)
    return () => clearInterval(id)
  }, [
    compareOn,
    compareNoradA,
    compareNoradB,
    idxA,
    idxB,
    getRec,
    clock,
    applyCrossToEngine,
  ])

  const clearCompareSlot = useCallback((slot: CompareSlot) => {
    if (slot === 'A') setCompareNoradA(null)
    else setCompareNoradB(null)
  }, [])

  const clearCompareAll = useCallback(() => {
    setCompareNoradA(null)
    setCompareNoradB(null)
    setCrossAnalysis(null)
    engineRef.current?.clearCompareRoutes()
    setPickSlot('A')
  }, [])

  const toggleCompare = useCallback(
    (on: boolean) => {
      setCompareOn(on)
      if (!on) {
        clearCompareAll()
      } else {
        setPickSlot('A')
        setLeftOpen(true)
      }
    },
    [clearCompareAll],
  )

  const useSelectedAs = useCallback(
    (slot: CompareSlot) => {
      if (selectedNorad === null) return
      if (slot === 'A') setCompareNoradA(selectedNorad)
      else setCompareNoradB(selectedNorad)
      setPickSlot(slot === 'A' ? 'B' : 'A')
    },
    [selectedNorad],
  )

  const selSat =
    selectedIndex !== null && selectedIndex < sats.length ? sats[selectedIndex] : null
  const selBoard =
    selectedNorad !== null ? (boardMap.get(selectedNorad) ?? null) : null

  const paletteActions = useMemo<PaletteAction[]>(
    () => [
      {
        id: 'act-graph',
        group: 'action',
        label: 'Investigate selected (object graph)',
        hint: 'G · ontology links + quant fingerprint',
        run: () => {
          if (selectedNorad != null) investigateNorad(selectedNorad)
          else openGraph()
        },
      },
      {
        id: 'act-poc',
        group: 'action',
        label: 'Open walk-forward proof (Claims A+B)',
        hint: 'P · new tab · GEO 5/5 vs EO 0/7',
        run: () => openPoc(),
      },
      {
        id: 'act-compare',
        group: 'action',
        label: compareOn ? 'Close conjunction lab' : 'Open conjunction lab',
        hint: 'two-orbit TCA',
        run: () => toggleCompare(!compareOn),
      },
      {
        id: 'act-catalog-wl',
        group: 'action',
        label: 'Globe focus · watchlist',
        run: () => {
          setCatalogFocus('watchlist')
          setCatalogOpen(true)
        },
      },
      {
        id: 'act-catalog-mil',
        group: 'action',
        label: 'Globe focus · military',
        run: () => {
          setCatalogFocus('military')
          setCatalogOpen(true)
        },
      },
      {
        id: 'flt-suspect',
        group: 'filter',
        label: 'Filter · role suspect',
        run: () => setBoardFilters((f) => ({ ...f, roles: ['suspect'] })),
      },
      {
        id: 'flt-asset',
        group: 'filter',
        label: 'Filter · role asset',
        run: () => setBoardFilters((f) => ({ ...f, roles: ['asset'] })),
      },
      {
        id: 'flt-cn',
        group: 'filter',
        label: 'Filter · country CN',
        run: () => setBoardFilters((f) => ({ ...f, countries: ['CN'] })),
      },
      {
        id: 'flt-ru',
        group: 'filter',
        label: 'Filter · country RU',
        run: () => setBoardFilters((f) => ({ ...f, countries: ['RU'] })),
      },
      {
        id: 'flt-geo',
        group: 'filter',
        label: 'Filter · orbit GEO',
        run: () => setBoardFilters((f) => ({ ...f, orbits: ['GEO'] })),
      },
      {
        id: 'flt-clear',
        group: 'filter',
        label: 'Clear all cross-filters',
        run: () => setBoardFilters(EMPTY_FILTERS),
      },
    ],
    [selectedNorad, investigateNorad, openPoc, openGraph, compareOn, toggleCompare],
  )

  // Auto-open right dock when a sat is selected
  useEffect(() => {
    if (selSat) {
      const id = window.setTimeout(() => setRightOpen(true), 0)
      return () => clearTimeout(id)
    }
  }, [selSat])

  // tooltip stays inside the viewport
  const tooltipPos = hover
    ? {
        left: Math.min(hover.x + 14, window.innerWidth - 190),
        top: Math.min(hover.y + 14, window.innerHeight - 44),
      }
    : null
  const hoverSat = hover ? sats[hover.index] : null

  if (!webglOk) {
    return (
      <div className="athena-space-bg h-full w-full overflow-y-auto">
        <FallbackTable dataset={dataset} />
      </div>
    )
  }

  return (
    <div className="relative h-full w-full overflow-hidden bg-black text-zinc-200">
      {/* Full-bleed globe — product hero */}
      <div ref={mountRef} className="absolute inset-0" />

      {/* Soft vignette so chrome text stays readable over bright earth */}
      <div
        className="pointer-events-none absolute inset-0 z-[1]"
        style={{
          background:
            'radial-gradient(ellipse 80% 70% at 50% 50%, transparent 50%, rgba(0,0,0,0.22) 100%)',
        }}
      />

      {/* hover tooltip */}
      {hover && tooltipPos && hoverSat && (
        <div
          className="pointer-events-none fixed z-30 flex max-w-[240px] items-center gap-1.5 truncate border border-white/15 bg-black/90 px-2.5 py-1"
          style={tooltipPos}
        >
          <span
            className="h-[6px] w-[6px] shrink-0"
            style={{
              background: boardMap.has(hoverSat.norad)
                ? boardColor(boardMap.get(hoverSat.norad)!)
                : UI_GROUPS[hoverSat.group]?.color,
            }}
          />
          <span className="truncate text-[14px] text-zinc-100">
            {hoverSat.name}
            {boardMap.has(hoverSat.norad) && (
              <span className="text-zinc-400">
                {' '}
                · {boardThreat(boardMap.get(hoverSat.norad)!)}
              </span>
            )}
          </span>
        </div>
      )}

      {/* ── Command strip (two rows: identity / tools — never stacked over docks) ── */}
      <div className="pointer-events-none absolute inset-x-0 top-0 z-20">
        <div className="flex items-start justify-between gap-2 p-2.5 pb-1.5 md:p-3 md:pb-1.5">
          <div className="pointer-events-auto flex min-w-0 flex-wrap items-start gap-2">
            <IdentityBlock
              total={dataset?.total ?? 0}
              mlDay={riskReport?.day ?? null}
              watchlistN={riskReport?.summary.n_scored ?? null}
              claims={paperClaims}
              onOpenProof={() => openPoc()}
            />
          </div>
          <div className="pointer-events-auto hidden shrink-0 md:block">
            <ClockCard clock={clock} />
          </div>
          <div className="pointer-events-auto hidden w-[min(320px,42vw)] items-center gap-2 md:flex">
            <div className="min-w-0 flex-1">
              <SearchBox sats={sats} onSelect={selectSat} />
            </div>
            <button
              type="button"
              onClick={() => setRightOpen((v) => !v)}
              className="athena-btn hidden shrink-0 px-2.5 py-1.5 text-[13px] md:inline-flex"
              title="Toggle track intel"
            >
              {rightOpen ? 'Intel ⟩' : '⟨ Intel'}
            </button>
          </div>
        </div>
        <div className="pointer-events-auto hidden w-fit max-w-[calc(100%-1.25rem)] flex-wrap items-center gap-1.5 bg-black/55 px-2.5 py-1.5 md:inline-flex md:px-3">
          <button
            type="button"
            onClick={() => setLeftOpen((v) => !v)}
            className="athena-btn hidden px-2.5 py-1.5 text-[13px] md:inline-flex"
            title="Toggle mission board"
          >
            {leftOpen ? '⟨ Board' : 'Board ⟩'}
          </button>
          <button
            type="button"
            onClick={() => setCatalogOpen((v) => !v)}
            className={`px-2.5 py-1.5 text-[13px] ${
              catalogOpen || catalogFocus !== 'all'
                ? 'athena-btn athena-btn-active'
                : 'athena-btn'
            }`}
            title="Catalog layers and watchlist / military focus"
          >
            Catalog{catalogFocus !== 'all' ? ' ·' : ''}
            {catalogFocus === 'watchlist'
              ? ' WL'
              : catalogFocus === 'military'
                ? ' MIL'
                : ''}
          </button>
          <button
            type="button"
            onClick={() => toggleCompare(!compareOn)}
            className={`px-2.5 py-1.5 text-[13px] ${
              compareOn ? 'athena-btn athena-btn-warn' : 'athena-btn'
            }`}
            title="Conjunction lab — two-orbit compare"
          >
            Conj {compareOn ? 'ON' : ''}
          </button>
          <button
            type="button"
            onClick={() => (graphOpen ? setGraphOpen(false) : openGraph())}
            className={`px-2.5 py-1.5 text-[13px] ${
              graphOpen ? 'athena-btn athena-btn-active' : 'athena-btn'
            }`}
            title="Object-graph investigation (G)"
          >
            Graph {graphOpen ? 'ON' : ''}
          </button>
          <button
            type="button"
            onClick={() => openPoc()}
            className="athena-btn px-2.5 py-1.5 text-[13px]"
            title="Walk-forward proof — opens in a new tab (P)"
          >
            PoC ↗
          </button>
          {dataset?.epochMs ? (
            <span className="border border-white/10 bg-black/50 px-2 py-1 text-[11px] uppercase tracking-wider text-zinc-500">
              TLE {formatUtc(dataset.epochMs)}
            </span>
          ) : null}
          {riskReport ? (
            <span className="border border-emerald-400/20 bg-black/50 px-2 py-1 text-[11px] uppercase tracking-wider text-emerald-300/80">
              report {riskReport.day}
              {riskReport.generated_at ? ` · ${riskReport.generated_at.slice(11, 16)}Z` : ''}
            </span>
          ) : null}
        </div>
      </div>

      {/* Mobile dock toggles */}
      <div className="absolute bottom-[88px] left-3 z-20 flex gap-2 md:hidden">
        <button
          type="button"
          onClick={() => setLeftOpen((v) => !v)}
          className="athena-btn px-3 py-2 text-[13px]"
        >
          Board
        </button>
        <button
          type="button"
          onClick={() => setCatalogOpen((v) => !v)}
          className={`athena-btn px-3 py-2 text-[13px] ${
            catalogFocus !== 'all' ? 'athena-btn-active' : ''
          }`}
        >
          Catalog
        </button>
        <button
          type="button"
          onClick={() => setRightOpen((v) => !v)}
          className="athena-btn px-3 py-2 text-[13px]"
        >
          Intel
        </button>
        <button
          type="button"
          onClick={() => (graphOpen ? setGraphOpen(false) : openGraph())}
          className={`athena-btn px-3 py-2 text-[13px] ${
            graphOpen ? 'athena-btn-active' : ''
          }`}
        >
          Graph
        </button>
        <button
          type="button"
          onClick={() => openPoc()}
          className="athena-btn px-3 py-2 text-[13px]"
        >
          PoC ↗
        </button>
      </div>

      <Suspense fallback={null}>
        <CommandPalette
          open={paletteOpen}
          onClose={() => setPaletteOpen(false)}
          board={riskReport?.board ?? []}
          onSelectNorad={(norad) => {
            investigateNorad(norad)
          }}
          actions={paletteActions}
        />
      </Suspense>

      {/* Floating catalog (layers + focus) — not buried under board scroll */}
      <div
        className={`absolute bottom-[78px] left-3 z-30 transition-opacity duration-200 md:left-4 ${
          catalogOpen
            ? 'pointer-events-auto opacity-100'
            : 'pointer-events-none opacity-0'
        } ${leftOpen ? 'md:left-[calc(1rem+340px+0.75rem)]' : ''}`}
      >
        <CatalogPanel
          open={catalogOpen}
          onClose={() => setCatalogOpen(false)}
          counts={dataset?.counts ?? UI_GROUPS.map(() => 0)}
          groupVisible={groupVisible}
          onToggleGroup={toggleGroup}
          focus={catalogFocus}
          onFocusChange={setCatalogFocus}
          watchlistN={riskReport?.summary.n_scored ?? boardMap.size}
          militaryN={
            riskReport
              ? riskReport.board.filter(
                  (b) => b.role === 'asset' || b.role === 'suspect',
                ).length
              : 0
          }
        />
      </div>

      {/* ── Left dock ── */}
      <div
        className={`absolute bottom-[78px] left-3 top-[132px] z-20 w-[min(340px,calc(100vw-1.5rem))] transition-transform duration-300 ease-out md:left-4 md:top-[212px] md:w-[340px] ${
          leftOpen
            ? 'translate-x-0'
            : 'pointer-events-none -translate-x-[110%]'
        }`}
      >
        <LeftDock
          selectedNorad={selectedNorad}
          onSelectNorad={selectByNorad}
          report={riskReport}
          reportStatus={riskStatus}
          reportError={riskError}
          filters={boardFilters}
          onFiltersChange={setBoardFilters}
          onInvestigate={investigateNorad}
          extra={
            compareOn ? (
              <CrossRoutePanel
                enabled={compareOn}
                onToggle={toggleCompare}
                pickSlot={pickSlot}
                onPickSlot={setPickSlot}
                satA={satA}
                satB={satB}
                onClearSlot={clearCompareSlot}
                onClearAll={clearCompareAll}
                onUseSelectedAs={useSelectedAs}
                hasPrimarySelection={selectedNorad !== null}
                analysis={crossAnalysis}
                nowMs={clock.getTime()}
                computing={crossComputing}
              />
            ) : null
          }
        />
      </div>

      {/* ── Right dock ── */}
      <div
        className={`absolute bottom-[78px] right-3 top-[132px] z-20 w-[min(360px,calc(100vw-1.5rem))] transition-transform duration-300 ease-out md:right-4 md:top-[212px] md:w-[360px] ${
          rightOpen
            ? 'translate-x-0'
            : 'pointer-events-none translate-x-[110%]'
        }`}
      >
        <RightDock
          sat={selSat}
          boardEntry={selBoard}
          telemetry={telemetry}
          showOrbit={showOrbit}
          showFoot={showFoot}
          follow={follow}
          onToggleOrbit={() => setShowOrbit((v) => !v)}
          onToggleFoot={() => setShowFoot((v) => !v)}
          onToggleFollow={() => setFollow((v) => !v)}
          onClose={() => selectSat(null)}
          totalTracked={dataset?.total ?? 0}
          fps={fps}
          reportDay={riskReport?.day ?? null}
        />
      </div>

      {/* Time controller — bottom center, between docks */}
      <div className="absolute bottom-4 left-1/2 z-20 -translate-x-1/2 pb-[env(safe-area-inset-bottom)]">
        <TimeController clock={clock} />
      </div>

      <div
        className={`absolute z-[28] transition-opacity duration-200 ${
          graphOpen
            ? 'pointer-events-auto opacity-100'
            : 'pointer-events-none opacity-0'
        } bottom-[78px] left-3 right-3 top-[132px] md:top-[212px] ${
          leftOpen ? 'md:left-[calc(1rem+340px+0.75rem)]' : 'md:left-4'
        } ${rightOpen ? 'md:right-[calc(1rem+360px+0.75rem)]' : 'md:right-4'}`}
      >
        <Suspense fallback={null}>
          <InvestigationCanvas
            open={graphOpen}
            onClose={() => setGraphOpen(false)}
            entry={selBoard}
            report={riskReport}
            cases={wfCases}
            onSelectNorad={selectByNorad}
            onOpenCase={(eventId) => openPoc(eventId)}
            investigation={investigation}
          />
        </Suspense>
      </div>

      <div className="pointer-events-none absolute bottom-1 left-1/2 z-10 hidden -translate-x-1/2 text-[13px] tracking-wider text-zinc-500 md:block">
        ATHENA-SDA · Ctrl+K · G investigate · / search
        {riskReport ? ` · ${riskReport.day}` : ''}
      </div>

      {degraded && (
        <div className="absolute bottom-[92px] left-1/2 z-20 -translate-x-1/2 border border-amber-400/40 bg-black/90 px-3 py-1.5 text-[14px] text-amber-200">
          Live propagation degraded: {degraded}
        </div>
      )}

      {ctxLost && (
        <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/95">
          <div className="athena-panel px-6 py-5 text-center">
            <div className="text-sm text-zinc-200">Graphics context lost</div>
            <button
              onClick={() => window.location.reload()}
              className="athena-btn athena-btn-active mt-3 px-3 py-1 text-sm"
            >
              Reload
            </button>
          </div>
        </div>
      )}

      {status === 'loading' && (
        <div className="athena-space-bg absolute inset-0 z-40 flex flex-col items-center justify-center">
          <div className="text-xl font-semibold tracking-[0.24em] text-zinc-50">
            ATHENA<span className="text-emerald-400">-SDA</span>
          </div>
          <div className="mt-2 text-[13px] uppercase tracking-[0.3em] text-zinc-400">
            Space Domain Awareness
          </div>
          <div className="mt-8 h-7 w-7 animate-spin rounded-full border-2 border-emerald-400/20 border-t-emerald-400" />
          <div className="mt-4 text-sm text-zinc-400">Ingesting live orbital elements…</div>
        </div>
      )}

      {status === 'error' && !dataset && (
        <div className="athena-space-bg absolute inset-0 z-40 flex flex-col items-center justify-center">
          <div className="text-xl font-semibold tracking-[0.24em] text-zinc-50">
            ATHENA<span className="text-emerald-400">-SDA</span>
          </div>
          <div className="mt-6 max-w-sm text-center text-sm text-rose-300">
            Failed to load orbital data{error ? `: ${error}` : '.'}
          </div>
          <button
            onClick={() => window.location.reload()}
            className="athena-btn mt-4 border-rose-400/40 px-3 py-1 text-sm text-rose-200"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  )
}

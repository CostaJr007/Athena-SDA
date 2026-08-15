import { useEffect, useState } from 'react'
import EventReplayPanel from '@/components/hud/EventReplayPanel'

type PocTab = 'overview' | 'method' | 'math' | 'cases' | 'placebos' | 'replay'

interface WalkforwardPocPanelProps {
  open: boolean
  onClose: () => void
  /** When set, open on the Replay tab for this walk-forward event id. */
  replayEventId?: string | null
}

const TABS: { id: PocTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'method', label: 'Method' },
  { id: 'math', label: 'Math' },
  { id: 'cases', label: 'Cases' },
  { id: 'replay', label: 'Replay' },
  { id: 'placebos', label: 'Placebos' },
]

/** Walk-forward event ids matching data/alerts/walkforward/wf_<id>.json */
const REPLAY_EVENTS: { id: string; label: string }[] = [
  { id: 'luch1_intelsat_2015', label: 'Luch-1 · Intelsat (2015)' },
  { id: 'luch1_intelsat_mid2015', label: 'Luch-1 · Intelsat mid-2015' },
  { id: 'luch1_athena_fidus_2018', label: 'Luch-1 · Athena-Fidus (2018)' },
  { id: 'luch2_geo_ops_2024', label: 'Luch-2 · GEO ops (2024)' },
  { id: 'luch2_trailing_2023', label: 'Luch-2 · trailing (2023)' },
  { id: 'sy12_geo_rpo_2021_22', label: 'SY-12 · GEO RPO (2021-22)' },
  { id: 'shiyan7_experimental_2015', label: 'Shiyan-7 · experimental (2015)' },
  { id: 'yaogan29_recon_2020', label: 'Yaogan-29 · recon (2020)' },
  { id: 'yaogan29_sso_2025q1', label: 'Yaogan-29 · SSO (2025 Q1)' },
  { id: 'yaogan3_recon_2016', label: 'Yaogan-3 · recon (2016)' },
  { id: 'tianhe_css_assembly_2021', label: 'Tianhe · CSS assembly (2021)' },
  { id: 'cosmos2550_military_leo_2022', label: 'Cosmos-2550 · mil LEO (2022)' },
  { id: 'beidou3_m11_meo_2019', label: 'Beidou-3 M11 · MEO (2019)' },
  { id: 'placebo_terra_2015', label: 'Placebo · TERRA 2015' },
  { id: 'placebo_terra_2018', label: 'Placebo · TERRA 2018' },
  { id: 'placebo_aqua_2015', label: 'Placebo · AQUA 2015' },
  { id: 'placebo_aqua_2020', label: 'Placebo · AQUA 2020' },
  { id: 'placebo_landsat8_2018', label: 'Placebo · Landsat-8 2018' },
  { id: 'placebo_noaa18_2021', label: 'Placebo · NOAA-18 2021' },
  { id: 'placebo_noaa20_2023', label: 'Placebo · NOAA-20 2023' },
]

type RefLink = { label: string; url: string }

const CASES: {
  id: string
  title: string
  norad: number
  firstHit: string
  peak: string
  lead: number
  score: number
  why: string
  report: string
  refs: RefLink[]
}[] = [
  {
    id: 'luch-mid',
    title: 'Luch-1 · Intelsat mid-2015',
    norad: 40258,
    firstHit: '2014-10-15',
    peak: '2015-04-15',
    lead: 182,
    score: 0.724,
    why: 'Page CUSUM ≈ 1.0 + LZ76 ~1.4–1.7 on the ΔSMA series (GEO slot move). DFA α stays ~0.5 on n≈20 — not a Hurst read.',
    report:
      'Open catalog history: Olymp-K moved ~Apr 2015 between Intelsat 7 and 901 (~18.1°W).',
    refs: [
      {
        label: "Gunter's Space Page — Olimp-K / Luch-Kh",
        url: 'https://space.skyrocket.de/doc_sdat/olimp-k.htm',
      },
      {
        label: 'CSIS Aerospace — Unusual Behavior in GEO: Luch (Olymp-K)',
        url: 'https://aerospace.csis.org/data/unusual-behavior-in-geo-olymp-k/',
      },
      {
        label: 'Wikipedia — Olymp-K (timeline & sources)',
        url: 'https://en.wikipedia.org/wiki/Olymp-K',
      },
    ],
  },
  {
    id: 'luch-2015',
    title: 'Luch-1 · Intelsat 905 season',
    norad: 40258,
    firstHit: '2015-01-15',
    peak: '2015-09-15',
    lead: 243,
    score: 0.699,
    why: 'Page CUSUM elevated (early mean 1.0) + Shannon H~1.9–2.0 + LZ76 ~1.6. DFA α = 0.5 (short-window floor).',
    report:
      'Open sources: late Sep 2015 move to ~24.4°W next to Intelsat 905 at 24.5°W; Intelsat criticism of non-normal behavior.',
    refs: [
      {
        label: "Gunter's Space Page — Olimp-K (Intelsat 905 colocation)",
        url: 'https://space.skyrocket.de/doc_sdat/olimp-k.htm',
      },
      {
        label: 'CSIS Aerospace — Unusual Behavior in GEO: Luch (Olymp-K)',
        url: 'https://aerospace.csis.org/data/unusual-behavior-in-geo-olymp-k/',
      },
      {
        label: 'Wikipedia — Olymp-K (Intelsat statements)',
        url: 'https://en.wikipedia.org/wiki/Olymp-K',
      },
    ],
  },
  {
    id: 'luch-fidus',
    title: 'Luch-1 · Athena-Fidus 2018',
    norad: 40258,
    firstHit: '2018-01-01',
    peak: '2018-09-01',
    lead: 243,
    score: 0.724,
    why: 'Page CUSUM = 1.0 + LZ76 1.38→1.71 + Shannon rising 1.52→1.87 under quiet Sun. DFA α = 0.5.',
    report:
      'French MoD (Florence Parly, Sep 2018) publicly described Luch-Olymp proximity to Athena-Fidus as espionage-like; also noted on Gunter.',
    refs: [
      {
        label: "Gunter's Space Page — Olimp-K (Athena-Fidus 2018)",
        url: 'https://space.skyrocket.de/doc_sdat/olimp-k.htm',
      },
      {
        label: 'Wikipedia — Olymp-K (Parly / Athena-Fidus statement)',
        url: 'https://en.wikipedia.org/wiki/Olymp-K',
      },
      {
        label: 'CSIS Aerospace — Unusual Behavior in GEO: Luch (Olymp-K)',
        url: 'https://aerospace.csis.org/data/unusual-behavior-in-geo-olymp-k/',
      },
    ],
  },
  {
    id: 'sy12',
    title: 'Shiyan-12 01 · GEO RPO',
    norad: 50321,
    firstHit: '2022-01-12',
    peak: '2022-06-15',
    lead: 154,
    score: 0.712,
    why: 'Shannon H rises 1.51→2.72 + LZ76 ~1.5 early + Page CUSUM 0.75 early. DFA α = 0.5 (do not cite α≈0.89).',
    report:
      'Secure World Foundation tracks SY-12 among Chinese military/intelligence GEO RPO missions; open SSA literature discusses SY-12 proximity ops.',
    refs: [
      {
        label: 'SWF — Chinese Military & Intelligence RPO Fact Sheet',
        url: 'https://www.swfound.org/publications-and-reports/chinese-military-and-intelligence-rendezvous-and-proximity-operations-fact-sheet',
      },
      {
        label: 'SWF — Global Counterspace Capabilities (program context)',
        url: 'https://www.swfound.org/publications-and-reports/2025-global-counterspace-capabilities-report',
      },
    ],
  },
  {
    id: 'luch2',
    title: 'Luch-2 · trailing 2023',
    norad: 55841,
    firstHit: '2023-04-01',
    peak: '2023-10-15',
    lead: 197,
    score: 0.722,
    why: 'Shannon H ~1.8–1.9 + short Shannon rising to 2.26 + elevated IF (max 0.722). DFA α = 0.5.',
    report:
      'Breaking Defense (17 Oct 2023): second Russian Luch/Olymp reported trailing Western systems in GEO.',
    refs: [
      {
        label: 'Breaking Defense — Second Luch/Olymp trailing Western systems (Oct 2023)',
        url: 'https://breakingdefense.com/2023/10/second-russian-luch-olymp-satellite-now-trailing-western-systems-in-orbit/',
      },
      {
        label: "Gunter's Space Page — Olimp-K series",
        url: 'https://space.skyrocket.de/doc_sdat/olimp-k.htm',
      },
    ],
  },
]

/**
 * In-app walk-forward proof-of-concept panel for judges.
 * Embedded in the globe HUD — not a separate browser-only page.
 */
export default function WalkforwardPocPanel({
  open,
  onClose,
  replayEventId = null,
}: WalkforwardPocPanelProps) {
  const [tab, setTab] = useState<PocTab>('overview')
  const [eventId, setEventId] = useState<string>(REPLAY_EVENTS[0]?.id ?? '')

  useEffect(() => {
    if (!open) return
    if (!replayEventId) return
    const t = window.setTimeout(() => {
      setTab('replay')
      setEventId(replayEventId)
    }, 0)
    return () => clearTimeout(t)
  }, [open, replayEventId])

  if (!open) return null

  const fullHtml = `${import.meta.env.BASE_URL}reports/walkforward_poc.html`

  return (
    <>
      {/* Dim globe so PoC text is readable */}
      <button
        type="button"
        aria-label="Close proof of concept"
        className="pointer-events-auto absolute inset-0 z-[39] cursor-default border-0 bg-black/88"
        onClick={onClose}
      />

      <div
        className="pointer-events-auto absolute inset-x-3 top-[88px] z-40 flex max-h-[min(780px,calc(100vh-120px))] flex-col overflow-hidden border border-emerald-400/30 bg-[#05070c] shadow-[0_12px_48px_rgba(0,0,0,0.85)] md:inset-x-auto md:left-1/2 md:w-[min(760px,calc(100vw-2rem))] md:-translate-x-1/2 md:top-[96px]"
        role="dialog"
        aria-modal="true"
        aria-label="Walk-forward ML proof of concept"
        onClick={(e) => e.stopPropagation()}
      >
      {/* Header */}
      <div className="flex shrink-0 items-start justify-between gap-3 border-b border-white/12 bg-[#0a1018] px-3 py-2.5 md:px-4">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-300/90">
            ML proof of concept · walk-forward
          </div>
          <h2 className="mt-0.5 text-[15px] font-semibold leading-snug text-zinc-50 md:text-[16px]">
            Quantitative noise detection · walk-forward validation
          </h2>
          <p className="mt-1 text-[12px] leading-relaxed text-zinc-400 md:text-[13px]">
            Isolation Forest past-only · thr 0.50 ·{' '}
            <span className="text-emerald-300">GEO interest 5/5</span> ·{' '}
            <span className="text-zinc-300">civil EO placebos 0/7</span>
          </p>
        </div>
        <div className="flex shrink-0 flex-col gap-1.5 sm:flex-row">
          <a
            href={fullHtml}
            target="_blank"
            rel="noreferrer"
            className="athena-btn px-2.5 py-1 text-center text-[12px]"
            title="Open full HTML report in a new browser tab"
          >
            New tab ↗
          </a>
          <button
            type="button"
            onClick={onClose}
            className="athena-btn athena-btn-active px-2.5 py-1 text-[12px]"
          >
            Close
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex shrink-0 gap-0.5 overflow-x-auto border-b border-white/10 px-2 py-1.5">
        {TABS.map((t) => {
          const active = tab === t.id
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`shrink-0 px-2.5 py-1.5 text-[12px] font-medium uppercase tracking-[0.1em] transition-colors ${
                active
                  ? 'border border-emerald-400/45 bg-emerald-400/15 text-emerald-100'
                  : 'border border-transparent text-zinc-400 hover:bg-white/[0.04] hover:text-zinc-200'
              }`}
            >
              {t.label}
            </button>
          )
        })}
      </div>

      {/* Body — solid surface for readability */}
      <div className="athena-scroll min-h-0 flex-1 overflow-y-auto bg-[#070a10] px-3 py-3 text-[13px] leading-relaxed text-zinc-200 md:px-4 md:text-[14px]">
        {tab === 'overview' && <OverviewTab />}
        {tab === 'method' && <MethodTab />}
        {tab === 'math' && <MathTab />}
        {tab === 'cases' && <CasesTab />}
        {tab === 'replay' && (
          <ReplayTab eventId={eventId} onEventId={setEventId} />
        )}
        {tab === 'placebos' && <PlacebosTab />}
      </div>

      <div className="shrink-0 border-t border-white/12 bg-[#0a1018] px-3 py-2 text-[11px] text-zinc-500 md:px-4">
        Use <strong className="text-zinc-400">New tab</strong> for full-page HTML · backdrop
        click or Esc closes · walk-forward 2026-08-11 · Athena-SDA
      </div>
      </div>
    </>
  )
}

function OverviewTab() {
  return (
    <div className="space-y-3">
      <p className="text-zinc-200">
        Athena turns public TLE + space weather into a{' '}
        <strong className="text-zinc-50">quantitative noise profile</strong>. Isolation Forest
        scores how rare the current window is versus normality anchors (baseline + asset).
        Walk-forward evaluates scores on open-source report windows and civil EO placebos under a
        past-only protocol.
      </p>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Stat k="GEO interest" v="5/5 hard" ok />
        <Stat k="Civil EO" v="0/7 hard" ok />
        <Stat k="Mean max GEO" v="0.716" ok />
        <Stat k="Mean max EO" v="0.457" />
      </div>

      <div className="border border-emerald-400/35 bg-[#0c1814] p-2.5">
        <div className="text-[11px] uppercase tracking-[0.14em] text-emerald-300/90">
          What Athena does
        </div>
        <ul className="mt-1.5 list-disc space-y-1 pl-4 text-[12px] text-zinc-200 md:text-[13px]">
          <li>Ingest public multi-year TLE + GFZ F10.7/Ap/Kp</li>
          <li>Build quant noise features (LZ76, DFA, Page CUSUM, Shannon, …)</li>
          <li>Train IF on baseline+asset; score suspects for micro-anomalies</li>
          <li>Validate GEO interest vs civil EO placebos (Claims A+B)</li>
          <li>Priority layer (pairs, XGB) ranks operator attention</li>
        </ul>
      </div>

      <p className="border border-sky-400/30 bg-[#0a1218] p-2.5 text-[12px] text-zinc-200 md:text-[13px]">
        <strong className="text-sky-200">Summary:</strong> multi-year public orbits → quantitative
        noise vector → past-only Isolation Forest → elevated scores on Luch/Shiyan-class windows
        relative to TERRA/AQUA/NOAA placebos under the same protocol.
      </p>
    </div>
  )
}

function MethodTab() {
  const steps = [
    'Ingest public TLE history + GFZ F10.7/Ap/Kp',
    '20-epoch window → Kepler + math noise + weather features',
    'Train Isolation Forest only on windows ending before asof − 3 days',
    'anomaly_score = clip(0.5 − decision_function) · hard hit if ≥ 0.50 near public peak',
    'Story: quant noise features → IF score vs placebo → open-source case reading',
  ]
  return (
    <div className="space-y-3">
      <p>
        Think of each satellite as a patient chart. Athena builds a short summary of recent
        orbits, then asks: <em className="text-zinc-100">“Given only past charts, is today weird?”</em>
      </p>
      <ol className="space-y-1.5">
        {steps.map((s, i) => (
          <li
            key={s}
            className="flex gap-2 border border-white/12 bg-[#0c0e12] px-2.5 py-2 font-mono text-[11px] text-zinc-200 md:text-[12px]"
          >
            <span className="text-emerald-400">{i + 1}</span>
            <span>{s}</span>
          </li>
        ))}
      </ol>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Stat k="Step" v="14 d" />
        <Stat k="Holdout" v="3 d" />
        <Stat k="Threshold" v="0.50" ok />
        <Stat k="Peak window" v="±45 d" />
      </div>
      <p className="text-[12px] text-zinc-500">
        XGBoost / fuzzy / pair-risk prioritize the daily board. The walk-forward{' '}
        <strong className="text-zinc-300">hit criterion is Isolation Forest anomaly only</strong>
        (series noise of that object — not cointegration).
      </p>
    </div>
  )
}

function MathTab() {
  const rows = [
    ['Shannon H', 'How messy are ΔSMA steps?', 'Irregular burns / SK'],
    ['DFA α (Peng 1994)', 'Does the series keep a scaling trend?', 'α≫0.5 persistence; n=20 often floors at 0.5'],
    ['LZ76 (Kaspar–Schuster)', 'Hard to compress the up/down pattern?', 'Active control complexity'],
    ['Page CUSUM (ARL)', 'When did the series leave its regime?', 'Structural change onset'],
    ['EWMA / BOCPD', 'Small shifts / Bayesian change prob?', 'Busy GEO ops, regime switches'],
    ['Space weather (GFZ)', 'Is the Sun stormy?', 'LEO drag vs intentional change'],
    ['IF anomaly', 'Is the full profile rare vs past?', 'Operational noise trigger'],
  ] as const
  return (
    <div className="space-y-3">
      <p>
        Math tools produce <strong className="text-zinc-100">features</strong> (numbers). Isolation
        Forest learns their joint “normal” envelope. Almost the full toolkit enters the ML vector;
        distance/cointegration go to XGBoost/pair priority, not IF.
      </p>
      <div className="overflow-x-auto border border-white/12 bg-[#0c0e12]">
        <table className="w-full min-w-[480px] text-left text-[12px]">
          <thead>
            <tr className="border-b border-white/12 bg-[#0a1018] text-[10px] uppercase tracking-[0.12em] text-zinc-500">
              <th className="px-2 py-1.5 font-medium">Tool</th>
              <th className="px-2 py-1.5 font-medium">Plain meaning</th>
              <th className="px-2 py-1.5 font-medium">Orbit cue</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([a, b, c]) => (
              <tr key={a} className="border-t border-white/10">
                <td className="px-2 py-1.5 font-medium text-emerald-200/90">{a}</td>
                <td className="px-2 py-1.5 text-zinc-200">{b}</td>
                <td className="px-2 py-1.5 text-zinc-400">{c}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="font-mono text-[11px] text-zinc-400 md:text-[12px]">
        score = clip(0.5 − IF.decision_function(x)) · train only on past windows
      </p>
    </div>
  )
}

function CasesTab() {
  return (
    <div className="space-y-3">
      <p className="text-[12px] text-zinc-400">
        Each case: elevated IF score on known atypical regimes → public anchor as case study. NORADs match the
        watchlist (Luch / SY-12).
      </p>
      {CASES.map((c) => (
        <article
          key={c.id}
          className="border border-l-[3px] border-white/12 border-l-emerald-400/80 bg-[#0c0e12] p-2.5"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-1">
            <h3 className="text-[13px] font-semibold text-zinc-50 md:text-[14px]">
              {c.title}{' '}
              <span className="font-mono text-[11px] font-normal text-zinc-500">
                #{c.norad}
              </span>
            </h3>
            <span className="font-mono text-[12px] text-emerald-300">
              lead {c.lead}d · score {c.score}
            </span>
          </div>
          <div className="mt-2 grid gap-1 text-[12px] md:grid-cols-2">
            <div>
              <span className="text-emerald-400">★ First hit</span>{' '}
              <span className="font-mono text-zinc-100">{c.firstHit}</span>
            </div>
            <div>
              <span className="text-rose-300">══ Public peak</span>{' '}
              <span className="font-mono text-zinc-100">{c.peak}</span>
            </div>
          </div>
          <p className="mt-1.5 text-[12px] text-zinc-200">
            <strong className="text-zinc-50">Why IF fired:</strong> {c.why}
          </p>
          <p className="mt-1 text-[12px] text-zinc-300">
            <strong className="text-zinc-100">Report story:</strong> {c.report}
          </p>
          <div className="mt-2 border-t border-white/10 pt-2">
            <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500">
              Open-source references
            </div>
            <ul className="mt-1 space-y-1">
              {c.refs.map((r) => (
                <li key={r.url}>
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="text-[12px] text-emerald-300/95 underline-offset-2 hover:text-emerald-200 hover:underline"
                  >
                    {r.label} ↗
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </article>
      ))}
      <p className="text-[11px] leading-relaxed text-zinc-500">
        References are public open-source anchors for narrative validation only. They are not
        classified ground truth. Athena scores use past-only TLE/features; links document what the
        public later reported.
      </p>
    </div>
  )
}

function PlacebosTab() {
  const rows = [
    ['TERRA #25994', '2015-09-15 vs Luch', '0.470', 'NO'],
    ['TERRA #25994', '2018-09-01 vs Fidus', '0.457', 'NO'],
    ['AQUA #27424', '2015 vs Luch', '0.490', 'NO'],
    ['AQUA #27424', '2020', '0.401', 'NO'],
    ['Landsat-8 #39084', '2018', '0.459', 'NO'],
    ['NOAA-18 #28654', '2021', '0.423', 'NO'],
    ['NOAA-20 #43013', '2023-10-15 vs Luch-2', '0.498', 'NO'],
  ] as const
  return (
    <div className="space-y-3">
      <p>
        Same solar/geomagnetic calendars as interest cases. If weather alone caused alerts,
        placebos would hard-hit. They did not.
      </p>
      <div className="overflow-x-auto border border-white/12 bg-[#0c0e12]">
        <table className="w-full min-w-[420px] text-left text-[12px]">
          <thead>
            <tr className="border-b border-white/12 bg-[#0a1018] text-[10px] uppercase tracking-[0.12em] text-zinc-500">
              <th className="px-2 py-1.5">Placebo</th>
              <th className="px-2 py-1.5">Shared peak</th>
              <th className="px-2 py-1.5">Max score</th>
              <th className="px-2 py-1.5">Hard hit</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([a, b, c, d]) => (
              <tr key={a + b} className="border-t border-white/10">
                <td className="px-2 py-1.5 text-zinc-100">{a}</td>
                <td className="px-2 py-1.5 font-mono text-zinc-400">{b}</td>
                <td className="px-2 py-1.5 font-mono text-zinc-200">{c}</td>
                <td className="px-2 py-1.5 text-zinc-500">{d}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border border-white/12 bg-[#0c0e12] p-2.5 text-[12px] text-zinc-300">
        Claim B = these 7 civil EO placebos (0/7 hard). Starlink / GPS can hard-hit
        (station-keeping) and are <strong className="text-zinc-100">not</strong> in the 0/7
        panel. Discriminator = LZ76 / Page CUSUM / Shannon / joint IF — not F10.7 alone.
      </p>
    </div>
  )
}

function Stat({
  k,
  v,
  ok,
}: {
  k: string
  v: string
  ok?: boolean
}) {
  return (
    <div className="border border-white/12 bg-[#0c0e12] px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500">{k}</div>
      <div
        className={`mt-0.5 font-mono text-[15px] ${
          ok ? 'text-emerald-300' : 'text-zinc-50'
        }`}
      >
        {v}
      </div>
    </div>
  )
}

function ReplayTab({
  eventId,
  onEventId,
}: {
  eventId: string
  onEventId: (id: string) => void
}) {
  return (
    <div className="space-y-2">
      <p className="text-[12px] text-zinc-400">
        Scruba a curva de anomaly_score(t) do walk-forward (patente Palantir
        12,450,265 — tile temporal). A linha tracejada vermelha é o âncora
        público <span className="font-mono text-rose-300">t_peak</span>; a
        amarela é o threshold 0.50.
      </p>
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-[11px] uppercase tracking-wider text-zinc-500">Event</span>
        <select
          value={eventId}
          onChange={(e) => onEventId(e.target.value)}
          className="athena-input min-w-0 flex-1 px-2 py-1 text-[13px]"
          aria-label="walk-forward event"
        >
          {[
            ...REPLAY_EVENTS,
            ...(!REPLAY_EVENTS.some((e) => e.id === eventId) && eventId
              ? [{ id: eventId, label: eventId.replace(/_/g, ' ') }]
              : []),
          ].map((e) => (
            <option key={e.id} value={e.id}>
              {e.label}
            </option>
          ))}
        </select>
      </div>
      {eventId && <EventReplayPanel eventId={eventId} threshold={0.5} />}
    </div>
  )
}

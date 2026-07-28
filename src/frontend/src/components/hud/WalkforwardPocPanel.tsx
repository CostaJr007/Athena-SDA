import { useState } from 'react'

type PocTab = 'overview' | 'method' | 'math' | 'cases' | 'placebos'

interface WalkforwardPocPanelProps {
  open: boolean
  onClose: () => void
}

const TABS: { id: PocTab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'method', label: 'Method' },
  { id: 'math', label: 'Math' },
  { id: 'cases', label: 'Cases' },
  { id: 'placebos', label: 'Placebos' },
]

const CASES = [
  {
    id: 'luch-mid',
    title: 'Luch-1 · Intelsat mid-2015',
    norad: 40258,
    firstHit: '2014-10-15',
    peak: '2015-04-15',
    lead: 182,
    score: 0.646,
    why: 'ΔSMA ≈ −72 km (GEO slot move) + Hurst 0.80. Quiet weather (Ap=9).',
    report: 'Gunter: first colocation between Intelsat 7 and 901 (~April 2015).',
  },
  {
    id: 'luch-2015',
    title: 'Luch-1 · Intelsat 905 season',
    norad: 40258,
    firstHit: '2015-01-15',
    peak: '2015-09-15',
    lead: 243,
    score: 0.537,
    why: 'Hurst 0.94 + 6 maneuvers/30d + Shannon elevated. Later ΔSMA +62 km fold.',
    report: 'Gunter / CSIS: proximity to Intelsat 905 ~24.5°W (~Sep 2015).',
  },
  {
    id: 'luch-fidus',
    title: 'Luch-1 · Athena-Fidus 2018',
    norad: 40258,
    firstHit: '2018-01-15',
    peak: '2018-09-01',
    lead: 229,
    score: 0.524,
    why: 'Hurst 0.96 + Kolmogorov 0.58 under quiet Sun (F10.7≈70). Later ΔSMA −110 km.',
    report: 'Open press / Gunter: concerns near Athena-Fidus (FR military satcom).',
  },
  {
    id: 'sy12',
    title: 'Shiyan-12 01 · GEO RPO',
    norad: 50321,
    firstHit: '2022-01-12',
    peak: '2022-06-15',
    lead: 154,
    score: 0.534,
    why: 'Kolmogorov 0.63 + 6 maneuvers/30d + Hurst 0.89 — inspection-like control.',
    report: 'AMOS / SWF open SSA: SY-12 GEO RPO / proximity reporting.',
  },
  {
    id: 'luch2',
    title: 'Luch-2 · trailing 2023',
    norad: 55841,
    firstHit: '2023-04-01',
    peak: '2023-10-15',
    lead: 197,
    score: 0.551,
    why: 'Shannon 2.12 + Hurst 0.91 weeks after launch. Max 0.569 on 2023-09-02.',
    report: 'Breaking Defense (Oct 2023): second Luch trailing Western GEO systems.',
  },
]

/**
 * In-app walk-forward proof-of-concept panel for judges.
 * Embedded in the globe HUD — not a separate browser-only page.
 */
export default function WalkforwardPocPanel({
  open,
  onClose,
}: WalkforwardPocPanelProps) {
  const [tab, setTab] = useState<PocTab>('overview')

  if (!open) return null

  return (
    <div
      className="pointer-events-auto absolute inset-x-3 top-[100px] z-40 flex max-h-[min(720px,calc(100vh-190px))] flex-col overflow-hidden border border-emerald-400/25 bg-black/92 shadow-[0_0_40px_rgba(0,0,0,0.65)] backdrop-blur-md md:inset-x-auto md:left-1/2 md:w-[min(720px,calc(100vw-2rem))] md:-translate-x-1/2 md:top-[110px]"
      role="dialog"
      aria-label="Walk-forward ML proof of concept"
    >
      {/* Header */}
      <div className="flex shrink-0 items-start justify-between gap-3 border-b border-white/10 bg-gradient-to-b from-emerald-500/10 to-transparent px-3 py-2.5 md:px-4">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-300/90">
            ML proof of concept · walk-forward
          </div>
          <h2 className="mt-0.5 text-[15px] font-semibold leading-snug text-zinc-50 md:text-[16px]">
            Noise detected before public reports
          </h2>
          <p className="mt-1 text-[12px] leading-relaxed text-zinc-400 md:text-[13px]">
            Isolation Forest past-only · thr 0.50 ·{' '}
            <span className="text-emerald-300">5/5 interest</span> ·{' '}
            <span className="text-zinc-300">0/3 placebos</span> · ~201 day mean
            lead-time
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="athena-btn shrink-0 px-2.5 py-1 text-[12px]"
        >
          Close
        </button>
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

      {/* Body */}
      <div className="athena-scroll min-h-0 flex-1 overflow-y-auto px-3 py-3 text-[13px] leading-relaxed text-zinc-300 md:px-4 md:text-[14px]">
        {tab === 'overview' && <OverviewTab />}
        {tab === 'method' && <MethodTab />}
        {tab === 'math' && <MathTab />}
        {tab === 'cases' && <CasesTab />}
        {tab === 'placebos' && <PlacebosTab />}
      </div>

      <div className="shrink-0 border-t border-white/10 px-3 py-2 text-[11px] text-zinc-500 md:px-4">
        Full static HTML still available at{' '}
        <code className="text-emerald-400/80">/reports/walkforward_poc.html</code>{' '}
        · run 2026-07-26 · Athena-SDA
      </div>
    </div>
  )
}

function OverviewTab() {
  return (
    <div className="space-y-3">
      <p className="text-zinc-200">
        Athena turns public TLE + space weather into a <strong className="text-zinc-50">noise profile</strong>.
        Isolation Forest asks: is this object rare compared with <em>its own past</em>?
        Walk-forward replays history <strong className="text-zinc-50">without future data</strong> and
        checks whether that score rose before open-source report dates.
      </p>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
        <Stat k="Interest hits" v="5/5" ok />
        <Stat k="Placebo hits" v="0/3" />
        <Stat k="Mean lead" v="~201 d" ok />
        <Stat k="Mean max score" v="0.603" />
      </div>

      <div className="grid gap-2 md:grid-cols-2">
        <div className="border border-emerald-400/25 bg-emerald-500/5 p-2.5">
          <div className="text-[11px] uppercase tracking-[0.14em] text-emerald-300/90">
            We claim
          </div>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-[12px] text-zinc-300 md:text-[13px]">
            <li>Real public TLE + GFZ weather</li>
            <li>Past-only training at each test date</li>
            <li>Hard anomaly before report anchors on 5/5 cases</li>
            <li>Civil placebos on same calendars did not hard-hit</li>
          </ul>
        </div>
        <div className="border border-white/10 bg-black/40 p-2.5">
          <div className="text-[11px] uppercase tracking-[0.14em] text-zinc-500">
            We do not claim
          </div>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-[12px] text-zinc-400 md:text-[13px]">
            <li>Classified ground-truth of hostile intent</li>
            <li>XGB accuracy = espionage detection</li>
            <li>Lead-time = single discrete burn prediction</li>
            <li>Secret TCA times (anchors are open publications)</li>
          </ul>
        </div>
      </div>

      <p className="border border-sky-400/20 bg-sky-500/5 p-2.5 text-[12px] text-zinc-300 md:text-[13px]">
        <strong className="text-sky-200">Jury one-liner:</strong> multi-year public orbits →
        quantitative noise vector → Isolation Forest on the past only → Luch/Shiyan
        statistically loud months before Gunter/CSIS/Breaking Defense — TERRA/NOAA placebos not.
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
    'Story: first hit date → lead-time → open-source report confirmation',
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
            className="flex gap-2 border border-white/10 bg-black/50 px-2.5 py-2 font-mono text-[11px] text-zinc-300 md:text-[12px]"
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
    ['Shannon', 'How messy are altitude steps?', 'Irregular burns / SK'],
    ['Hurst', 'Does the series keep drifting one way?', 'H ≫ 0.5 → low-thrust / control'],
    ['Kolmogorov', 'Hard to compress up/down pattern?', 'Active control complexity'],
    ['L1-CUSUM', 'When did the series break?', 'Structural change onset'],
    ['ΔSMA / maneuvers', 'How far / how often?', 'Slot moves, busy GEO ops'],
    ['Space weather', 'Is the Sun stormy?', 'Drag vs intentional change'],
    ['IF anomaly', 'Is the full profile rare vs past?', 'Operational noise trigger'],
  ] as const
  return (
    <div className="space-y-3">
      <p>
        Math tools produce <strong className="text-zinc-100">features</strong> (numbers). Isolation
        Forest learns their joint “normal” envelope. Almost the full toolkit enters the ML vector;
        distance/cointegration go to XGBoost/pair priority, not IF.
      </p>
      <div className="overflow-x-auto border border-white/10">
        <table className="w-full min-w-[480px] text-left text-[12px]">
          <thead>
            <tr className="border-b border-white/10 text-[10px] uppercase tracking-[0.12em] text-zinc-500">
              <th className="px-2 py-1.5 font-medium">Tool</th>
              <th className="px-2 py-1.5 font-medium">Plain meaning</th>
              <th className="px-2 py-1.5 font-medium">Orbit cue</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([a, b, c]) => (
              <tr key={a} className="border-t border-white/5">
                <td className="px-2 py-1.5 font-medium text-emerald-200/90">{a}</td>
                <td className="px-2 py-1.5 text-zinc-300">{b}</td>
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
        Each case: Athena hard hit → lead-time → public open-source anchor. NORADs match the
        watchlist (Luch / SY-12).
      </p>
      {CASES.map((c) => (
        <article
          key={c.id}
          className="border border-l-[3px] border-white/10 border-l-emerald-400/70 bg-black/40 p-2.5"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-1">
            <h3 className="text-[13px] font-semibold text-zinc-100 md:text-[14px]">
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
              <span className="text-emerald-400/90">★ First hit</span>{' '}
              <span className="font-mono text-zinc-200">{c.firstHit}</span>
            </div>
            <div>
              <span className="text-rose-300/90">══ Public peak</span>{' '}
              <span className="font-mono text-zinc-200">{c.peak}</span>
            </div>
          </div>
          <p className="mt-1.5 text-[12px] text-zinc-300">
            <strong className="text-zinc-100">Why IF fired:</strong> {c.why}
          </p>
          <p className="mt-1 text-[12px] text-zinc-400">
            <strong className="text-zinc-300">Report story:</strong> {c.report}
          </p>
        </article>
      ))}
    </div>
  )
}

function PlacebosTab() {
  const rows = [
    ['TERRA #25994', '2015-09-15 vs Luch', '0.478', 'NO'],
    ['TERRA #25994', '2018-09-01 vs Fidus', '0.489', 'NO'],
    ['NOAA-20 #43013', '2023-10-15 vs Luch-2', '0.463', 'NO'],
  ] as const
  return (
    <div className="space-y-3">
      <p>
        Same solar/geomagnetic calendars as interest cases. If weather alone caused alerts,
        placebos would hard-hit. They did not.
      </p>
      <div className="overflow-x-auto border border-white/10">
        <table className="w-full min-w-[420px] text-left text-[12px]">
          <thead>
            <tr className="border-b border-white/10 text-[10px] uppercase tracking-[0.12em] text-zinc-500">
              <th className="px-2 py-1.5">Placebo</th>
              <th className="px-2 py-1.5">Shared peak</th>
              <th className="px-2 py-1.5">Max score</th>
              <th className="px-2 py-1.5">Hard hit</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([a, b, c, d]) => (
              <tr key={a + b} className="border-t border-white/5">
                <td className="px-2 py-1.5 text-zinc-200">{a}</td>
                <td className="px-2 py-1.5 font-mono text-zinc-400">{b}</td>
                <td className="px-2 py-1.5 font-mono">{c}</td>
                <td className="px-2 py-1.5 text-zinc-500">{d}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border border-white/10 bg-black/40 p-2.5 text-[12px] text-zinc-400">
        Discriminator = orbital regime features (Hurst / Shannon / ΔSMA / joint IF profile), not
        F10.7 alone.
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
    <div className="border border-white/10 bg-black/50 px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-[0.12em] text-zinc-500">{k}</div>
      <div
        className={`mt-0.5 font-mono text-[15px] ${
          ok ? 'text-emerald-300' : 'text-zinc-100'
        }`}
      >
        {v}
      </div>
    </div>
  )
}

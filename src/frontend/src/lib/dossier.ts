/**
 * Investigation dossier — Gotham Dossier analogue.
 * BLUF + immutable scores + links + lineage. Not a conjunction report.
 * OpenCTI pattern: investigation graph → exportable Report.
 */
import type { BoardEntry, RiskReport } from '@/lib/risk-report'
import { boardThreat } from '@/lib/risk-report'
import type { ObjectGraph, WfCaseHit } from '@/lib/investigation'
import { casesForNorad, shortEventLabel } from '@/lib/investigation'

export function buildDossierHtml(opts: {
  entry: BoardEntry
  report: RiskReport | null
  graph: ObjectGraph | null
  cases: WfCaseHit[]
}): string {
  const { entry, report, graph, cases } = opts
  const threat = boardThreat(entry)
  const own = casesForNorad(cases, entry.norad_id)
  const links = (graph?.edges ?? [])
    .map((e) => {
      const n = graph?.nodes.find((x) => x.id === e.to)
      return n ? `${e.label} → ${n.label} (${n.sub})` : e.label
    })
    .join('<br/>')
  const caseLines = own
    .map(
      (c) =>
        `${shortEventLabel(c.eventId)} · ${c.isPlacebo ? 'placebo' : 'interest'} · ${
          c.hit ? 'HIT' : 'miss'
        } · t_peak ${c.tPeak.slice(0, 10)}${
          c.leadDays != null ? ` · lead ${c.leadDays.toFixed(0)}d` : ''
        }`,
    )
    .join('<br/>')

  const bluf = `${entry.object_name} (#${entry.norad_id}) is ${entry.role} · ${
    entry.orbit_class
  } · ${entry.country} · ${threat}. Attention ${entry.attention_score.toFixed(
    3,
  )} · anomaly ${entry.anomaly_score.toFixed(3)}. Pattern-of-life ≠ intent.`

  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Dossier · ${entry.object_name} #${entry.norad_id}</title>
<style>
  body{margin:24px;background:#07090d;color:#e4e4e7;font:15px/1.45 "IBM Plex Sans",system-ui,sans-serif}
  h1{font-size:20px;margin:0 0 4px} .meta{color:#a1a1aa;font-size:12px;letter-spacing:.08em;text-transform:uppercase}
  section{border:1px solid #27272a;padding:12px 14px;margin:12px 0;background:#0c0e12}
  .bluf{border-left:3px solid #34d399;padding-left:12px}
  .num{font-variant-numeric:tabular-nums;font-family:"IBM Plex Mono",ui-monospace,monospace}
</style></head><body>
<p class="meta">Athena-SDA · investigation dossier · ${report?.schema ?? 'athena.risk_report.v1'}</p>
<h1>${entry.object_name} <span class="num">#${entry.norad_id}</span></h1>
<p class="meta">${report?.day ?? '—'} · ${(report?.doctrine ?? 'military_first_sda').replace(/_/g, ' ')} · past-only IF</p>
<section class="bluf"><strong>BLUF.</strong> ${bluf}</section>
<section><div class="meta">Immutable scores</div>
<p class="num">attention ${entry.attention_score.toFixed(3)} · anomaly ${entry.anomaly_score.toFixed(3)} · status ${entry.status}
${entry.evidence?.belief_anomalous != null ? ` · DS belief ${entry.evidence.belief_anomalous.toFixed(3)}` : ''}</p>
<p>Scores are Isolation Forest / fusion outputs. This dossier does not rewrite them (US 2024/0394296).</p>
</section>
<section><div class="meta">Ontology links</div><p>${links || '—'}</p></section>
<section><div class="meta">Walk-forward cases</div><p>${caseLines || 'none on this NORAD'}</p></section>
<section><div class="meta">Lineage · insight-first</div>
<p>TLE public → noise features (LZ76, DFA, CUSUM…) → IF past-only → DS / Kelly · thr ${
    report?.summary.threshold?.toFixed(3) ?? '—'
  } · ${report?.protocol ?? 'military_baseline_train__suspect_score'}</p>
</section>
</body></html>`
}

export function downloadDossier(html: string, norad: number, day?: string) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `dossier_${norad}_${day ?? 'session'}.html`
  a.click()
  URL.revokeObjectURL(a.href)
}

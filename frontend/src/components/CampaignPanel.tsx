import { useEffect, useState } from 'react'
import Plot from 'react-plotly.js'

import { api } from '../api'
import type { CampaignDetail, CampaignSummary } from '../types'
import { MetricCard } from './MetricCard'

const config = { responsive: true, displaylogo: false }
const layout = { autosize: true, height: 330, margin: { l: 55, r: 20, t: 42, b: 90 }, paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)', font: { family: 'Inter, system-ui, sans-serif', size: 11 } }

export function CampaignPanel() {
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([])
  const [detail, setDetail] = useState<CampaignDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => { api.listCampaigns().then((items) => { setCampaigns(items); if (items[0]) return api.getCampaign(items[0].campaign_id).then(setDetail) }).catch((reason: unknown) => setError(String(reason))) }, [])
  async function select(id: string) { setDetail(await api.getCampaign(id)) }

  if (error) return <section className="panel message error">{error}</section>
  if (campaigns.length === 0) return <section className="panel" data-testid="campaign-empty"><p className="eyebrow">Frozen study</p><h2>No campaign dataset yet</h2><p>Run the reproducible baseline from PowerShell, then refresh this page:</p><code className="command-block">uv --cache-dir .uv-cache run --all-groups python -m mcp_traffic_analysis.campaigns baseline-v1</code></section>
  if (!detail) return <section className="panel">Loading campaign…</section>
  const analysis = detail.analysis
  const coefficients = analysis?.primary_model.coefficients ?? []
  return <div className="campaign-stack" data-testid="campaign-panel">
    <section className="panel"><div className="section-heading"><div><p className="eyebrow">Randomized factorial study</p><h2>Baseline campaign</h2></div><select aria-label="Campaign" value={detail.manifest.campaign_id} onChange={(event) => void select(event.target.value)}>{campaigns.map((item) => <option key={item.campaign_id}>{item.campaign_id}</option>)}</select></div><div className="study-facts"><span data-testid="campaign-progress-text"><strong>{detail.progress.completed_runs}</strong> / {detail.progress.planned_runs} runs</span><span><strong>48</strong> conditions</span><span><strong>{detail.manifest.replicates}</strong> run replicates</span><span><strong>{detail.manifest.calls_per_run}</strong> calls/run</span></div><progress max={detail.progress.planned_runs} value={detail.progress.completed_runs} /><p className="method-note">Independent unit: run. Calls are nested. Execution is randomized in complete replicate blocks.</p></section>
    {analysis ? <>
      <section className="metric-grid"><MetricCard label="Modeled runs" value={analysis.primary_model.n_runs} /><MetricCard label="Successful calls" value={analysis.counts.successful_calls} /><MetricCard label="Adjusted R²" value={analysis.primary_model.adjusted_r_squared.toFixed(3)} /><MetricCard label="Run ICC" value={analysis.mixed_model.icc === undefined ? 'Unavailable' : analysis.mixed_model.icc.toFixed(3)} /></section>
      <section className="panel statistics-panel"><div className="section-heading"><div><p className="eyebrow">Factorial OLS</p><h2>Coefficient uncertainty</h2></div><span className="phase-chip">HC3 95% CI</span></div><p className="method-note">Response: log run-median client RTT. Coefficients are relative to reference factor levels.</p><Plot data={[{ type: 'scatter', mode: 'markers', x: coefficients.map((item) => item.estimate), y: coefficients.map((item) => item.term), error_x: { type: 'data', symmetric: false, array: coefficients.map((item) => item.ci_high - item.estimate), arrayminus: coefficients.map((item) => item.estimate - item.ci_low) }, marker: { color: '#22577a', size: 8 } }]} layout={{ ...layout, title: { text: 'OLS coefficients on log latency' } }} config={config} useResizeHandler style={{ width: '100%' }} /> </section>
      <section className="statistics-grid two"><div className="panel plot-card"><Plot data={[{ type: 'scatter', mode: 'markers', x: analysis.diagnostics.fitted, y: analysis.diagnostics.residuals, marker: { color: '#3a7d78', size: 6 } }]} layout={{ ...layout, title: { text: 'Residuals vs fitted' }, xaxis: { title: { text: 'Fitted log latency' } }, yaxis: { title: { text: 'Residual' } } }} config={config} useResizeHandler style={{ width: '100%' }} /></div><div className="panel plot-card"><Plot data={[{ type: 'scatter', mode: 'markers', x: analysis.diagnostics.qq_theoretical, y: analysis.diagnostics.qq_observed, marker: { color: '#ef8354', size: 6 } }]} layout={{ ...layout, title: { text: 'Normal Q–Q diagnostic' } }} config={config} useResizeHandler style={{ width: '100%' }} /></div></section>
      <section className="panel"><div className="section-heading compact"><div><p className="eyebrow">Condition estimates</p><h2>Cluster-bootstrap intervals</h2></div><span className="count-chip">{analysis.condition_summaries.length}</span></div><div className="table-scroll"><table className="data-table"><thead><tr><th>Transport</th><th>Bytes</th><th>Service</th><th>Concurrency</th><th>Runs</th><th>Median [95% CI]</th><th>p95</th></tr></thead><tbody>{analysis.condition_summaries.map((row) => <tr key={`${row.transport}-${row.payload_target_bytes}-${row.service_time_ms}-${row.concurrency}`}><td>{row.transport}</td><td>{row.payload_target_bytes.toLocaleString()}</td><td>{row.service_time_ms} ms</td><td>{row.concurrency}</td><td>{row.n_runs}</td><td>{row.median_ms.toFixed(2)} [{row.median_ci_low.toFixed(2)}, {row.median_ci_high.toFixed(2)}]</td><td>{row.p95_ms.toFixed(2)}</td></tr>)}</tbody></table></div><div className="download-row"><a href={`/api/campaigns/${detail.manifest.campaign_id}/tables/runs.csv`}>Download runs.csv</a><a href={`/api/campaigns/${detail.manifest.campaign_id}/tables/calls.csv`}>Download calls.csv</a></div></section>
    </> : <section className="panel empty-state">Campaign is still running; model results appear after validation.</section>}
  </div>
}

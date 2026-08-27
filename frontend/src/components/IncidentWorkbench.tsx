import { useEffect, useState } from 'react'
import { api } from '../api'
import type { IncidentCampaignSummary, IncidentRunDetail, IncidentScenarioDescriptor, IncidentScenarioId } from '../types'

function ms(value: number) { return `${value.toFixed(1)} ms` }

export function IncidentWorkbench() {
  const [scenarios, setScenarios] = useState<IncidentScenarioDescriptor[]>([])
  const [scenario, setScenario] = useState<IncidentScenarioId>('checkout_failures')
  const [runs, setRuns] = useState<IncidentRunDetail[]>([])
  const [active, setActive] = useState<IncidentRunDetail | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [campaigns, setCampaigns] = useState<IncidentCampaignSummary[]>([])

  useEffect(() => { Promise.all([api.listIncidentScenarios(), api.listIncidentRuns(), api.listIncidentCampaigns()]).then(([s, r, c]) => {
    setScenarios(s); setRuns(r); setActive(r[0] ?? null); setCampaigns(c)
  }).catch((reason: unknown) => setError(String(reason))) }, [])

  async function run() {
    setBusy(true); setError(null)
    try { const result = await api.createIncidentRun(scenario); setActive(result); setRuns(current => [result, ...current]) }
    catch (reason) { setError(reason instanceof Error ? reason.message : String(reason)) }
    finally { setBusy(false) }
  }

  return <main className="workspace incident-workbench">
    <aside className="sidebar">
      <section className="panel control-panel">
        <p className="eyebrow">Real agent run</p><h2>Investigate an incident</h2>
        <label>Incident scenario<select value={scenario} onChange={event => setScenario(event.target.value as IncidentScenarioId)}>
          {scenarios.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
        </select></label>
        <p className="field-note">One fresh GPT-5.6 Sol agent and one fresh local MCP session. All remediation is simulated.</p>
        <button className="primary-button" disabled={busy} onClick={run}>{busy ? 'Agent is investigating…' : 'Run real agent'}</button>
        {error ? <div className="message error" role="alert">{error}</div> : null}
      </section>
      <section className="panel"><p className="eyebrow">Completed runs</p><h2>{runs.length} observations</h2>
        <div className="run-list">{runs.map(item => <button key={item.run_id} onClick={() => setActive(item)}>{item.scenario_id}<small>{item.score.task_success ? 'success' : 'failure'}</small></button>)}</div>
      </section>
      <section className="panel"><p className="eyebrow">Campaign results</p><h2>{campaigns.length} saved</h2>{campaigns.map(item => <div key={item.campaign_id} className="campaign-mini"><strong>{item.campaign_id}</strong><span>{item.successes}/{item.n_runs} successes · ${item.total_estimated_cost_usd.toFixed(3)}</span><a href={`/api/agent/campaigns/${item.campaign_id}/tables/runs.csv`}>runs.csv</a></div>)}</section>
    </aside>
    <div className="main-column">{!active ? <section className="panel welcome-panel"><p className="eyebrow">Start here</p><h2>Measure a real decision trace</h2><p>The agent gathers evidence through MCP, chooses a simulated action, and is scored against known ground truth.</p></section> : <>
      <section className="metric-grid">
        <div className="panel metric-card"><span>Task success</span><strong>{active.score.task_success ? 'Yes' : 'No'}</strong></div>
        <div className="panel metric-card"><span>Total latency</span><strong>{ms(active.measurement.total_latency_ms)}</strong></div>
        <div className="panel metric-card"><span>Model / MCP calls</span><strong>{active.measurement.model_call_count} / {active.measurement.mcp_call_count}</strong></div>
        <div className="panel metric-card"><span>Estimated cost</span><strong>${active.measurement.estimated_cost_usd.toFixed(4)}</strong></div>
      </section>
      <section className="panel"><p className="eyebrow">Agent conclusion</p><h2>{active.result?.diagnosis ?? active.measurement.failure_type ?? 'No structured result'}</h2>
        <p>{active.result?.resolution_summary}</p><dl className="detail-grid"><div><dt>Evidence</dt><dd>{active.result?.evidence_ids.join(', ') || '—'}</dd></div><div><dt>Action</dt><dd>{active.result ? `${active.result.selected_action} → ${active.result.action_target}` : '—'}</dd></div></dl>
      </section>
      <section className="panel"><p className="eyebrow">Latency decomposition</p><h2>L total = L model + L MCP handler + L orchestration</h2>
        <div className="decomposition"><span>Model {ms(active.measurement.model_latency_ms)}</span><span>MCP client RTT {ms(active.measurement.mcp_latency_ms)}<small> ({ms(active.measurement.server_handler_latency_ms)} handler)</small></span><span>Orchestration {ms(active.measurement.orchestration_latency_ms)}</span></div>
        {!active.measurement.decomposition_consistent ? <p className="message error">Timing reconciliation is inconsistent; the residual was retained, not clipped.</p> : null}
      </section>
      <section className="panel"><p className="eyebrow">Observed execution trace</p><h2>{active.measurement.tool_sequence.length} ordered MCP calls</h2>
        <ol className="timeline-list">{active.measurement.tool_sequence.map((tool, index) => <li key={`${tool}-${index}`}><span>{index + 1}</span>{tool}</li>)}</ol>
        <p className="field-note">Tokens: {active.measurement.input_tokens} input + {active.measurement.output_tokens} output. Bytes: {active.measurement.request_frame_bytes} request / {active.measurement.response_frame_bytes} response.</p>
      </section>
      <section className="panel"><p className="eyebrow">Objective score</p><div className="score-grid">{Object.entries(active.score).filter(([key]) => key !== 'task_success').map(([key, value]) => <div key={key} className={value ? 'pass' : 'fail'}>{value ? '✓' : '×'} {key.replaceAll('_', ' ')}</div>)}</div></section>
    </>}</div>
  </main>
}

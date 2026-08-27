import { useEffect, useMemo, useState } from 'react'
import Plot from 'react-plotly.js'

import { api } from '../api'
import type {
  BehaviorCampaignAnalysis,
  BehaviorCondition,
  IncidentRunDetail,
  IncidentScenarioId,
  TaskStructure,
} from '../types'

const structureText: Record<TaskStructure, string> = {
  sequential: 'Evidence is gathered in a prescribed order.',
  branching: 'Observed metrics determine which evidence source is relevant.',
  recovery: 'A safe first action is deliberately rejected, then retried after guidance.',
}

function format(value: number, digits = 2) {
  return value.toFixed(digits)
}

export function BehaviorWorkbench() {
  const [conditions, setConditions] = useState<BehaviorCondition[]>([])
  const [runs, setRuns] = useState<IncidentRunDetail[]>([])
  const [campaigns, setCampaigns] = useState<BehaviorCampaignAnalysis[]>([])
  const [scenario, setScenario] = useState<IncidentScenarioId>('checkout_failures')
  const [structure, setStructure] = useState<TaskStructure>('sequential')
  const [mode, setMode] = useState<'live' | 'deterministic'>('deterministic')
  const [active, setActive] = useState<IncidentRunDetail | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    const [nextConditions, nextRuns, nextCampaigns] = await Promise.all([
      api.listBehaviorConditions(),
      api.listBehaviorRuns(),
      api.listBehaviorCampaigns(),
    ])
    setConditions(nextConditions)
    setRuns(nextRuns)
    setCampaigns(nextCampaigns)
    setActive((current) => current ?? nextRuns[0] ?? null)
  }

  useEffect(() => {
    void load().catch((reason: unknown) => setError(String(reason)))
  }, [])

  const condition = useMemo(
    () => conditions.find((item) => item.scenario_id === scenario && item.task_structure === structure),
    [conditions, scenario, structure],
  )
  const scenarios = useMemo(
    () => [...new Map(conditions.map((item) => [item.scenario_id, item])).values()],
    [conditions],
  )
  const latestCampaign = campaigns.at(-1) ?? null
  const coefficients = latestCampaign?.primary_model?.primary?.coefficients ?? []
  const structureEffects = coefficients.filter((item) => item.term.includes('task_structure'))

  async function run() {
    setBusy(true)
    setError(null)
    try {
      const detail = await api.createBehaviorRun(scenario, structure, mode)
      setActive(detail)
      setRuns((current) => [detail, ...current.filter((item) => item.run_id !== detail.run_id)])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  return <main className="workspace behavior-workbench" data-testid="behavior-workbench">
    <aside className="sidebar">
      <section className="panel control-panel">
        <div className="section-heading"><div><p className="eyebrow">Phase 4 experiment</p><h2>Run one task</h2></div><span className="phase-chip">4</span></div>
        <label>Incident ticket<select aria-label="Incident ticket" value={scenario} onChange={(event) => setScenario(event.target.value as IncidentScenarioId)}>{scenarios.map((item) => <option key={item.scenario_id} value={item.scenario_id}>{item.label}</option>)}</select></label>
        <label>Hidden task structure<select aria-label="Task structure" value={structure} onChange={(event) => setStructure(event.target.value as TaskStructure)}><option value="sequential">Sequential</option><option value="branching">Conditional branching</option><option value="recovery">Failure recovery</option></select></label>
        <p className="field-note">{structureText[structure]}</p>
        <label>Execution<select aria-label="Execution mode" value={mode} onChange={(event) => setMode(event.target.value as 'live' | 'deterministic')}><option value="deterministic">Scripted validation — no model cost</option><option value="live">Real model measurement</option></select></label>
        <button disabled={busy || !condition} onClick={() => void run()}>{busy ? 'Running…' : 'Run task'}</button>
        <p className="field-note">Repeated paid campaigns remain CLI-only.</p>
      </section>
      <section className="panel"><p className="eyebrow">Saved Phase 4 runs</p><h2>{runs.length}</h2><div className="run-list">{runs.slice(0, 8).map((item) => <button className="run-select" key={item.run_id} onClick={() => setActive(item)}><strong>{item.behavior?.task_structure}</strong><span>{item.scenario_id.replaceAll('_', ' ')}</span></button>)}</div></section>
    </aside>

    <div className="main-column">
      {error ? <div className="message error" role="alert">{error}</div> : null}
      <section className="panel study-question">
        <p className="eyebrow">Study question</p><h2>Does task structure change how much MCP work an agent performs?</h2>
        <div className="control-grid"><div><strong>Varied</strong><span>Sequential, branching, recovery</span></div><div><strong>Held fixed</strong><span>Ticket, model, prompt policy, tools, stdio transport</span></div><div><strong>Experimental unit</strong><span>One fresh agent run and MCP session</span></div></div>
      </section>
      <section className="panel ticket-card"><p className="eyebrow">Simulated incoming incident ticket</p><h2>{condition?.label ?? 'Choose a task'}</h2><blockquote>{condition?.incoming_message ?? 'Loading the frozen task bank…'}</blockquote><p className="field-note">This is synthetic. The application does not read Outlook or contact a production system.</p></section>

      {!active?.behavior ? <section className="panel welcome-panel"><p className="eyebrow">Start here</p><h2>Run a matched task condition</h2><p>Use scripted validation to inspect the five-call oracle without model cost, or choose a live run to observe a stochastic agent trace.</p></section> : <>
        <section className="metric-grid behavior-metrics">
          <div className="panel metric-card"><span>Task success</span><strong>{active.score.task_success ? 'Yes' : 'No'}</strong></div>
          <div className="panel metric-card"><span>MCP calls</span><strong>{active.measurement.mcp_call_count}</strong></div>
          <div className="panel metric-card"><span>Excess calls</span><strong>{active.behavior.excess_mcp_calls ?? 'N/A'}</strong></div>
          <div className="panel metric-card"><span>Oracle distance</span><strong>{format(active.behavior.normalized_oracle_distance, 3)}</strong></div>
        </section>
        {active.behavior.execution_mode === 'scripted_validation' ? <div className="message warning">Scripted structural validation: tool order and scoring are validated, but latency, model tokens, and stdio frame bytes are not measured.</div> : <div className="message success">Live measurement: exact stdio request and response frame bytes were observed.</div>}
        <section className="trace-comparison">
          <div className="panel"><p className="eyebrow">Observed trace</p><h2>{active.behavior.observed_sequence.length} calls</h2><ol className="timeline-list">{active.behavior.trace_steps.map((step) => <li key={step.sequence} className={`trace-${step.classification}`}><span>{step.sequence + 1}</span><div><strong>{step.tool_name}</strong><small>{step.classification.replaceAll('_', ' ')}</small></div></li>)}</ol></div>
          <div className="panel"><p className="eyebrow">Shortest valid trace</p><h2>Five-call oracle</h2><ol className="timeline-list">{active.behavior.oracle_sequence.map((tool, index) => <li key={`${tool}-${index}`}><span>{index + 1}</span>{tool}</li>)}</ol></div>
        </section>
        <section className="panel"><p className="eyebrow">Measurement boundary</p><div className="study-facts"><span><strong>{format(active.measurement.total_latency_ms)}</strong> ms total</span><span><strong>{active.measurement.total_tokens}</strong> tokens</span><span><strong>{active.behavior.request_frame_bytes ?? 'Unavailable'}</strong> request bytes</span><span><strong>{active.behavior.response_frame_bytes ?? 'Unavailable'}</strong> response bytes</span></div></section>
      </>}

      <section className="panel" data-testid="behavior-campaign">
        <div className="section-heading"><div><p className="eyebrow">Saved campaign analysis</p><h2>{latestCampaign ? `${latestCampaign.campaign_id} · ${latestCampaign.n_runs} runs` : 'No campaign dataset yet'}</h2></div>{latestCampaign ? <span className="count-chip">{latestCampaign.study_stage}</span> : null}</div>
        {!latestCampaign ? <p>Run the frozen pilot from PowerShell, then refresh:</p> : <>
          <p className="method-note">Primary outcome: MCP calls. Sequential is the reference structure. Effect ratios above 1 mean more calls. {latestCampaign.study_stage === 'pilot' ? 'Pilot coefficients diagnose the design; they are not confirmatory results.' : 'Holm adjustment covers the two planned structure contrasts.'}</p>
          <div className="table-scroll"><table className="data-table"><thead><tr><th>Structure contrast</th><th>Call ratio</th><th>95% interval</th><th>Raw p</th><th>Holm p</th></tr></thead><tbody>{structureEffects.map((row) => <tr key={row.term}><td>{row.term.includes('branching') ? 'Branching vs sequential' : 'Recovery vs sequential'}</td><td>{row.effect_ratio ? format(row.effect_ratio) : '—'}</td><td>{row.effect_ratio_ci ? `${format(row.effect_ratio_ci[0])}–${format(row.effect_ratio_ci[1])}` : '—'}</td><td>{format(row.p_value, 3)}</td><td>{row.p_value_holm === null ? '—' : format(row.p_value_holm, 3)}</td></tr>)}</tbody></table></div>
          <div className="statistics-grid two behavior-plots">
            <div className="plot-card"><h3>Empirical CDF of MCP calls</h3><Plot data={(latestCampaign.mcp_call_distributions ?? []).map((distribution) => ({ x: distribution.ecdf.map((point) => point.value), y: distribution.ecdf.map((point) => point.probability), name: distribution.task_structure, type: 'scatter', mode: 'lines+markers', line: { shape: 'hv' } }))} layout={{ autosize: true, height: 300, margin: { l: 45, r: 15, t: 10, b: 45 }, xaxis: { title: { text: 'MCP calls' } }, yaxis: { title: { text: 'Empirical probability' }, range: [0, 1] }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', legend: { orientation: 'h' } }} config={{ displayModeBar: false, responsive: true }} useResizeHandler style={{ width: '100%' }} /></div>
            <div className="plot-card"><h3>Empirical transition probabilities</h3><div className="transition-grid">{latestCampaign.transition_summary?.slice(0, 18).map((row) => <div key={`${row.task_structure}-${row.source_tool}-${row.target_tool}`} style={{ background: `rgba(58, 125, 120, ${0.08 + row.probability * 0.32})` }}><strong>{row.task_structure}</strong><span>{row.source_tool} → {row.target_tool}</span><b>{format(row.probability, 2)}</b></div>)}</div><p className="field-note">Row-normalized observed transitions. This is descriptive and does not assert a Markov model.</p></div>
          </div>
          <h3>Condition summaries</h3><div className="table-scroll"><table className="data-table"><thead><tr><th>Task</th><th>Structure</th><th>Runs</th><th>Success</th><th>Median calls</th><th>Unique paths</th><th>Entropy</th></tr></thead><tbody>{latestCampaign.condition_summaries?.map((row) => <tr key={`${row.scenario_id}-${row.task_structure}`}><td>{row.scenario_id.replaceAll('_', ' ')}</td><td>{row.task_structure}</td><td>{row.n_runs}</td><td>{row.successes}/{row.n_runs}</td><td>{format(row.median_mcp_calls, 1)}</td><td>{row.unique_paths}</td><td>{format(row.path_entropy_bits, 2)} bits</td></tr>)}</tbody></table></div>
          <div className="download-row"><a href={`/api/behavior/campaigns/${latestCampaign.campaign_id}/tables/runs.csv`}>runs.csv</a><a href={`/api/behavior/campaigns/${latestCampaign.campaign_id}/tables/traces.csv`}>traces.csv</a><a href={`/api/behavior/campaigns/${latestCampaign.campaign_id}/tables/transitions.csv`}>transitions.csv</a></div>
        </>}
      </section>
    </div>
  </main>
}

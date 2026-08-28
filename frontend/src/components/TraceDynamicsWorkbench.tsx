import { useEffect, useMemo, useState } from 'react'
import Plot from 'react-plotly.js'

import { api } from '../api'
import type { TraceStudyAnalysis } from '../types'

function percentage(value: number | null, digits = 1) {
  return value === null ? 'Not estimable' : `${(value * 100).toFixed(digits)}%`
}

function interval(value: [number, number] | null) {
  return value === null ? 'Not estimable' : `${percentage(value[0])} to ${percentage(value[1])}`
}

function numericInterval(field: string, value: [number, number] | null | undefined) {
  if (value === null || value === undefined) return 'Not estimable'
  return `${scalarValue(field, value[0])} to ${scalarValue(field, value[1])}`
}

function shortState(value: string) {
  return value.replace('|', ' · ').replaceAll('_', ' ')
}

function measured(value: number | null | undefined, digits = 1) {
  return value === null || value === undefined ? 'Unavailable' : value.toFixed(digits)
}

function scalarValue(field: string, value: number | null | undefined) {
  if (value === null || value === undefined) return 'Unavailable'
  if (field === 'estimated_cost_usd') return `$${value.toFixed(4)}`
  if (field === 'total_tokens' || field.endsWith('_bytes')) return value.toFixed(0)
  if (field === 'task_success') return percentage(value)
  return measured(value)
}

export function TraceDynamicsWorkbench() {
  const [campaigns, setCampaigns] = useState<TraceStudyAnalysis[]>([])
  const [campaignId, setCampaignId] = useState('')
  const [selectedRun, setSelectedRun] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void api.listTraceStudyCampaigns().then((values) => {
      setCampaigns(values)
      const preferred = [...values].reverse().find((item) => item.study_stage === 'main')
        ?? values.at(-1)
      setCampaignId(preferred?.campaign_id ?? '')
    }).catch((reason: unknown) => setError(String(reason)))
  }, [])

  const campaign = campaigns.find((item) => item.campaign_id === campaignId) ?? null
  const focusedSummary = campaign?.condition_summaries.find(
    (item) => item.scenario_id === 'orders_api_outage' && item.task_structure === 'recovery',
  ) ?? null
  const paths = useMemo(() => (campaign?.path_summary ?? [])
    .filter((item) => item.scenario_id === 'orders_api_outage' && item.task_structure === 'recovery')
    .sort((left, right) => right.count - left.count), [campaign])
  const transitions = useMemo(() => (campaign?.transition_summary ?? [])
    .filter((item) => item.scenario_id === 'orders_api_outage' && item.task_structure === 'recovery')
    .sort((left, right) => right.count - left.count), [campaign])
  const focusedTraces = useMemo(() => (campaign?.trace_examples ?? [])
    .filter((item) => item.scenario_id === 'orders_api_outage' && item.task_structure === 'recovery'), [campaign])
  const successTrace = focusedTraces.find((item) => item.task_success) ?? null
  const failureTrace = focusedTraces.find((item) => !item.task_success) ?? null
  const activeTrace = focusedTraces.find((item) => item.run_id === selectedRun)
    ?? failureTrace ?? successTrace
  const post = campaign?.post_rejection_analysis ?? null

  useEffect(() => {
    setSelectedRun('')
  }, [campaignId])

  function traceCard(title: string, trace: typeof successTrace) {
    if (!trace) return <div className="empty-trace">No {title.toLowerCase()} is available.</div>
    return <div className="trace-lane">
      <h3>{title}</h3>
      <ol>{trace.state_sequence.split(' > ').map((state, index) => <li
        key={`${state}-${index}`}
        className={trace.first_oracle_divergence === index ? 'divergence' : ''}
      ><span>{index}</span>{shortState(state)}</li>)}</ol>
    </div>
  }

  return <main className="trace-workbench" data-testid="trace-dynamics-workbench">
    <section className="panel trace-intro">
      <div><p className="eyebrow">Phase 5 · practical question</p><h2>What does the agent do after escalation is rejected?</h2></div>
      <blockquote>“The Orders API is returning 503 errors. Investigate and resolve the incident.”</blockquote>
      <div className="plain-flow"><span>Escalation rejected</span><b>→</b><span>Read runbook or retry?</span><b>→</b><span>Success or failure</span></div>
      <p>The statistics below count those observable choices over repeated runs. They do not infer the model's private reasoning.</p>
    </section>

    {error ? <div className="message error" role="alert">{error}</div> : null}
    {!campaign ? <section className="panel welcome-panel"><h2>No Phase 5 analysis yet</h2><p>Run the credit-free Phase 4 reanalysis, then refresh this page.</p></section> : <>
      <section className="panel campaign-control">
        <label>Dataset<select aria-label="Trace study dataset" value={campaignId} onChange={(event) => setCampaignId(event.target.value)}>{campaigns.map((item) => <option key={item.campaign_id} value={item.campaign_id}>{item.campaign_id} · {item.n_runs} runs</option>)}</select></label>
        <div><strong>{campaign.study_stage === 'exploratory' ? 'Reused Phase 4 evidence' : `New Phase 5 ${campaign.study_stage} evidence`}</strong><span>{campaign.study_stage === 'exploratory' ? 'No new model calls' : campaign.campaign_complete ? 'Complete campaign' : 'Incomplete campaign'}</span></div>
      </section>

      {campaign.primary_intervention_result && campaign.intervention_arms ? <section className="panel primary-result" data-testid="intervention-result">
        <p className="eyebrow">Phase 13 · randomized policy intervention</p>
        <h2>Does assigning runbook-first recovery improve success?</h2>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>Assigned policy</th><th>Runs</th><th>Successes</th><th>Success rate</th><th>95% interval</th></tr></thead><tbody>{campaign.intervention_arms.map((row) => <tr key={row.arm}><td>{row.arm === 'runbook_first' ? 'Runbook first' : 'Normal policy'}</td><td>{row.assigned_runs}</td><td>{row.successes}</td><td>{percentage(row.success_rate)}</td><td>{interval(row.success_rate_wilson_95)}</td></tr>)}</tbody></table></div>
        <div className="plain-result"><strong>Assigned-policy success difference: {percentage(campaign.primary_intervention_result.risk_difference)}</strong><span>95% interval: {interval(campaign.primary_intervention_result.risk_difference_newcombe_95)}</span></div>
        <div className="download-row"><a href={`/api/trace-study/campaigns/${campaign.campaign_id}/artifacts/q16_randomized_intervention.json`}>Download intervention result</a></div>
        <p className="method-note">This compares randomized policy assignment under one synthetic incident configuration. It does not measure private reasoning or claim a universal production effect. {campaign.causal_interpretation_limit}</p>
      </section> : null}

      {campaign.scalar_distributions?.length ? <section className="panel" data-testid="scalar-baseline">
        <p className="eyebrow">Phase 8 · scalar baseline</p>
        <h2>Start with one run and its basic measurements</h2>
        <p>Each fresh run is one observation. These summaries describe the distributions of scalar outcomes before we study complete execution paths. Intervals show sampling uncertainty within this campaign; they are not guarantees about all agents.</p>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>Measure</th><th>Type</th><th>Unit</th><th>n</th><th>Missing</th><th>Mean</th><th>Mean 95% interval</th><th>Median</th><th>Q1–Q3</th><th>Range</th></tr></thead><tbody>{campaign.scalar_distributions.map((row) => <tr key={row.field}><td>{row.label}</td><td>{row.type}</td><td>{row.unit}</td><td>{row.n}</td><td>{row.missing}</td><td>{scalarValue(row.field, row.mean)}</td><td>{row.field === 'task_success' ? interval(row.proportion_wilson_95 ?? null) : numericInterval(row.field, row.mean_bootstrap_95)}</td><td>{scalarValue(row.field, row.median)}</td><td>{scalarValue(row.field, row.q1)}–{scalarValue(row.field, row.q3)}</td><td>{scalarValue(row.field, row.minimum)}–{scalarValue(row.field, row.maximum)}</td></tr>)}</tbody></table></div>
        <div className="download-row"><a href={`/api/trace-study/campaigns/${campaign.campaign_id}/artifacts/q01_data_dictionary.json`}>Download data dictionary</a><a href={`/api/trace-study/campaigns/${campaign.campaign_id}/artifacts/q02_scalar_distributions.json`}>Download scalar distributions</a><a href={`/api/trace-study/campaigns/${campaign.campaign_id}/artifacts/q03_batch_stability.json`}>Download batch stability</a><a href={`/api/trace-study/campaigns/${campaign.campaign_id}/artifacts/q09_q14_trajectory_analysis.json`}>Download trajectory contract</a></div>
        <p className="method-note">Statuses are defined in the data dictionary. Local stdio frame bytes are measured application data, not network packets; estimated cost is derived.</p>
      </section> : null}

      {campaign.batch_summaries.length ? <section className="panel" data-testid="batch-stability">
        <p className="eyebrow">Q03 · stability diagnostic</p><h2>Do the repeated batches look stable?</h2>
        <p>These are descriptive comparisons across acquisition batches. They help us notice drift; they are not a time-series model.</p>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>Batch</th><th>Runs</th><th>Success rate</th><th>Success 95% interval</th><th>Runbook-first</th><th>Mean calls</th><th>Median calls</th><th>Mean latency (ms)</th><th>Median latency (ms)</th><th>Mean tokens</th></tr></thead><tbody>{campaign.batch_summaries.map((row) => <tr key={row.batch}><td>{row.batch}</td><td>{row.n_runs}</td><td>{percentage(row.success_rate)}</td><td>{interval(row.success_rate_wilson_95 ?? null)}</td><td>{percentage(row.read_runbook_first_rate)}</td><td>{measured(row.mean_mcp_calls)}</td><td>{measured(row.median_mcp_calls)}</td><td>{measured(row.mean_total_latency_ms)}</td><td>{measured(row.median_total_latency_ms)}</td><td>{measured(row.mean_total_tokens, 0)}</td></tr>)}</tbody></table></div>
      </section> : null}

      {campaign.campaign_complete === false ? <section className="panel campaign-warning" role="status">
        <p className="eyebrow">Incomplete acquisition</p>
        <h2>{campaign.n_runs} of {campaign.planned_runs ?? '?'} valid runs are available</h2>
        <p>{campaign.excluded_provider_attempts ?? 0} provider-error attempts are preserved for audit and excluded from all scientific statistics. These are interim results until the frozen schedule is complete.</p>
      </section> : null}

      <section className="metric-grid">
        <div className="panel metric-card"><span>Focused runs</span><strong>{post?.focused_runs ?? 0}</strong></div>
        <div className="panel metric-card"><span>Successful runs</span><strong>{focusedSummary?.successes ?? 0}/{focusedSummary?.n_runs ?? 0}</strong></div>
        <div className="panel metric-card"><span>Distinct paths</span><strong>{focusedSummary?.unique_paths ?? 0}</strong></div>
        <div className="panel metric-card"><span>Failure-rate difference</span><strong>{percentage(post?.failure_risk_difference_retry_minus_read ?? null)}</strong></div>
      </section>

      <section className="panel primary-result" data-testid="post-rejection-result">
        <p className="eyebrow">Question 1 · behaviour and failure</p>
        <h2>Did the agent read the runbook before trying another action?</h2>
        <div className="table-scroll"><table className="data-table outcome-table"><thead><tr><th>After rejection</th><th>Success</th><th>Failure</th><th>Failure rate</th><th>95% interval</th></tr></thead><tbody>
          <tr><td>Read runbook first</td><td>{post?.counts.read_runbook_first.success}</td><td>{post?.counts.read_runbook_first.failure}</td><td>{percentage(post?.failure_rate_read_runbook_first ?? null)}</td><td>{interval(post?.failure_rate_read_runbook_first_wilson_95 ?? null)}</td></tr>
          <tr><td>Retried first</td><td>{post?.counts.retried_first.success}</td><td>{post?.counts.retried_first.failure}</td><td>{percentage(post?.failure_rate_retried_first ?? null)}</td><td>{interval(post?.failure_rate_retried_first_wilson_95 ?? null)}</td></tr>
        </tbody></table></div>
        <div className="plain-result"><strong>Observed difference: {percentage(post?.failure_risk_difference_retry_minus_read ?? null)}</strong><span>95% interval: {interval(post?.failure_risk_difference_newcombe_95 ?? null)}</span></div>
        <p className="method-note">{post?.interpretation_limit} {post?.classified_runs ?? 0} of {post?.focused_runs ?? 0} focused runs entered the two behaviour groups; {post?.unclassified_runs ?? 0} lacked the required rejection/follow-up sequence. Counts come first because a percentage based on five runs is not as precise as one based on one hundred.</p>
      </section>

      {campaign.prefix_outcomes?.length ? <section className="panel">
        <p className="eyebrow">Secondary analysis · partial histories</p><h2>Where does failure become visible?</h2>
        <p>These are observed prefixes of the trace, not predictions from private model reasoning.</p>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>Observed prefix</th><th>Runs</th><th>Successes</th><th>Failures</th><th>Failure rate</th><th>95% interval</th></tr></thead><tbody>{campaign.prefix_outcomes.filter((row) => row.n_runs > 0).map((row) => <tr key={row.prefix}><td>{row.prefix.replaceAll('_', ' ')}</td><td>{row.n_runs}</td><td>{row.successes}</td><td>{row.failures}</td><td>{percentage(row.failure_rate)}</td><td>{interval(row.failure_rate_wilson_95)}</td></tr>)}</tbody></table></div>
        <p className="method-note">A prefix is an observed history. These percentages are conditional summaries, not a fitted Markov model.</p>
      </section> : null}

      {campaign.tool_usage?.length ? <section className="panel">
        <p className="eyebrow">Secondary analysis · tool traffic</p><h2>Which tools dominate the work?</h2>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>Tool</th><th>Invocations</th><th>Share of calls</th><th>Runs using tool</th><th>Successful runs</th></tr></thead><tbody>{campaign.tool_usage.map((row) => <tr key={row.tool_name}><td>{row.tool_name.replaceAll('_', ' ')}</td><td>{row.invocations}</td><td>{percentage(row.invocation_proportion)}</td><td>{row.runs}</td><td>{row.successful_runs}</td></tr>)}</tbody></table></div>
        <p className="method-note">Invocation counts are available by tool. Per-tool bytes and latency are unavailable because the current recorder stores those quantities at run level.</p>
      </section> : null}

      <section className="panel">
        <p className="eyebrow">Where paths separate</p><h2>One successful trace and one failed trace</h2>
        <div className="trace-lanes">{traceCard('Successful run', successTrace)}{traceCard('Failed run', failureTrace)}</div>
        <p className="field-note">The highlighted step is the first position that differs from the five-call oracle. Tool outcomes come from the recorded synthetic action ledger.</p>
      </section>

      <section className="statistics-grid two">
        <div className="panel plot-card"><p className="eyebrow">Question 2 · path variability</p><h2>Most common complete paths</h2><Plot data={[{ type: 'bar', orientation: 'h', x: paths.slice(0, 8).map((item) => item.count).reverse(), y: paths.slice(0, 8).map((_, index) => `Path ${index + 1}`).reverse(), marker: { color: '#3a7d78' } }]} layout={{ autosize: true, height: 320, margin: { l: 70, r: 15, t: 10, b: 45 }, xaxis: { title: { text: 'Observed runs' } }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent' }} config={{ displayModeBar: false, responsive: true }} useResizeHandler style={{ width: '100%' }} /><p className="method-note">{focusedSummary?.unique_paths} paths; entropy {focusedSummary?.path_entropy_bits.toFixed(2)} bits. The path table, not entropy alone, carries the practical meaning.</p></div>
        <div className="panel plot-card"><p className="eyebrow">One-step movements</p><h2>Observed transition probabilities</h2><div className="transition-grid phase5-transitions">{transitions.slice(0, 18).map((row) => <div key={`${row.source_state}-${row.target_state}`} style={{ background: `rgba(58, 125, 120, ${0.08 + row.probability * 0.32})` }}><span>{shortState(row.source_state)} → {shortState(row.target_state)}</span><b>{row.count} · {percentage(row.probability, 0)}</b></div>)}</div><p className="method-note">Counts and row-normalized percentages only. No Markov model is claimed.</p></div>
      </section>

      <section className="panel"><p className="eyebrow">Complete path counts</p><h2>What does each path label mean?</h2><div className="table-scroll"><table className="data-table path-table"><thead><tr><th>Path</th><th>Runs</th><th>Observed percentage</th><th>Ordered tool-and-outcome states</th></tr></thead><tbody>{paths.slice(0, 12).map((path, index) => <tr key={path.state_sequence}><td>Path {index + 1}</td><td>{path.count}</td><td>{percentage(path.proportion)}</td><td className="path-cell">{path.state_sequence.split(' > ').map(shortState).join(' → ')}</td></tr>)}</tbody></table></div></section>

      {campaign.path_concentration?.length ? <section className="panel"><p className="eyebrow">Secondary analysis · path concentration</p><h2>How quickly do common paths cover the runs?</h2><div className="table-scroll"><table className="data-table"><thead><tr><th>Rank</th><th>Path count</th><th>Cumulative coverage</th><th>Path</th></tr></thead><tbody>{campaign.path_concentration.slice(0, 10).map((row) => <tr key={row.rank}><td>{row.rank}</td><td>{row.count}</td><td>{percentage(row.cumulative_proportion)}</td><td className="path-cell">{row.state_sequence.split(' > ').map(shortState).join(' → ')}</td></tr>)}</tbody></table></div><p className="method-note">Paths are ordered from most frequent to least frequent. Coverage is descriptive and calculated from complete run traces.</p></section> : null}

      <section className="panel efficiency-panel">
        <p className="eyebrow">Question 3 · action efficiency</p><h2>Calls beyond the five-call valid path</h2>
        <div className="study-facts"><span><strong>{focusedSummary?.exact_oracle_successes ?? 0}</strong> exact-oracle successes</span><span><strong>{focusedSummary?.successful_excess_calls.median ?? 'N/A'}</strong> median excess calls</span><span><strong>{focusedSummary?.successful_excess_calls.q1 ?? 'N/A'}–{focusedSummary?.successful_excess_calls.q3 ?? 'N/A'}</strong> interquartile range</span><span><strong>{focusedSummary?.successful_excess_calls.minimum ?? 'N/A'}–{focusedSummary?.successful_excess_calls.maximum ?? 'N/A'}</strong> observed range</span></div>
        <p>Excess calls are defined only for successful runs. Failed runs did not complete a valid path, so the UI does not invent a successful-path excess value for them.</p>
      </section>

      <section className="panel"><p className="eyebrow">Supporting performance measurements</p><h2>How much measured work did a focused run require?</h2><div className="table-scroll"><table className="data-table"><thead><tr><th>Quantity</th><th>Available runs</th><th>Median</th><th>Interquartile range</th><th>Observed range</th></tr></thead><tbody>{[
        ['MCP calls', 'mcp_call_count', 1],
        ['Total latency (ms)', 'total_latency_ms', 1],
        ['Model tokens', 'total_tokens', 0],
        ['Request frame bytes', 'request_frame_bytes', 0],
        ['Response frame bytes', 'response_frame_bytes', 0],
        ['Estimated cost (USD)', 'estimated_cost_usd', 4],
      ].map(([label, key, digits]) => {
        const summary = campaign.focused_measurements[String(key)]
        return <tr key={String(key)}><td>{label}</td><td>{summary?.n ?? 0}</td><td>{measured(summary?.median, Number(digits))}</td><td>{measured(summary?.q1, Number(digits))}–{measured(summary?.q3, Number(digits))}</td><td>{measured(summary?.minimum, Number(digits))}–{measured(summary?.maximum, Number(digits))}</td></tr>
      })}</tbody></table></div><p className="method-note">{campaign.measurement_boundary}</p></section>

      {campaign.latency_decomposition?.length ? <section className="panel">
        <p className="eyebrow">Secondary analysis · runtime components</p><h2>Where does the runtime go?</h2>
        <div className="table-scroll"><table className="data-table"><thead><tr><th>Component</th><th>Median ms</th><th>Median share</th><th>Correlation with total</th></tr></thead><tbody>{campaign.latency_decomposition.map((row) => <tr key={row.component}><td>{row.component.replaceAll('_', ' ').replace(' ms', '')}</td><td>{measured(row.median)}</td><td>{percentage(row.median_share_of_total)}</td><td>{measured(row.correlation_with_total, 2)}</td></tr>)}</tbody></table></div>
        <p className="method-note">Component shares describe this measured run decomposition; they do not estimate queueing delay or network transmission time.</p>
      </section> : null}

      {campaign.divergence_by_outcome?.length ? <section className="panel">
        <p className="eyebrow">Secondary analysis · oracle divergence</p><h2>When do successful and failed traces depart?</h2>
        <div className="study-facts">{campaign.divergence_by_outcome.map((row) => <span key={row.outcome}><strong>{row.median ?? 'N/A'}</strong> median step for {row.outcome} traces <small>({row.n_runs} runs)</small></span>)}</div>
        <p className="method-note">The step number is an index in the observed tool sequence, not a model-internal reasoning step.</p>
      </section> : null}

      {campaign.batch_summaries.length > 1 ? <section className="panel"><p className="eyebrow">Acquisition diagnostic</p><h2>Did behaviour change across batches?</h2><Plot data={[{ x: campaign.batch_summaries.map((row) => row.batch), y: campaign.batch_summaries.map((row) => row.success_rate), name: 'Success rate', type: 'scatter', mode: 'lines+markers' }, { x: campaign.batch_summaries.map((row) => row.batch), y: campaign.batch_summaries.map((row) => row.read_runbook_first_rate), name: 'Read runbook first', type: 'scatter', mode: 'lines+markers' }]} layout={{ autosize: true, height: 280, margin: { l: 50, r: 15, t: 10, b: 45 }, xaxis: { title: { text: 'Batch' } }, yaxis: { title: { text: 'Observed proportion' }, range: [0, 1] }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', legend: { orientation: 'h' } }} config={{ displayModeBar: false, responsive: true }} useResizeHandler style={{ width: '100%' }} /><p className="method-note">A diagnostic for time-related drift, not an additional hypothesis test.</p></section> : null}

      <section className="panel trace-explorer"><p className="eyebrow">Raw observation</p><h2>Inspect one focused trace</h2><label>Run<select aria-label="Focused trace" value={activeTrace?.run_id ?? ''} onChange={(event) => setSelectedRun(event.target.value)}>{focusedTraces.map((trace) => <option key={trace.run_id} value={trace.run_id}>{trace.task_success ? 'Success' : 'Failure'} · order {trace.execution_order ?? 'unknown'} · {trace.run_id.slice(0, 8)}</option>)}</select></label>{activeTrace ? <ol className="raw-trace">{activeTrace.state_sequence.split(' > ').map((state, index) => <li key={`${state}-${index}`}>{shortState(state)}</li>)}</ol> : null}</section>

      <section className="panel"><p className="eyebrow">Auditable artifacts</p><div className="download-row">{['runs.csv', 'traces.csv', 'paths.csv', 'transitions.csv', 'post_rejection_outcomes.csv', 'prefix_outcomes.csv', 'tool_usage.csv', 'latency_components.csv', 'divergence.csv', 'path_concentration.csv'].map((name) => <a key={name} href={`/api/trace-study/campaigns/${campaign.campaign_id}/tables/${name}`}>{name}</a>)}</div></section>
    </>}
  </main>
}

import { useEffect, useState } from 'react'

import { api } from './api'
import { EventTable } from './components/EventTable'
import { CampaignPanel } from './components/CampaignPanel'
import { ExperimentForm } from './components/ExperimentForm'
import { MetricCard } from './components/MetricCard'
import { RunBrowser } from './components/RunBrowser'
import { StatisticsPanel } from './components/StatisticsPanel'
import { TraceTimeline } from './components/TraceTimeline'
import { Phase2RunForm } from './components/Phase2RunForm'
import { Phase2RunResult } from './components/Phase2RunResult'
import type { AnalysisResponse, Phase2RunParameters, Phase2RunResponse, RunDetail, RunParameters, RunSummary, ScenarioDescriptor, TraceEvent } from './types'

function number(value: number | null, suffix = '') {
  return value === null ? '—' : `${value.toFixed(2)}${suffix}`
}

export default function App() {
  const [scenarios, setScenarios] = useState<ScenarioDescriptor[]>([])
  const [runs, setRuns] = useState<RunSummary[]>([])
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [detail, setDetail] = useState<RunDetail | null>(null)
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null)
  const [unit, setUnit] = useState<'call' | 'run'>('call')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [view, setView] = useState<'calibration' | 'study'>('study')
  const [phase2Run, setPhase2Run] = useState<Phase2RunResponse | null>(null)
  const [phase2Busy, setPhase2Busy] = useState(false)

  async function refreshRuns(preferredRunId?: string) {
    const nextRuns = await api.listRuns()
    setRuns(nextRuns)
    const nextActive = preferredRunId ?? activeId ?? nextRuns[0]?.run_id ?? null
    setActiveId(nextActive)
    if (preferredRunId) setSelectedIds([preferredRunId])
    else if (selectedIds.length === 0 && nextActive) setSelectedIds([nextActive])
  }

  useEffect(() => {
    let current = true
    Promise.all([api.listScenarios(), api.listRuns()])
      .then(([nextScenarios, nextRuns]) => {
        if (!current) return
        setScenarios(nextScenarios)
        setRuns(nextRuns)
        const first = nextRuns[0]?.run_id ?? null
        setActiveId(first)
        setSelectedIds(first ? [first] : [])
      })
      .catch((reason: unknown) => current && setError(String(reason)))
      .finally(() => current && setLoading(false))
    return () => { current = false }
  }, [])

  useEffect(() => {
    let current = true
    if (!activeId) {
      setDetail(null)
      setEvents([])
      return
    }
    Promise.all([api.getRun(activeId), api.getEvents(activeId)])
      .then(([nextDetail, nextEvents]) => {
        if (!current) return
        setDetail(nextDetail)
        setEvents(nextEvents)
      })
      .catch((reason: unknown) => current && setError(String(reason)))
    return () => { current = false }
  }, [activeId])

  useEffect(() => {
    let current = true
    if (selectedIds.length === 0) {
      setAnalysis(null)
      return
    }
    api.describe(selectedIds, unit)
      .then((result) => current && setAnalysis(result))
      .catch((reason: unknown) => current && setError(String(reason)))
    return () => { current = false }
  }, [selectedIds, unit])

  async function runExperiment(parameters: RunParameters) {
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const created = await api.createRun(parameters)
      await refreshRuns(created.summary.run_id)
      setNotice(`Validated ${created.summary.scenario_id} trace and saved its artifact.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setBusy(false)
    }
  }

  async function runPhase2(parameters: Phase2RunParameters) {
    setPhase2Busy(true)
    setError(null)
    try {
      const result = await api.createPhase2Run(parameters)
      setPhase2Run(result)
      setNotice(`Measured ${parameters.calls_per_run} calls through ${parameters.transport}.`)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason))
    } finally {
      setPhase2Busy(false)
    }
  }

  function toggleRun(runId: string) {
    setSelectedIds((current) => current.includes(runId)
      ? current.filter((id) => id !== runId)
      : [...current, runId])
  }

  const summary = detail?.summary ?? null

  return (
    <div className="app-shell" data-testid="app-ready">
      <header className="site-header">
        <div>
          <p className="eyebrow">Performance analysis of agentic AI systems</p>
          <h1>MCP Traffic Analysis</h1>
          <p className="header-copy">Generate controlled traces, inspect protocol events, and examine reproducible descriptive statistics before making modeling claims.</p>
        </div>
        <div><div className="status-badge"><span /> Model-free statistical laboratory</div><nav className="view-tabs" aria-label="Workbench view"><button className={view === 'study' ? 'active' : ''} onClick={() => setView('study')}>Statistical study</button><button className={view === 'calibration' ? 'active' : ''} onClick={() => setView('calibration')}>Phase 1 traces</button></nav></div>
      </header>

      {error ? <div className="message error" role="alert">{error}</div> : null}
      {notice ? <div className="message success" role="status">{notice}</div> : null}

      {view === 'study' ? <main className="workspace">
        <aside className="sidebar"><section className="panel control-panel"><Phase2RunForm busy={phase2Busy} onRun={runPhase2} /></section><section className="panel"><p className="eyebrow">Study question</p><h2>What explains MCP latency?</h2><p className="field-note">Transport, serialized size, controlled service time, concurrency, and run-level variation. No agent is used in this phase.</p></section></aside>
        <div className="main-column">{phase2Run ? <Phase2RunResult run={phase2Run} /> : <section className="panel welcome-panel"><p className="eyebrow">Single-run calibration</p><h2>Cross a measured transport boundary</h2><p>Run the same controlled workload through in-memory MCP or a real stdio subprocess. Exact bytes exist only for stdio.</p></section>}<CampaignPanel /></div>
      </main> : <main className="workspace">
        <aside className="sidebar">
          <section className="panel control-panel">
            <ExperimentForm scenarios={scenarios} busy={busy} onRun={runExperiment} />
          </section>
          <RunBrowser runs={runs} selectedIds={selectedIds} activeId={activeId} onToggle={toggleRun} onActivate={setActiveId} />
        </aside>

        <div className="main-column">
          {loading ? <section className="panel empty-state">Loading experiment store…</section> : null}
          {!loading && !summary ? (
            <section className="panel welcome-panel">
              <p className="eyebrow">Start here</p><h2>Create a deterministic MCP trace</h2>
              <p>Choose a scenario on the left. The experiment is validated before it appears here.</p>
            </section>
          ) : null}

          {summary ? (
            <>
              <section className="metric-grid" aria-label="Active run summary">
                <MetricCard label="MCP requests" value={String(summary.mcp_request_count)} testId="metric-requests" />
                <MetricCard label="Tool calls" value={String(summary.tool_call_count)} testId="metric-tool-calls" />
                <MetricCard label="Failed spans" value={String(summary.failed_span_count)} testId="metric-failures" />
                <MetricCard label="Observed window" value={number(summary.observed_trace_window_ms, ' ms')} testId="metric-window" />
              </section>
              <section className="panel boundary-panel">
                <div><p className="eyebrow">Measurement boundary</p><h2>Application-layer MCP events</h2></div>
                <p>Handler latency and event ordering are measured. Serialized request/response bytes are deliberately marked unavailable for the current in-memory transport; they are not estimated from Python objects.</p>
              </section>
            </>
          ) : null}

          {analysis ? (
            <><StatisticsPanel analysis={analysis} unit={unit} onUnitChange={setUnit} /><TraceTimeline spans={analysis.timeline} /></>
          ) : selectedIds.length === 0 && runs.length > 0 ? (
            <section className="panel empty-state">Select at least one run for statistics.</section>
          ) : null}
          {events.length > 0 ? <EventTable events={events} /> : null}
        </div>
      </main>}
    </div>
  )
}

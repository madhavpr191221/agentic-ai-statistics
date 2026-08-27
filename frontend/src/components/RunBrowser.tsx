import type { RunSummary } from '../types'

interface RunBrowserProps {
  runs: RunSummary[]
  selectedIds: string[]
  activeId: string | null
  onToggle: (runId: string) => void
  onActivate: (runId: string) => void
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(value))
}

export function RunBrowser({ runs, selectedIds, activeId, onToggle, onActivate }: RunBrowserProps) {
  return (
    <section className="run-browser panel">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Artifact store</p>
          <h2>Completed runs</h2>
        </div>
        <span className="count-chip">{runs.length}</span>
      </div>
      {runs.length === 0 ? (
        <p className="empty-state">Run a scenario to create the first validated trace.</p>
      ) : (
        <div className="run-list">
          {runs.map((run) => (
            <article
              className={`run-row ${activeId === run.run_id ? 'active' : ''}`}
              key={run.run_id}
            >
              <label className="run-select">
                <input
                  aria-label={`Include ${run.scenario_id} run in statistics`}
                  type="checkbox"
                  checked={selectedIds.includes(run.run_id)}
                  onChange={() => onToggle(run.run_id)}
                />
                <span>
                  <strong>{run.scenario_id}</strong>
                  <small>{formatDate(run.start_time_utc)}</small>
                </span>
              </label>
              <button type="button" className="text-button" onClick={() => onActivate(run.run_id)}>
                Inspect
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

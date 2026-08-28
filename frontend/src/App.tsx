import { useState } from 'react'

import { BehaviorWorkbench } from './components/BehaviorWorkbench'
import { IncidentWorkbench } from './components/IncidentWorkbench'
import { TraceDynamicsWorkbench } from './components/TraceDynamicsWorkbench'

export default function App() {
  const [view, setView] = useState<'trace' | 'behavior' | 'agent'>('trace')

  return (
    <div className="app-shell" data-testid="app-ready">
      <header className="site-header">
        <div>
          <p className="eyebrow">Performance analysis of agentic AI systems</p>
          <h1>MCP Traffic Analysis</h1>
          <p className="header-copy">
            Measure real agent traces, protocol traffic, task success, and stochastic path
            variability in controlled IT incidents.
          </p>
        </div>
        <div>
          <div className="status-badge"><span /> Measured agent systems laboratory</div>
          <nav className="view-tabs" aria-label="Workbench view">
            <button
              className={view === 'trace' ? 'active' : ''}
              onClick={() => setView('trace')}
            >
              Trace dynamics
            </button>
            <button
              className={view === 'behavior' ? 'active' : ''}
              onClick={() => setView('behavior')}
            >
              Behavior study
            </button>
            <button
              className={view === 'agent' ? 'active' : ''}
              onClick={() => setView('agent')}
            >
              Incident Agent
            </button>
          </nav>
        </div>
      </header>
      {view === 'trace' ? <TraceDynamicsWorkbench /> : view === 'behavior' ? <BehaviorWorkbench /> : <IncidentWorkbench />}
    </div>
  )
}

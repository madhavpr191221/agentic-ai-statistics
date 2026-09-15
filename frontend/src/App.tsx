import { IncidentWorkbench } from './components/IncidentWorkbench'

export default function App() {
  return (
    <div className="app-shell" data-testid="app-ready">
      <header className="site-header">
        <div>
          <p className="eyebrow">A statistical case study of stochastic agent behaviour</p>
          <h1>Agentic AI Statistics</h1>
          <p className="header-copy">
            Repeat controlled IT-incident executions and study their work, time, cost, paths, and reliability.
          </p>
        </div>
        <div>
          <div className="status-badge"><span /> One fresh run = one observation</div>
        </div>
      </header>
      <IncidentWorkbench />
    </div>
  )
}

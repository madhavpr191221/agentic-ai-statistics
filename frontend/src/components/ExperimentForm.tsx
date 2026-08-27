import { useEffect, useState, type FormEvent } from 'react'

import type { RunParameters, ScenarioDescriptor, ScenarioId } from '../types'

interface ExperimentFormProps {
  scenarios: ScenarioDescriptor[]
  busy: boolean
  onRun: (parameters: RunParameters) => Promise<void>
}

export function ExperimentForm({ scenarios, busy, onRun }: ExperimentFormProps) {
  const [scenario, setScenario] = useState<ScenarioId>('echo')
  const [repeat, setRepeat] = useState(1)
  const [seed, setSeed] = useState(0)

  useEffect(() => {
    if (scenarios.length > 0 && !scenarios.some((item) => item.id === scenario)) {
      setScenario(scenarios[0].id)
    }
  }, [scenario, scenarios])

  const selected = scenarios.find((item) => item.id === scenario)

  async function submit(event: FormEvent) {
    event.preventDefault()
    await onRun({ scenario, repeat, seed })
  }

  return (
    <form className="experiment-form" onSubmit={(event) => void submit(event)}>
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Experiment control</p>
          <h2>Run calibration</h2>
        </div>
        <span className="phase-chip">Phase 1A</span>
      </div>

      <label>
        Scenario
        <select
          aria-label="Scenario"
          value={scenario}
          onChange={(event) => setScenario(event.target.value as ScenarioId)}
          disabled={busy}
        >
          {scenarios.map((item) => (
            <option key={item.id} value={item.id}>
              {item.label}
            </option>
          ))}
        </select>
      </label>

      <p className="field-note" data-testid="scenario-description">
        {selected?.description ?? 'Loading deterministic scenarios…'}
      </p>

      <div className="form-grid">
        <label>
          Repetitions
          <input
            aria-label="Repetitions"
            type="number"
            min={1}
            max={100}
            value={repeat}
            onChange={(event) => setRepeat(Number(event.target.value))}
            disabled={busy}
          />
        </label>
        <label>
          Seed
          <input
            aria-label="Seed"
            type="number"
            value={seed}
            onChange={(event) => setSeed(Number(event.target.value))}
            disabled={busy}
          />
        </label>
      </div>

      <button className="primary-button" type="submit" disabled={busy || scenarios.length === 0}>
        {busy ? 'Running and validating…' : 'Run experiment'}
      </button>
      <p className="privacy-note">No model call. No .env access. Synthetic payloads only.</p>
    </form>
  )
}

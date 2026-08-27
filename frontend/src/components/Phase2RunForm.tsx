import { useState, type FormEvent } from 'react'

import type { Phase2RunParameters } from '../types'

export function Phase2RunForm({ busy, onRun }: { busy: boolean; onRun: (value: Phase2RunParameters) => Promise<void> }) {
  const [transport, setTransport] = useState<'in_memory' | 'stdio'>('stdio')
  const [payload, setPayload] = useState(1024)
  const [service, setService] = useState(20)
  const [concurrency, setConcurrency] = useState(1)
  const [calls, setCalls] = useState(8)

  async function submit(event: FormEvent) {
    event.preventDefault()
    await onRun({ transport, payload_target_bytes: payload, service_time_ms: service, concurrency, calls_per_run: calls, seed: 0 })
  }

  return (
    <form className="experiment-form" onSubmit={(event) => void submit(event)}>
      <div className="section-heading compact"><div><p className="eyebrow">Controlled factors</p><h2>Latency experiment</h2></div><span className="phase-chip">Phase 2</span></div>
      <label>Transport<select aria-label="Transport" value={transport} onChange={(event) => setTransport(event.target.value as 'in_memory' | 'stdio')} disabled={busy}><option value="stdio">stdio subprocess</option><option value="in_memory">In memory</option></select></label>
      <div className="form-grid">
        <label>Payload<select aria-label="Payload size" value={payload} onChange={(event) => setPayload(Number(event.target.value))} disabled={busy}><option value={64}>64 B</option><option value={1024}>1 KiB</option><option value={16384}>16 KiB</option><option value={65536}>64 KiB</option></select></label>
        <label>Service time<select aria-label="Service time" value={service} onChange={(event) => setService(Number(event.target.value))} disabled={busy}><option value={0}>0 ms</option><option value={20}>20 ms</option><option value={100}>100 ms</option></select></label>
        <label>Concurrency<select aria-label="Concurrency" value={concurrency} onChange={(event) => setConcurrency(Number(event.target.value))} disabled={busy}><option value={1}>1</option><option value={4}>4</option></select></label>
        <label>Calls<input aria-label="Calls per run" type="number" min={1} max={100} value={calls} onChange={(event) => setCalls(Number(event.target.value))} disabled={busy} /></label>
      </div>
      <button className="primary-button" type="submit" disabled={busy}>{busy ? 'Measuring…' : 'Run controlled experiment'}</button>
      <p className="privacy-note">Synthetic ASCII only. Frame contents are discarded after byte counting and hashing.</p>
    </form>
  )
}

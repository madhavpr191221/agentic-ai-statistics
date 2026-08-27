import type { Phase2RunResponse } from '../types'
import { MetricCard } from './MetricCard'

function ms(value: number | null) { return value === null ? 'Unavailable' : `${value.toFixed(2)} ms` }
function bytes(value: number | null) { return value === null ? 'Unavailable' : value.toLocaleString() }

export function Phase2RunResult({ run }: { run: Phase2RunResponse }) {
  return <>
    <section className="metric-grid" data-testid="phase2-result">
      <MetricCard label="Median client RTT" value={ms(run.median_client_roundtrip_ms)} testId="metric-rtt" />
      <MetricCard label="Median handler" value={ms(run.median_server_handler_ms)} testId="metric-handler" />
      <MetricCard label="Non-handler residual" value={ms(run.median_nonhandler_residual_ms)} testId="metric-residual" />
      <MetricCard label="Response frame bytes" value={bytes(run.total_response_frame_bytes)} testId="metric-response-bytes" />
    </section>
    <section className="panel boundary-panel"><div><p className="eyebrow">Observed boundary</p><h2>{run.transport}</h2></div><p>{run.transport === 'stdio' ? 'Exact JSON-RPC payload and newline-delimited frame sizes were observed at the relay. The residual is RTT minus handler duration, not pure transport latency.' : 'No serialized frame exists in this transport. Byte quantities remain unavailable rather than estimated.'}</p></section>
    <section className="panel"><div className="section-heading compact"><div><p className="eyebrow">Nested observations</p><h2>Measured calls</h2></div><span className="count-chip">{run.calls.length}</span></div><div className="table-scroll"><table className="data-table" data-testid="phase2-call-table"><thead><tr><th>Call</th><th>RTT</th><th>Handler</th><th>Request frame</th><th>Response frame</th><th>Residual</th></tr></thead><tbody>{run.calls.map((call) => { const residual = call.server_handler_ms === null ? null : call.client_roundtrip_ms - call.server_handler_ms; return <tr key={call.call_id}><td>{call.call_index + 1}</td><td>{ms(call.client_roundtrip_ms)}</td><td>{ms(call.server_handler_ms)}</td><td>{bytes(call.request_frame_bytes)}</td><td>{bytes(call.response_frame_bytes)}</td><td>{ms(residual)}</td></tr> })}</tbody></table></div></section>
  </>
}

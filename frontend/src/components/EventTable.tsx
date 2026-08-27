import type { TraceEvent } from '../types'

function formatLatency(value: number | null) {
  return value === null ? '—' : `${value.toFixed(2)} ms`
}

export function EventTable({ events }: { events: TraceEvent[] }) {
  return (
    <section className="panel event-panel">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Canonical JSONL</p>
          <h2>Event stream</h2>
        </div>
        <span className="count-chip">{events.length} events</span>
      </div>
      <div className="table-scroll">
        <table className="data-table" data-testid="event-table">
          <thead>
            <tr>
              <th>Seq</th>
              <th>Kind</th>
              <th>Method</th>
              <th>Tool</th>
              <th>Outcome</th>
              <th>Error type</th>
              <th>Latency</th>
              <th>Bytes</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.event_id}>
                <td>{event.sequence_number}</td>
                <td>{event.event_kind}</td>
                <td>{event.mcp_method ?? '—'}</td>
                <td>{event.tool_name ?? '—'}</td>
                <td>
                  <span className={`outcome-pill ${event.outcome}`}>{event.outcome}</span>
                </td>
                <td>{event.error_type ?? '—'}</td>
                <td>{formatLatency(event.latency_ms)}</td>
                <td title={event.payload_recording_policy}>
                  {event.payload_bytes === null ? 'Unavailable' : event.payload_bytes}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

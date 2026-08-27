import type { TimelineSpan } from '../types'

export function TraceTimeline({ spans }: { spans: TimelineSpan[] }) {
  const maximum = Math.max(
    1,
    ...spans.map((span) => span.start_offset_ms + span.event_window_ms),
  )
  return (
    <section className="panel timeline-panel" data-testid="trace-timeline">
      <div className="section-heading compact">
        <div>
          <p className="eyebrow">Causal execution</p>
          <h2>Trace timeline</h2>
        </div>
        <span className="count-chip">{spans.length} spans</span>
      </div>
      <div className="timeline-axis">
        <span>0 ms</span>
        <span>{maximum.toFixed(1)} ms</span>
      </div>
      <div className="timeline-list">
        {spans.map((span) => {
          const left = (span.start_offset_ms / maximum) * 100
          const width = Math.max((span.event_window_ms / maximum) * 100, 1.5)
          return (
            <div className="timeline-row" key={`${span.run_id}-${span.span_id}`}>
              <div className="timeline-label">
                <strong>{span.tool_name ?? span.method}</strong>
                <small>{span.outcome}</small>
              </div>
              <div className="timeline-track">
                <div
                  className={`timeline-bar ${span.outcome}`}
                  data-testid="timeline-span"
                  style={{ left: `${left}%`, width: `${Math.min(width, 100 - left)}%` }}
                  title={`${span.handler_latency_ms.toFixed(2)} ms handler latency`}
                />
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}

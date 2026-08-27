import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TraceTimeline } from './TraceTimeline'

describe('TraceTimeline', () => {
  it('renders ordered spans on a common run-relative scale', () => {
    render(<TraceTimeline spans={[{ run_id: 'run-1', span_id: 'span-1', method: 'tools/call', tool_name: 'sleep_ms', outcome: 'success', error_type: null, start_offset_ms: 2, event_window_ms: 20, handler_latency_ms: 20 }]} />)
    expect(screen.getByText('sleep_ms')).toBeInTheDocument()
    expect(screen.getByTestId('timeline-span')).toHaveStyle({ left: `${(2 / 22) * 100}%` })
  })
})

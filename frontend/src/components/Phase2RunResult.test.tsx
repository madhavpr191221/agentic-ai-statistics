import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { Phase2RunResponse } from '../types'
import { Phase2RunResult } from './Phase2RunResult'

const run: Phase2RunResponse = {
  run_id: 'run', condition_id: 'condition', transport: 'stdio', session_start_ms: 30,
  run_elapsed_ms: 60, median_client_roundtrip_ms: 5, median_server_handler_ms: 2,
  median_nonhandler_residual_ms: 3, total_request_frame_bytes: 400,
  total_response_frame_bytes: 300, calls: [{ run_id: 'run', condition_id: 'condition',
    call_id: 'call', call_index: 0, batch_index: 0, transport: 'stdio',
    payload_target_bytes: 64, service_time_ms: 0, concurrency: 1, is_first_call: true,
    client_roundtrip_ms: 5, outcome: 'success', error_type: null, request_payload_bytes: 199,
    request_frame_bytes: 200, response_payload_bytes: 149, response_frame_bytes: 150,
    server_handler_ms: 2 }],
}

describe('Phase2RunResult', () => {
  it('separates roundtrip, handler, residual, and wire bytes', () => {
    render(<Phase2RunResult run={run} />)
    expect(screen.getByTestId('metric-rtt')).toHaveTextContent('5.00 ms')
    expect(screen.getByTestId('metric-response-bytes')).toHaveTextContent('300')
    expect(screen.getByText('not pure transport latency', { exact: false })).toBeInTheDocument()
  })
})

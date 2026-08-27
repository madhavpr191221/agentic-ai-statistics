import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { IncidentWorkbench } from './IncidentWorkbench'
import { api } from '../api'

vi.mock('../api', () => ({ api: {
  listIncidentScenarios: vi.fn(), listIncidentRuns: vi.fn(), createIncidentRun: vi.fn(),
  listIncidentCampaigns: vi.fn(),
} }))

test('runs and renders a scored incident observation', async () => {
  vi.mocked(api.listIncidentScenarios).mockResolvedValue([{ id: 'checkout_failures', label: 'Checkout', alert: 'errors' }])
  vi.mocked(api.listIncidentRuns).mockResolvedValue([])
  vi.mocked(api.listIncidentCampaigns).mockResolvedValue([])
  vi.mocked(api.createIncidentRun).mockResolvedValue({
    run_id: 'r1', scenario_id: 'checkout_failures', created_at_utc: '2026-08-27T00:00:00Z', model_id: 'gpt-5.6-sol',
    measurement: { status: 'success', failure_type: null, total_latency_ms: 100, model_latency_ms: 80, mcp_latency_ms: 5, server_handler_latency_ms: 2, orchestration_latency_ms: 15, decomposition_consistent: true, correlation_consistent: true, model_call_count: 2, mcp_call_count: 3, tool_sequence: ['get_metrics', 'get_recent_changes', 'rollback_deployment'], input_tokens: 100, cached_input_tokens: 0, output_tokens: 20, total_tokens: 120, request_frame_bytes: 400, response_frame_bytes: 800, estimated_cost_usd: .0008 },
    result: { incident_id: 'checkout_failures', diagnosis: 'bad deployment', evidence_ids: ['e1'], selected_action: 'rollback_deployment', action_target: 'd1', resolution_summary: 'resolved' },
    score: { diagnosis_correct: true, required_evidence_present: true, correct_remediation_executed: true, no_prohibited_action_attempted: true, final_state_resolved: true, task_success: true }, actions: [], agent_events: [],
  })
  render(<IncidentWorkbench />)
  await waitFor(() => expect(screen.getByText('Checkout')).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: 'Run real agent' }))
  await waitFor(() => expect(screen.getByText('bad deployment')).toBeInTheDocument())
  expect(screen.getByText('3 ordered MCP calls')).toBeInTheDocument()
})

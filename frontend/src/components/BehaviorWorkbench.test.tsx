import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { api } from '../api'
import { BehaviorWorkbench } from './BehaviorWorkbench'

vi.mock('../api', () => ({ api: {
  listBehaviorConditions: vi.fn(), listBehaviorRuns: vi.fn(),
  listBehaviorCampaigns: vi.fn(), createBehaviorRun: vi.fn(),
} }))

test('grounds the behavior study in a concrete ticket and labels scripted data', async () => {
  vi.mocked(api.listBehaviorConditions).mockResolvedValue([{
    scenario_id: 'checkout_failures', label: 'Checkout failures',
    incoming_message: 'Customers cannot complete checkout after the release.',
    task_structure: 'sequential',
    oracle_sequence: ['get_alert', 'get_metrics', 'get_recent_changes', 'get_runbook', 'rollback_deployment'],
  }])
  vi.mocked(api.listBehaviorRuns).mockResolvedValue([])
  vi.mocked(api.listBehaviorCampaigns).mockResolvedValue([])
  vi.mocked(api.createBehaviorRun).mockResolvedValue({
    run_id: 'behavior-1', scenario_id: 'checkout_failures',
    created_at_utc: '2026-09-01T00:00:00Z', model_id: 'gpt-5.6-sol',
    measurement: { status: 'success', failure_type: null, total_latency_ms: 1, model_latency_ms: 0, mcp_latency_ms: 0, server_handler_latency_ms: 0, orchestration_latency_ms: 1, decomposition_consistent: true, correlation_consistent: true, model_call_count: 0, mcp_call_count: 5, tool_sequence: ['get_alert', 'get_metrics', 'get_recent_changes', 'get_runbook', 'rollback_deployment'], input_tokens: 0, cached_input_tokens: 0, output_tokens: 0, total_tokens: 0, request_frame_bytes: 0, response_frame_bytes: 0, estimated_cost_usd: 0 },
    result: { incident_id: 'checkout_failures', diagnosis: 'defective checkout deployment', evidence_ids: ['metric-checkout-errors', 'change-checkout-deploy', 'runbook-safe-response'], selected_action: 'rollback_deployment', action_target: 'checkout-2026.08.27.4', resolution_summary: 'resolved' },
    score: { diagnosis_correct: true, required_evidence_present: true, correct_remediation_executed: true, no_prohibited_action_attempted: true, final_state_resolved: true, task_success: true },
    actions: [], agent_events: [],
    behavior: { task_structure: 'sequential', incoming_message: 'Customers cannot complete checkout after the release.', oracle_sequence: ['get_alert', 'get_metrics', 'get_recent_changes', 'get_runbook', 'rollback_deployment'], observed_sequence: ['get_alert', 'get_metrics', 'get_recent_changes', 'get_runbook', 'rollback_deployment'], oracle_call_count: 5, excess_mcp_calls: 0, normalized_oracle_distance: 0, expected_rejections: 0, unexpected_rejections: 0, trace_steps: ['get_alert', 'get_metrics', 'get_recent_changes', 'get_runbook', 'rollback_deployment'].map((tool_name, sequence) => ({ sequence, tool_name, classification: 'oracle' as const })), execution_mode: 'scripted_validation', request_frame_bytes: null, response_frame_bytes: null, block: null, execution_order: null },
  })
  render(<BehaviorWorkbench />)
  await waitFor(() => expect(screen.getByText(/Customers cannot complete checkout/)).toBeInTheDocument())
  fireEvent.click(screen.getByRole('button', { name: 'Run task' }))
  await waitFor(() => expect(screen.getByText(/Scripted structural validation/)).toBeInTheDocument())
  expect(screen.getByText('Five-call oracle')).toBeInTheDocument()
  expect(screen.getAllByText('Unavailable', { selector: 'strong' })).toHaveLength(2)
})

test('shows the Q04 workload comparison from saved campaign data', async () => {
  vi.mocked(api.listBehaviorConditions).mockResolvedValue([])
  vi.mocked(api.listBehaviorRuns).mockResolvedValue([])
  vi.mocked(api.listBehaviorCampaigns).mockResolvedValue([{
    campaign_id: 'task-structure-main-v1', study_stage: 'main',
    experimental_unit: 'one fresh agent run and MCP session', n_runs: 90,
    primary_outcome: 'mcp_call_count', condition_summaries: [],
    workload_by_structure: [
      { task_structure: 'sequential', n_runs: 30, successes: 30, success_rate: 1,
        mcp_call_count: { mean: 8.13, median: 8, q1: 8, q3: 8, minimum: 7, maximum: 10 },
        model_call_count: { mean: 9, median: 9, q1: 8, q3: 10, minimum: 7, maximum: 11 },
        total_latency_ms: { mean: 16000, median: 16000, q1: 14000, q3: 18000, minimum: 10000, maximum: 22000 },
        total_tokens: { mean: 7500, median: 7500, q1: 7000, q3: 8000, minimum: 6000, maximum: 9000 },
        estimated_cost_usd: { mean: 0.02, median: 0.02, q1: 0.01, q3: 0.03, minimum: 0.01, maximum: 0.04 } },
    ],
  }])
  render(<BehaviorWorkbench />)
  await waitFor(() => expect(screen.getByTestId('workload-analysis')).toBeInTheDocument())
  expect(screen.getByText('Does task structure change agent workload?')).toBeInTheDocument()
  expect(screen.getByText('Download workload summaries')).toBeInTheDocument()
})

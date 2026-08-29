import { render, screen, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'

import { api } from '../api'
import type { TraceStudyAnalysis } from '../types'
import { TraceDynamicsWorkbench } from './TraceDynamicsWorkbench'

vi.mock('../api', () => ({ api: { listTraceStudyCampaigns: vi.fn() } }))

const analysis: TraceStudyAnalysis = {
  schema_version: '5.0.0', campaign_id: 'phase4-main-reanalysis-v1',
  study_stage: 'exploratory', created_at_utc: '2026-08-28T00:00:00Z',
  experimental_unit: 'one fresh agent run and MCP session', n_runs: 90,
  new_model_calls: 0,
  focused_condition: { scenario_id: 'orders_api_outage', task_structure: 'recovery' },
  primary_question: 'What happens after rejection?',
  post_rejection_analysis: {
    focused_runs: 10,
    classified_runs: 10, unclassified_runs: 0,
    counts: {
      read_runbook_first: { success: 5, failure: 0 },
      retried_first: { success: 0, failure: 5 },
    },
    failure_rate_read_runbook_first: 0,
    failure_rate_read_runbook_first_wilson_95: [0, 0.434],
    failure_rate_retried_first: 1,
    failure_rate_retried_first_wilson_95: [0.566, 1],
    failure_risk_difference_retry_minus_read: 1,
    failure_risk_difference_newcombe_95: [0.386, 1],
    fisher_exact_two_sided_p: 0.0079,
    interpretation_limit: 'Observed association; behavior was not randomized.',
  },
  focused_measurements: { mcp_call_count: { n: 10, median: 10, q1: 9, q3: 10, minimum: 9, maximum: 11 } },
  measurement_boundary: 'Exact local stdio frame bytes, not network packets.',
  condition_summaries: [{
    scenario_id: 'orders_api_outage', task_structure: 'recovery', n_runs: 10,
    successes: 5, unique_paths: 8, singleton_paths: 7, modal_path_count: 2,
    modal_path_proportion: 0.2, path_entropy_bits: 2.846,
    path_entropy_bootstrap_95: [1.5, 2.9], exact_oracle_successes: 0,
    successful_excess_calls: { n: 5, mean: 5.2, median: 5, q1: 5, q3: 5, minimum: 5, maximum: 6 },
  }],
  path_summary: [{
    scenario_id: 'orders_api_outage', task_structure: 'recovery',
    state_sequence: 'START > escalate_incident|expected_rejection > get_runbook|observed > END_SUCCESS',
    count: 5, proportion: 0.5,
  }],
  transition_summary: [{
    scenario_id: 'orders_api_outage', task_structure: 'recovery',
    source_state: 'escalate_incident|expected_rejection', target_state: 'get_runbook|observed',
    count: 5, probability: 0.5,
  }],
  batch_summaries: [{ batch: 1, n_runs: 10, success_rate: 0.5, read_runbook_first_rate: 0.5, mean_mcp_calls: 9.9 }],
  trace_examples: [
    { run_id: 'success-run', scenario_id: 'orders_api_outage', task_structure: 'recovery', task_success: true, batch: 1, execution_order: 1, tool_sequence: 'escalate_incident > get_runbook', state_sequence: 'START > escalate_incident|expected_rejection > get_runbook|observed > escalate_incident|accepted > END_SUCCESS', oracle_sequence: 'get_alert > get_dependencies > escalate_incident > get_runbook > escalate_incident', post_rejection_behavior: 'read_runbook_first', first_oracle_divergence: 1 },
    { run_id: 'failure-run', scenario_id: 'orders_api_outage', task_structure: 'recovery', task_success: false, batch: 1, execution_order: 2, tool_sequence: 'escalate_incident > escalate_incident', state_sequence: 'START > escalate_incident|expected_rejection > escalate_incident|unexpected_rejection > END_FAILURE', oracle_sequence: 'get_alert > get_dependencies > escalate_incident > get_runbook > escalate_incident', post_rejection_behavior: 'retried_first', first_oracle_divergence: 1 },
  ],
  notes: [],
  prediction: {
    schema_version: '15.0.0', training_campaign_id: 'train', test_campaign_id: 'test',
    training_runs: 4, test_runs: 2, state_vocabulary: ['START', 'END_SUCCESS'],
    model_comparison: [{
      model: 'history_aware', n_runs: 2, n_transitions: 4, mean_run_log_loss: 0.5,
      mean_run_accuracy: 0.8, mean_run_brier_score: 0.2,
      mean_run_log_loss_bootstrap_95: [0.3, 0.7], mean_run_accuracy_bootstrap_95: [0.6, 1],
      mean_run_brier_score_bootstrap_95: [0.1, 0.3],
    }],
    paired_log_loss_comparisons: [{
      better_model: 'history_aware', baseline_model: 'current_state',
      mean_log_loss_difference: -0.2, mean_log_loss_difference_bootstrap_95: [-0.3, -0.1],
    }],
    limitations: [],
  },
}

test('connects the practical rejection choice to counts and failure percentages', async () => {
  vi.mocked(api.listTraceStudyCampaigns).mockResolvedValue([analysis])
  render(<TraceDynamicsWorkbench />)
  await waitFor(() => expect(screen.getByText('Read runbook first')).toBeInTheDocument())
  expect(screen.getByText(/Orders API is returning 503/)).toBeInTheDocument()
  expect(screen.getByText('Retried first')).toBeInTheDocument()
  expect(screen.getByText('Observed difference: 100.0%')).toBeInTheDocument()
  expect(screen.getByText('Successful run')).toBeInTheDocument()
  expect(screen.getByText('Failed run')).toBeInTheDocument()
  expect(screen.getByText('Can the models predict new observable actions?')).toBeInTheDocument()
  expect(screen.getAllByTestId('plotly-chart')).toHaveLength(1)
})

test('labels an interrupted campaign and excludes provider attempts', async () => {
  vi.mocked(api.listTraceStudyCampaigns).mockResolvedValue([{
    ...analysis,
    campaign_id: 'trace-orders-recovery-main-v2',
    study_stage: 'main',
    n_runs: 66,
    planned_runs: 100,
    campaign_complete: false,
    excluded_provider_attempts: 17,
  }])
  render(<TraceDynamicsWorkbench />)

  await waitFor(() => expect(screen.getByText('66 of 100 valid runs are available')).toBeInTheDocument())
  expect(screen.getByText(/17 provider-error attempts/)).toBeInTheDocument()
  expect(screen.getByText(/interim results/i)).toBeInTheDocument()
})

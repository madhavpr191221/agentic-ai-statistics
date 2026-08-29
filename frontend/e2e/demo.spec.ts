import { expect, test } from '@playwright/test'

test('runs a concrete Phase 4 task without model cost', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Behavior study' }).click()
  await expect(page.getByTestId('behavior-workbench')).toBeVisible()
  await expect(page.getByText('Simulated incoming incident ticket')).toBeVisible()
  await page.getByLabel('Task structure').selectOption('recovery')
  await page.getByRole('button', { name: 'Run task' }).click()
  await expect(page.getByText(/Scripted structural validation/)).toBeVisible()
  await expect(page.getByText('Five-call oracle')).toBeVisible()
  await expect(page.getByText('expected rejection')).toBeVisible()
})

test('connects a practical rejection choice to Phase 5 failure statistics', async ({ page }) => {
  await page.route('**/api/trace-study/campaigns', async route => {
    await route.fulfill({ json: [{
      schema_version: '5.0.0', campaign_id: 'phase4-main-reanalysis-v1',
      study_stage: 'exploratory', created_at_utc: '2026-08-28T00:00:00Z',
      experimental_unit: 'one fresh agent run and MCP session', n_runs: 90,
      focused_condition: { scenario_id: 'orders_api_outage', task_structure: 'recovery' },
      primary_question: 'What happens after rejection?',
      post_rejection_analysis: {
        focused_runs: 10, classified_runs: 10, unclassified_runs: 0,
        counts: { read_runbook_first: { success: 5, failure: 0 }, retried_first: { success: 0, failure: 5 } },
        failure_rate_read_runbook_first: 0, failure_rate_read_runbook_first_wilson_95: [0, 0.434],
        failure_rate_retried_first: 1, failure_rate_retried_first_wilson_95: [0.566, 1],
        failure_risk_difference_retry_minus_read: 1, failure_risk_difference_newcombe_95: [0.386, 1],
        fisher_exact_two_sided_p: 0.0079, interpretation_limit: 'Observed association; behavior was not randomized.',
      },
      focused_measurements: { mcp_call_count: { n: 10, median: 10, q1: 9, q3: 10, minimum: 9, maximum: 11 } },
      measurement_boundary: 'Exact local stdio frame bytes, not network packets.',
      condition_summaries: [{ scenario_id: 'orders_api_outage', task_structure: 'recovery', n_runs: 10, successes: 5, unique_paths: 8, singleton_paths: 7, modal_path_count: 2, modal_path_proportion: 0.2, path_entropy_bits: 2.846, path_entropy_bootstrap_95: [1.5, 2.9], exact_oracle_successes: 0, successful_excess_calls: { n: 5, mean: 5.2, median: 5, q1: 5, q3: 5, minimum: 5, maximum: 6 } }],
      path_summary: [{ scenario_id: 'orders_api_outage', task_structure: 'recovery', state_sequence: 'START > escalate_incident|expected_rejection > get_runbook|observed > END_SUCCESS', count: 5, proportion: 0.5 }],
      transition_summary: [{ scenario_id: 'orders_api_outage', task_structure: 'recovery', source_state: 'escalate_incident|expected_rejection', target_state: 'get_runbook|observed', count: 5, probability: 0.5 }],
      batch_summaries: [],
      trace_examples: [
        { run_id: 'success-run', scenario_id: 'orders_api_outage', task_structure: 'recovery', task_success: true, batch: 1, execution_order: 1, tool_sequence: 'escalate_incident > get_runbook', state_sequence: 'START > escalate_incident|expected_rejection > get_runbook|observed > escalate_incident|accepted > END_SUCCESS', oracle_sequence: 'get_alert > get_dependencies > escalate_incident > get_runbook > escalate_incident', post_rejection_behavior: 'read_runbook_first', first_oracle_divergence: 1 },
        { run_id: 'failure-run', scenario_id: 'orders_api_outage', task_structure: 'recovery', task_success: false, batch: 1, execution_order: 2, tool_sequence: 'escalate_incident > escalate_incident', state_sequence: 'START > escalate_incident|expected_rejection > escalate_incident|unexpected_rejection > END_FAILURE', oracle_sequence: 'get_alert > get_dependencies > escalate_incident > get_runbook > escalate_incident', post_rejection_behavior: 'retried_first', first_oracle_divergence: 1 },
      ], notes: [],
    }] })
  })
  await page.goto('/')
  await expect(page.getByTestId('trace-dynamics-workbench')).toBeVisible()
  await expect(page.getByText('Read runbook first')).toBeVisible()
  await expect(page.getByText('Retried first')).toBeVisible()
  await expect(page.getByText('Observed difference: 100.0%')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Successful run', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Failed run', exact: true })).toBeVisible()
})

test('renders a scored incident agent trace without spending API credit', async ({ page }) => {
  await page.route('**/api/agent/**', async route => {
    const url = new URL(route.request().url())
    if (route.request().method() === 'POST') {
      await route.fulfill({ json: {
        run_id: 'e2e-agent', scenario_id: 'checkout_failures', created_at_utc: '2026-08-27T00:00:00Z', model_id: 'gpt-5.6-sol',
        measurement: { status: 'success', failure_type: null, total_latency_ms: 100, model_latency_ms: 80, mcp_latency_ms: 5, server_handler_latency_ms: 2, orchestration_latency_ms: 15, decomposition_consistent: true, correlation_consistent: true, model_call_count: 2, mcp_call_count: 3, tool_sequence: ['get_metrics', 'get_recent_changes', 'rollback_deployment'], input_tokens: 100, cached_input_tokens: 0, output_tokens: 20, total_tokens: 120, request_frame_bytes: 400, response_frame_bytes: 800, estimated_cost_usd: 0.001 },
        result: { incident_id: 'checkout_failures', diagnosis: 'checkout deployment defect', evidence_ids: ['metric-checkout-errors', 'change-checkout-deploy'], selected_action: 'rollback_deployment', action_target: 'checkout-2026.08.27.4', resolution_summary: 'resolved' },
        score: { diagnosis_correct: true, required_evidence_present: true, correct_remediation_executed: true, no_prohibited_action_attempted: true, final_state_resolved: true, task_success: true }, actions: [], agent_events: [],
      } })
    } else if (url.pathname.endsWith('/scenarios')) {
      await route.fulfill({ json: [{ id: 'checkout_failures', label: 'Checkout', alert: 'errors' }] })
    } else {
      await route.fulfill({ json: [] })
    }
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Incident Agent' }).click()
  await page.getByRole('button', { name: 'Run real agent' }).click()
  await expect(page.getByText('checkout deployment defect')).toBeVisible()
  await expect(page.getByText('3 ordered MCP calls')).toBeVisible()
  await expect(page.getByText('Yes')).toBeVisible()
})

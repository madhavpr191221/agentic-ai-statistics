import { expect, test } from '@playwright/test'

test('runs a concrete Phase 4 task without model cost', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('behavior-workbench')).toBeVisible()
  await expect(page.getByText('Simulated incoming incident ticket')).toBeVisible()
  await page.getByLabel('Task structure').selectOption('recovery')
  await page.getByRole('button', { name: 'Run task' }).click()
  await expect(page.getByText(/Scripted structural validation/)).toBeVisible()
  await expect(page.getByText('Five-call oracle')).toBeVisible()
  await expect(page.getByText('expected rejection')).toBeVisible()
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

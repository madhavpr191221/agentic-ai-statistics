import { expect, test } from '@playwright/test'

test('runs a successful trace and exposes measured statistics', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('app-ready')).toBeVisible()
  await page.getByRole('button', { name: 'Phase 1 traces' }).click()
  await page.getByLabel('Scenario').selectOption('echo')
  await page.getByLabel('Repetitions').fill('3')
  await page.getByRole('button', { name: 'Run experiment' }).click()
  await expect(page.getByRole('status')).toContainText('Validated echo trace')
  await expect(page.getByTestId('metric-tool-calls')).toContainText('3')
  await expect(page.getByTestId('statistics-panel')).toBeVisible()
  await expect(page.getByTestId('event-table')).toContainText('tools/call')
})

test('shows concurrency and retains classified failure traces', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: 'Phase 1 traces' }).click()
  await page.getByLabel('Scenario').selectOption('concurrent')
  await page.getByRole('button', { name: 'Run experiment' }).click()
  await expect(page.getByTestId('metric-tool-calls')).toContainText('3')
  // The three concurrent tool calls must be visible; client discovery may add spans.
  await expect.poll(() => page.getByTestId('trace-timeline').getByTestId('timeline-span').count())
    .toBeGreaterThanOrEqual(3)
  await page.getByLabel('Scenario').selectOption('backend_exception')
  await page.getByRole('button', { name: 'Run experiment' }).click()
  await expect(page.getByTestId('metric-failures')).toContainText('1')
  await expect(page.getByTestId('event-table')).toContainText('backend_exception')
  await page.reload()
  await page.getByRole('button', { name: 'Phase 1 traces' }).click()
  await expect(page.getByTestId('metric-failures')).toContainText('1')
})

test('measures a real stdio run with exact frame bytes', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Transport').selectOption('stdio')
  await page.getByLabel('Payload size').selectOption('64')
  await page.getByLabel('Service time').selectOption('0')
  await page.getByLabel('Calls per run').fill('2')
  await page.getByRole('button', { name: 'Run controlled experiment' }).click()
  await expect(page.getByTestId('phase2-result')).toBeVisible()
  await expect(page.getByTestId('metric-response-bytes')).not.toContainText('Unavailable')
  await expect(page.getByTestId('phase2-call-table')).toContainText('Request frame')
})

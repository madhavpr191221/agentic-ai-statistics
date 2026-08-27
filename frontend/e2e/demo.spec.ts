import { expect, test } from '@playwright/test'

test('runs a successful trace and exposes measured statistics', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByTestId('app-ready')).toBeVisible()
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
  await expect(page.getByTestId('metric-failures')).toContainText('1')
})

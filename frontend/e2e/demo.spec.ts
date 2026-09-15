import { expect, test } from '@playwright/test'

test('runs a deterministic incident observation without model cost', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Each fresh run is one statistical observation.')).toBeVisible()
  await page.getByRole('button', { name: 'Run observation' }).click()
  await expect(page.getByText(/checkout-api deployment/)).toBeVisible()
  await expect(page.getByText('5 ordered MCP calls')).toBeVisible()
  await expect(page.getByText('Yes')).toBeVisible()
})

test('allows switching between deterministic and live execution modes', async ({ page }) => {
  await page.goto('/')
  const mode = page.getByLabel('Execution mode')
  await expect(mode).toHaveValue('deterministic')
  await mode.selectOption('live')
  await expect(mode).toHaveValue('live')
})

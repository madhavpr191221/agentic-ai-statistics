import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '../api'
import { CampaignPanel } from './CampaignPanel'

vi.mock('../api', () => ({ api: { listCampaigns: vi.fn(), getCampaign: vi.fn() } }))

describe('CampaignPanel', () => {
  beforeEach(() => {
    vi.mocked(api.listCampaigns).mockResolvedValue([{ campaign_id: 'baseline-v1', design_name: 'baseline-v1', status: 'complete', planned_runs: 960, completed_runs: 960, created_at_utc: '2026-08-27T00:00:00Z' }])
    vi.mocked(api.getCampaign).mockResolvedValue({
      manifest: { campaign_id: 'baseline-v1', design_name: 'baseline-v1', replicates: 20, calls_per_run: 8, transports: ['in_memory', 'stdio'], payload_sizes: [64], service_times_ms: [0], concurrency_levels: [1], planned_runs: [] },
      progress: { status: 'complete', planned_runs: 960, completed_runs: 960 },
      analysis: { experimental_unit: 'run', primary_model: { model_type: 'OLS', formula: 'formula', n_runs: 960, r_squared: .8, adjusted_r_squared: .79, coefficients: [] }, mixed_model: { formula: 'mixed', converged: true, icc: .2 }, byte_model: null, condition_summaries: [], diagnostics: { fitted: [1], residuals: [0], qq_theoretical: [0], qq_observed: [0] }, counts: { runs: 960, successful_calls: 7680, failed_calls: 0 }, notes: [] },
    })
  })

  it('shows experimental units, balance, and model results', async () => {
    render(<CampaignPanel />)
    await waitFor(() => expect(screen.getByTestId('campaign-panel')).toBeInTheDocument())
    expect(screen.getByTestId('campaign-progress-text')).toHaveTextContent('960 / 960 runs')
    expect(screen.getByText('0.200')).toBeInTheDocument()
    expect(screen.getByText('Independent unit: run', { exact: false })).toBeInTheDocument()
  })
})

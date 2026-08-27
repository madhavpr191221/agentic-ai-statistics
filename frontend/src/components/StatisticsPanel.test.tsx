import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { AnalysisResponse } from '../types'
import { StatisticsPanel } from './StatisticsPanel'

const distribution = {
  summary: { count: 3, missing_count: 0, minimum: 1, maximum: 3, mean: 2, median: 2, sample_standard_deviation: 1, interquartile_range: 1, p50: 2, p90: 2.8, p95: 2.9, p99: 2.98, coefficient_of_variation: 0.5 },
  values: [1, 2, 3], ecdf: [{ value: 1, probability: 1 / 3 }, { value: 2, probability: 2 / 3 }, { value: 3, probability: 1 }],
  histogram: [{ left: 1, right: 2, count: 1 }, { left: 2, right: 3, count: 2 }], quantile_method: 'linear', histogram_rule: 'Freedman-Diaconis',
}
const analysis: AnalysisResponse = { unit: 'call', metric: 'server_handler_latency_ms', selected_run_count: 1, distribution, by_method: [{ key: 'tools/call', distribution }], by_tool: [], by_outcome: [], error_counts: {}, timeline: [], notes: ['Descriptive only.'] }

describe('StatisticsPanel', () => {
  it('renders reproducible summaries and changes experimental unit', () => {
    const onUnitChange = vi.fn()
    render(<StatisticsPanel analysis={analysis} unit="call" onUnitChange={onUnitChange} />)
    expect(screen.getByText('Freedman-Diaconis', { exact: false })).toBeInTheDocument()
    expect(screen.getAllByTestId('plotly-chart')).toHaveLength(3)
    fireEvent.click(screen.getByRole('button', { name: 'Runs' }))
    expect(onUnitChange).toHaveBeenCalledWith('run')
  })
})

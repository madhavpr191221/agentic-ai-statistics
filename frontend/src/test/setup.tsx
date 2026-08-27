import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

vi.mock('react-plotly.js', () => ({
  default: ({ data }: { data?: unknown }) => (
    <div data-testid="plotly-chart" data-traces={Array.isArray(data) ? data.length : 0} />
  ),
}))

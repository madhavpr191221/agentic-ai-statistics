import Plot from 'react-plotly.js'

import type { AnalysisResponse, SummaryStatistics } from '../types'

interface StatisticsPanelProps {
  analysis: AnalysisResponse
  unit: 'call' | 'run'
  onUnitChange: (unit: 'call' | 'run') => void
}

function format(value: number | null, digits = 2) {
  return value === null ? '—' : value.toFixed(digits)
}

function SummaryTable({ summary }: { summary: SummaryStatistics }) {
  const rows = [
    ['n', String(summary.count)],
    ['Missing', String(summary.missing_count)],
    ['Mean', format(summary.mean)],
    ['Median', format(summary.median)],
    ['Sample SD', format(summary.sample_standard_deviation)],
    ['IQR', format(summary.interquartile_range)],
    ['p90', format(summary.p90)],
    ['p95', format(summary.p95)],
    ['p99', format(summary.p99)],
    ['CV', format(summary.coefficient_of_variation, 3)],
  ]
  return (
    <table className="summary-table">
      <tbody>
        {rows.map(([label, value]) => (
          <tr key={label}>
            <th>{label}</th>
            <td>{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

const plotConfig = { responsive: true, displaylogo: false }
const baseLayout = {
  autosize: true,
  height: 300,
  margin: { l: 54, r: 20, t: 42, b: 50 },
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: 'Inter, system-ui, sans-serif', color: '#27343d', size: 12 },
}

export function StatisticsPanel({ analysis, unit, onUnitChange }: StatisticsPanelProps) {
  const { distribution } = analysis
  const binCenters = distribution.histogram.map((bin) => (bin.left + bin.right) / 2)
  const binWidths = distribution.histogram.map((bin) => bin.right - bin.left)

  return (
    <section className="panel statistics-panel" data-testid="statistics-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Descriptive statistics</p>
          <h2>{analysis.metric.replaceAll('_', ' ')}</h2>
        </div>
        <div className="segmented-control" aria-label="Analysis unit">
          <button className={unit === 'call' ? 'active' : ''} onClick={() => onUnitChange('call')}>
            Calls
          </button>
          <button className={unit === 'run' ? 'active' : ''} onClick={() => onUnitChange('run')}>
            Runs
          </button>
        </div>
      </div>

      <div className="analysis-note" role="note">
        {analysis.notes.map((note) => (
          <p key={note}>{note}</p>
        ))}
      </div>

      <div className="statistics-grid">
        <div className="summary-card">
          <h3>Summary</h3>
          <SummaryTable summary={distribution.summary} />
          <p className="method-note">
            Quantiles: {distribution.quantile_method}. Histogram: {distribution.histogram_rule}.
          </p>
        </div>

        <div className="plot-card" data-testid="ecdf-chart">
          <Plot
            data={[
              {
                x: distribution.ecdf.map((point) => point.value),
                y: distribution.ecdf.map((point) => point.probability),
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: '#22577a', shape: 'hv' },
                marker: { size: 6 },
              },
            ]}
            layout={{ ...baseLayout, title: { text: 'Empirical CDF' }, yaxis: { range: [0, 1.02] } }}
            config={plotConfig}
            useResizeHandler
            style={{ width: '100%' }}
          />
        </div>

        <div className="plot-card" data-testid="histogram-chart">
          <Plot
            data={[
              {
                x: binCenters,
                y: distribution.histogram.map((bin) => bin.count),
                width: binWidths,
                type: 'bar',
                marker: { color: '#3a7d78' },
              },
            ]}
            layout={{ ...baseLayout, title: { text: 'Reproducible histogram' } }}
            config={plotConfig}
            useResizeHandler
            style={{ width: '100%' }}
          />
        </div>

        <div className="plot-card" data-testid="boxplot-chart">
          <Plot
            data={[
              {
                y: distribution.values,
                type: 'box',
                name: analysis.metric,
                boxpoints: 'all',
                jitter: 0.3,
                pointpos: -1.5,
                marker: { color: '#ef8354', size: 5 },
              },
            ]}
            layout={{ ...baseLayout, title: { text: 'Observed distribution' }, showlegend: false }}
            config={plotConfig}
            useResizeHandler
            style={{ width: '100%' }}
          />
        </div>
      </div>

      {analysis.by_method.length > 0 ? (
        <div className="group-table-wrap">
          <h3>Grouped by MCP method</h3>
          <table className="data-table compact-table">
            <thead>
              <tr>
                <th>Method</th>
                <th>n</th>
                <th>Mean</th>
                <th>Median</th>
                <th>p95</th>
              </tr>
            </thead>
            <tbody>
              {analysis.by_method.map((group) => (
                <tr key={group.key}>
                  <td>{group.key}</td>
                  <td>{group.distribution.summary.count}</td>
                  <td>{format(group.distribution.summary.mean)}</td>
                  <td>{format(group.distribution.summary.median)}</td>
                  <td>{format(group.distribution.summary.p95)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}

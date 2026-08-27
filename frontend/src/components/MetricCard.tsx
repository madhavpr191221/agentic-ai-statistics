interface MetricCardProps {
  label: string
  value: string | number
  detail?: string
  tone?: 'default' | 'good' | 'warning'
  testId?: string
}

export function MetricCard({ label, value, detail, tone = 'default', testId }: MetricCardProps) {
  return (
    <article className={`metric-card ${tone}`} data-testid={testId}>
      <p>{label}</p>
      <strong>{value}</strong>
      {detail ? <span>{detail}</span> : null}
    </article>
  )
}

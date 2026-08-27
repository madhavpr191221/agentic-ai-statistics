export type ScenarioId =
  | 'list_tools'
  | 'echo'
  | 'sleep'
  | 'backend_exception'
  | 'tool_error'
  | 'timeout'
  | 'nonexistent_tool'
  | 'concurrent'
  | 'cancellation'

export interface ScenarioDescriptor {
  id: ScenarioId
  label: string
  description: string
  expected_outcome: string
}

export interface ExperimentManifest {
  schema_version: string
  experiment_id: string
  condition_id: string
  campaign: string
  run_id: string
  scenario_id: string
  scenario_seed: number
  task_structure: string
  autonomy_level: string
  agent_architecture: string
  model_id: string | null
  transport: 'in_memory' | 'stdio'
  start_time_utc: string
  software_versions: Record<string, string | number | boolean | null>
}

export interface RunSummary {
  run_id: string
  scenario_id: string
  start_time_utc: string
  transport: 'in_memory' | 'stdio'
  event_count: number
  span_count: number
  mcp_request_count: number
  discovery_call_count: number
  tool_call_count: number
  successful_span_count: number
  failed_span_count: number
  failure_proportion: number | null
  observed_trace_window_ms: number | null
  mean_handler_latency_ms: number | null
}

export interface RunDetail {
  manifest: ExperimentManifest
  summary: RunSummary
}

export interface TraceEvent {
  schema_version: string
  event_id: string
  run_id: string
  trace_id: string
  span_id: string
  parent_span_id: string | null
  sequence_number: number
  wall_time_utc: string
  monotonic_time_ns: number
  component: string
  layer: string
  direction: string
  transport: string
  event_kind: 'request_started' | 'request_finished'
  message_type: string
  jsonrpc_id: string | number | null
  mcp_method: string | null
  tool_name: string | null
  payload_bytes: number | null
  frame_bytes: number | null
  payload_hash: string | null
  payload_recording_policy: string
  latency_ms: number | null
  outcome: string
  error_type: string | null
  error_code: string | number | null
  tool_is_error: boolean | null
  metadata: Record<string, unknown>
}

export interface SummaryStatistics {
  count: number
  missing_count: number
  minimum: number | null
  maximum: number | null
  mean: number | null
  median: number | null
  sample_standard_deviation: number | null
  interquartile_range: number | null
  p50: number | null
  p90: number | null
  p95: number | null
  p99: number | null
  coefficient_of_variation: number | null
}

export interface DistributionDescription {
  summary: SummaryStatistics
  values: number[]
  ecdf: Array<{ value: number; probability: number }>
  histogram: Array<{ left: number; right: number; count: number }>
  quantile_method: string
  histogram_rule: string
}

export interface NamedDistribution {
  key: string
  distribution: DistributionDescription
}

export interface TimelineSpan {
  run_id: string
  span_id: string
  method: string
  tool_name: string | null
  outcome: string
  error_type: string | null
  start_offset_ms: number
  event_window_ms: number
  handler_latency_ms: number
}

export interface AnalysisResponse {
  unit: 'call' | 'run'
  metric: string
  selected_run_count: number
  distribution: DistributionDescription
  by_method: NamedDistribution[]
  by_tool: NamedDistribution[]
  by_outcome: NamedDistribution[]
  error_counts: Record<string, number>
  timeline: TimelineSpan[]
  notes: string[]
}

export interface RunParameters {
  scenario: ScenarioId
  repeat: number
  seed: number
}

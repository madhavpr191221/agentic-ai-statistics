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

export interface Phase2RunParameters {
  transport: 'in_memory' | 'stdio'
  payload_target_bytes: number
  service_time_ms: number
  concurrency: number
  calls_per_run: number
  seed: number
}

export interface CallMeasurement {
  run_id: string
  condition_id: string
  call_id: string
  call_index: number
  batch_index: number
  transport: 'in_memory' | 'stdio'
  payload_target_bytes: number
  service_time_ms: number
  concurrency: number
  is_first_call: boolean
  client_roundtrip_ms: number
  outcome: string
  error_type: string | null
  request_payload_bytes: number | null
  request_frame_bytes: number | null
  response_payload_bytes: number | null
  response_frame_bytes: number | null
  server_handler_ms: number | null
}

export interface Phase2RunResponse {
  run_id: string
  condition_id: string
  transport: 'in_memory' | 'stdio'
  session_start_ms: number
  run_elapsed_ms: number
  median_client_roundtrip_ms: number
  median_server_handler_ms: number | null
  median_nonhandler_residual_ms: number | null
  total_request_frame_bytes: number | null
  total_response_frame_bytes: number | null
  calls: CallMeasurement[]
}

export interface CampaignSummary {
  campaign_id: string
  design_name: string
  status: string
  planned_runs: number
  completed_runs: number
  created_at_utc: string
}

export interface ModelCoefficient {
  term: string
  estimate: number
  standard_error: number
  ci_low: number
  ci_high: number
  p_value: number
  latency_ratio: number
}

export interface ConditionSummary {
  transport: string
  payload_target_bytes: number
  service_time_ms: number
  concurrency: number
  n_runs: number
  n_calls: number
  median_ms: number
  median_ci_low: number
  median_ci_high: number
  p90_ms: number
  p95_ms: number
  p95_ci_low: number
  p95_ci_high: number
  iqr_ms: number
}

export interface Phase2Analysis {
  experimental_unit: string
  primary_model: {
    model_type: string
    formula: string
    n_runs: number
    r_squared: number
    adjusted_r_squared: number
    coefficients: ModelCoefficient[]
  }
  mixed_model: {
    formula: string
    converged: boolean
    coefficients?: ModelCoefficient[]
    between_run_variance?: number
    within_run_variance?: number
    icc?: number
    error_type?: string
  }
  byte_model: unknown
  condition_summaries: ConditionSummary[]
  diagnostics: {
    fitted: number[]
    residuals: number[]
    qq_theoretical: number[]
    qq_observed: number[]
  }
  counts: { runs: number; successful_calls: number; failed_calls: number }
  notes: string[]
}

export interface CampaignDetail {
  manifest: {
    campaign_id: string
    design_name: string
    replicates: number
    calls_per_run: number
    transports: string[]
    payload_sizes: number[]
    service_times_ms: number[]
    concurrency_levels: number[]
    planned_runs: unknown[]
  }
  progress: {
    status: string
    planned_runs: number
    completed_runs: number
  }
  analysis: Phase2Analysis | null
}

export type IncidentScenarioId = 'checkout_failures' | 'image_worker_degradation' | 'orders_api_outage'

export interface IncidentScenarioDescriptor { id: IncidentScenarioId; label: string; alert: string }
export interface IncidentScore {
  diagnosis_correct: boolean; required_evidence_present: boolean; correct_remediation_executed: boolean
  no_prohibited_action_attempted: boolean; final_state_resolved: boolean; task_success: boolean
}
export interface IncidentMeasurement {
  status: 'success' | 'failure'; failure_type: string | null; total_latency_ms: number
  model_latency_ms: number; mcp_latency_ms: number; server_handler_latency_ms: number; orchestration_latency_ms: number
  decomposition_consistent: boolean; correlation_consistent: boolean; model_call_count: number; mcp_call_count: number
  tool_sequence: string[]; input_tokens: number; cached_input_tokens: number; output_tokens: number
  total_tokens: number; request_frame_bytes: number; response_frame_bytes: number; estimated_cost_usd: number
}
export interface IncidentRunDetail {
  run_id: string; scenario_id: IncidentScenarioId; created_at_utc: string; model_id: string
  measurement: IncidentMeasurement
  result: null | { incident_id: string; diagnosis: string; evidence_ids: string[]; selected_action: string; action_target: string; resolution_summary: string }
  score: IncidentScore
  actions: Array<{ sequence: number; action: string; target: string; accepted: boolean; prohibited: boolean; result: string }>
  agent_events: Array<{ sequence: number; event: string; elapsed_ms: number | null; tool_name: string | null }>
}
export interface IncidentCampaignSummary {
  campaign_id: string; created_at_utc: string; n_runs: number; successes: number
  success_rate: number; success_rate_wilson_95: [number, number]; total_estimated_cost_usd: number
}

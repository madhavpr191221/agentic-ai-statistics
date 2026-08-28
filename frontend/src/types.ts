export type IncidentScenarioId =
  | 'checkout_failures'
  | 'image_worker_degradation'
  | 'orders_api_outage'

export interface IncidentScenarioDescriptor {
  id: IncidentScenarioId
  label: string
  alert: string
}

export interface IncidentScore {
  diagnosis_correct: boolean
  required_evidence_present: boolean
  correct_remediation_executed: boolean
  no_prohibited_action_attempted: boolean
  final_state_resolved: boolean
  task_success: boolean
}

export interface IncidentMeasurement {
  status: 'success' | 'failure'
  failure_type: string | null
  total_latency_ms: number
  model_latency_ms: number
  mcp_latency_ms: number
  server_handler_latency_ms: number
  orchestration_latency_ms: number
  decomposition_consistent: boolean
  correlation_consistent: boolean
  model_call_count: number
  mcp_call_count: number
  tool_sequence: string[]
  input_tokens: number
  cached_input_tokens: number
  output_tokens: number
  total_tokens: number
  request_frame_bytes: number
  response_frame_bytes: number
  estimated_cost_usd: number
}

export interface IncidentRunDetail {
  run_id: string
  scenario_id: IncidentScenarioId
  created_at_utc: string
  model_id: string
  measurement: IncidentMeasurement
  result: null | {
    incident_id: string
    diagnosis: string
    evidence_ids: string[]
    selected_action: string
    action_target: string
    resolution_summary: string
  }
  score: IncidentScore
  actions: Array<{
    sequence: number
    action: string
    target: string
    accepted: boolean
    prohibited: boolean
    result: string
  }>
  agent_events: Array<{
    sequence: number
    event: string
    elapsed_ms: number | null
    tool_name: string | null
  }>
  behavior?: BehaviorMetadata | null
}

export interface IncidentCampaignSummary {
  campaign_id: string
  created_at_utc: string
  n_runs: number
  successes: number
  success_rate: number
  success_rate_wilson_95: [number, number]
  total_estimated_cost_usd: number
}

export type TaskStructure = 'sequential' | 'branching' | 'recovery'

export interface BehaviorCondition {
  scenario_id: IncidentScenarioId
  label: string
  incoming_message: string
  task_structure: TaskStructure
  oracle_sequence: string[]
}

export interface BehaviorMetadata {
  task_structure: TaskStructure
  incoming_message: string
  oracle_sequence: string[]
  observed_sequence: string[]
  oracle_call_count: number
  excess_mcp_calls: number | null
  normalized_oracle_distance: number
  expected_rejections: number
  unexpected_rejections: number
  trace_steps: Array<{
    sequence: number
    tool_name: string
    classification:
      | 'oracle'
      | 'expected_rejection'
      | 'extra'
      | 'unexpected_rejection'
      | 'prohibited'
  }>
  execution_mode: 'live_measurement' | 'scripted_validation'
  request_frame_bytes: number | null
  response_frame_bytes: number | null
  block: number | null
  execution_order: number | null
}

export interface BehaviorCoefficient {
  term: string
  estimate: number
  standard_error: number
  ci_low: number
  ci_high: number
  p_value: number
  p_value_holm: number | null
  effect_ratio: number | null
  effect_ratio_ci: [number, number] | null
}

export interface BehaviorCampaignAnalysis {
  campaign_id: string
  study_stage: 'pilot' | 'main'
  experimental_unit: string
  n_runs: number
  successes?: number
  success_rate?: number
  primary_outcome?: string
  primary_model?: {
    formula: string
    primary: null | {
      model_type: string
      coefficients: BehaviorCoefficient[]
      pearson_dispersion: number
    }
    negative_binomial_sensitivity: null | {
      fitted: boolean
      converged?: boolean
      coefficients?: BehaviorCoefficient[]
      error_type?: string
      note?: string
    }
    note?: string
  }
  success_model?: {
    available: boolean
    formula: string
    note?: string
    error_type?: string
    coefficients?: BehaviorCoefficient[]
  }
  condition_summaries?: Array<{
    scenario_id: string
    task_structure: TaskStructure
    n_runs: number
    successes: number
    success_rate: number
    median_mcp_calls: number
    median_latency_ms: number
    median_oracle_distance: number
    unique_paths: number
    path_entropy_bits: number
  }>
  mcp_call_distributions?: Array<{
    task_structure: TaskStructure
    values: number[]
    ecdf: Array<{ value: number; probability: number }>
  }>
  transition_summary?: Array<{
    task_structure: TaskStructure
    source_tool: string
    target_tool: string
    count: number
    probability: number
  }>
  notes?: string[]
}

import type {
  AnalysisResponse,
  RunDetail,
  RunParameters,
  RunSummary,
  ScenarioDescriptor,
  TraceEvent,
  CampaignDetail,
  CampaignSummary,
  Phase2RunParameters,
  Phase2RunResponse,
  IncidentRunDetail,
  IncidentScenarioDescriptor,
  IncidentScenarioId,
  IncidentCampaignSummary,
  BehaviorCampaignAnalysis,
  BehaviorCondition,
  TaskStructure,
} from './types'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body && typeof body.detail === 'string' ? body.detail : response.statusText
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const api = {
  listScenarios: () => request<ScenarioDescriptor[]>('/api/scenarios'),
  listRuns: async () => (await request<{ runs: RunSummary[] }>('/api/runs')).runs,
  createRun: (parameters: RunParameters) =>
    request<RunDetail>('/api/runs', {
      method: 'POST',
      body: JSON.stringify(parameters),
    }),
  getRun: (runId: string) => request<RunDetail>(`/api/runs/${runId}`),
  getEvents: async (runId: string) =>
    (await request<{ run_id: string; events: TraceEvent[] }>(`/api/runs/${runId}/events`))
      .events,
  describe: (runIds: string[], unit: 'call' | 'run') =>
    request<AnalysisResponse>('/api/analysis/describe', {
      method: 'POST',
      body: JSON.stringify({ run_ids: runIds, unit }),
    }),
  createPhase2Run: (parameters: Phase2RunParameters) =>
    request<Phase2RunResponse>('/api/phase2/runs', {
      method: 'POST',
      body: JSON.stringify(parameters),
    }),
  listCampaigns: async () =>
    (await request<{ campaigns: CampaignSummary[] }>('/api/campaigns')).campaigns,
  getCampaign: (campaignId: string) =>
    request<CampaignDetail>(`/api/campaigns/${campaignId}`),
  listIncidentScenarios: () => request<IncidentScenarioDescriptor[]>('/api/agent/scenarios'),
  listIncidentRuns: () => request<IncidentRunDetail[]>('/api/agent/runs'),
  createIncidentRun: (scenario: IncidentScenarioId, mode: 'live' | 'deterministic' = 'live') =>
    request<IncidentRunDetail>('/api/agent/runs', { method: 'POST', body: JSON.stringify({ scenario, mode }) }),
  listIncidentCampaigns: () => request<IncidentCampaignSummary[]>('/api/agent/campaigns'),
  listBehaviorConditions: () => request<BehaviorCondition[]>('/api/behavior/conditions'),
  listBehaviorRuns: () => request<IncidentRunDetail[]>('/api/behavior/runs'),
  createBehaviorRun: (
    scenario: IncidentScenarioId,
    taskStructure: TaskStructure,
    mode: 'live' | 'deterministic' = 'live',
  ) => request<IncidentRunDetail>('/api/behavior/runs', {
    method: 'POST',
    body: JSON.stringify({ scenario, task_structure: taskStructure, mode }),
  }),
  listBehaviorCampaigns: () => request<BehaviorCampaignAnalysis[]>('/api/behavior/campaigns'),
}

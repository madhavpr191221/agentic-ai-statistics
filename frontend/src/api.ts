import type {
  BehaviorCampaignAnalysis,
  BehaviorCondition,
  IncidentCampaignSummary,
  IncidentRunDetail,
  IncidentScenarioDescriptor,
  IncidentScenarioId,
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
  listIncidentScenarios: () => request<IncidentScenarioDescriptor[]>('/api/agent/scenarios'),
  listIncidentRuns: () => request<IncidentRunDetail[]>('/api/agent/runs'),
  createIncidentRun: (scenario: IncidentScenarioId, mode: 'live' | 'deterministic' = 'live') =>
    request<IncidentRunDetail>('/api/agent/runs', {
      method: 'POST',
      body: JSON.stringify({ scenario, mode }),
    }),
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
  listBehaviorCampaigns: () =>
    request<BehaviorCampaignAnalysis[]>('/api/behavior/campaigns'),
}

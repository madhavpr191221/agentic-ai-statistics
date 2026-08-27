import type {
  AnalysisResponse,
  RunDetail,
  RunParameters,
  RunSummary,
  ScenarioDescriptor,
  TraceEvent,
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
}

import client from './client'

export interface AttributionModel {
  name: string
  description: string
}

export interface AttributionRequest {
  model: string
  datasource_id: number
  touchpoint_table: string
  conversion_table: string
  time_range?: Record<string, string> | null
  params?: Record<string, any>
}

export async function getAttributionModels(): Promise<AttributionModel[]> {
  const res = await client.get('/attribution/models')
  return res.data.data || []
}

export async function analyzeAttribution(data: AttributionRequest): Promise<any> {
  const res = await client.post('/attribution/analyze', data)
  return res.data.data
}

export function createAttributionSSEUrl(): string {
  return '/api/v1/attribution/analyze/stream'
}
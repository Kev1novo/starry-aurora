import client from './client'

export interface QueryAskRequest {
  question: string
  datasource_id?: number | null
  conversation_id?: string | null
}

export interface QueryResponse {
  sql?: string
  result?: any[]
  explanation?: string
  chart_suggestion?: any
  error?: string
}

export async function askQuestion(data: QueryAskRequest): Promise<QueryResponse> {
  const res = await client.post('/queries/ask', data)
  return res.data.data
}

export async function getQueryHistory(page = 1, pageSize = 20): Promise<{ data: any[]; total: number }> {
  const res = await client.get('/queries/history', { params: { page, page_size: pageSize } })
  return { data: res.data.data || [], total: res.data.total || 0 }
}

export async function getQueryDetail(queryId: number): Promise<any> {
  const res = await client.get(`/queries/${queryId}`)
  return res.data.data
}
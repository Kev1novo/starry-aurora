import client from './client'

export interface Conversation {
  id: number
  title: string
  workspace_type: string
  status: string
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  id: number
  role: string
  content: string
  message_type: string
  created_at: string
  metadata?: Record<string, any>
}

export async function listConversations(page = 1, pageSize = 20): Promise<{ data: Conversation[]; total: number }> {
  const res = await client.get('/conversations', { params: { page, page_size: pageSize } })
  const body = res.data.data || {}
  return { data: body.items || [], total: body.total || 0 }
}

export async function getConversation(id: number): Promise<Conversation> {
  const res = await client.get(`/conversations/${id}`)
  return res.data.data
}

export async function createConversation(data: { title: string; workspace_type?: string }): Promise<Conversation> {
  const res = await client.post('/conversations', data)
  return res.data.data
}

export async function deleteConversation(id: number): Promise<void> {
  await client.delete(`/conversations/${id}`)
}

export async function getConversationMessages(conversationId: number, page = 1, pageSize = 50): Promise<{ data: ConversationMessage[]; total: number }> {
  const res = await client.get(`/conversations/${conversationId}/messages`, { params: { page, page_size: pageSize } })
  const body = res.data.data || {}
  return { data: body.items || [], total: body.total || 0 }
}
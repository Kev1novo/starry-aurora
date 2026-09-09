import { create } from 'zustand'
import type { Conversation } from '@/api/conversations'
import * as conversationApi from '@/api/conversations'

interface ConversationState {
  conversations: Conversation[]
  currentId: number | null
  loading: boolean
  total: number
}

interface ConversationActions {
  fetchConversations: (page?: number, pageSize?: number) => Promise<void>
  selectConversation: (id: number | null) => void
  createConversation: (title: string, workspace_type?: string) => Promise<Conversation | null>
  deleteConversation: (id: number) => Promise<void>
}

type ConversationStore = ConversationState & ConversationActions

const initialState: ConversationState = {
  conversations: [],
  currentId: null,
  loading: false,
  total: 0,
}

export const useConversationStore = create<ConversationStore>()((set) => ({
  ...initialState,

  fetchConversations: async (page = 1, pageSize = 20) => {
    set({ loading: true })
    try {
      const res = await conversationApi.listConversations(page, pageSize)
      set({ conversations: res.data, total: res.total, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  selectConversation: (id) => set({ currentId: id }),

  createConversation: async (title, workspace_type = 'query') => {
    try {
      const conv = await conversationApi.createConversation({ title, workspace_type })
      set((state) => ({
        conversations: [conv, ...state.conversations],
        currentId: conv.id,
        total: state.total + 1,
      }))
      return conv
    } catch {
      return null
    }
  },

  deleteConversation: async (id) => {
    try {
      await conversationApi.deleteConversation(id)
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== id),
        currentId: state.currentId === id ? null : state.currentId,
        total: Math.max(0, state.total - 1),
      }))
    } catch {
      // 错误已在拦截器中处理
    }
  },
}))
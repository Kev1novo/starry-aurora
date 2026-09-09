import { create } from 'zustand'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  sql?: string
  chart?: any
}

interface QueryState {
  question: string
  messages: ChatMessage[]
  isLoading: boolean
  currentConversationId: string | null
}

interface QueryActions {
  setQuestion: (question: string) => void
  addMessage: (message: ChatMessage) => void
  setLoading: (loading: boolean) => void
  clearMessages: () => void
  setCurrentConversation: (id: string | null) => void
}

type QueryStore = QueryState & QueryActions

const initialState: QueryState = {
  question: '',
  messages: [],
  isLoading: false,
  currentConversationId: null,
}

export const useQueryStore = create<QueryStore>()((set) => ({
  ...initialState,

  setQuestion: (question) => set({ question }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  setLoading: (loading) => set({ isLoading: loading }),

  clearMessages: () => set({ messages: [], currentConversationId: null }),

  setCurrentConversation: (id) => set({ currentConversationId: id }),
}))
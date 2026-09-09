import { create } from 'zustand'
import type { AttributionModel } from '@/api/attribution'
import * as attributionApi from '@/api/attribution'

export interface AttributionParams {
  datasource_id: number
  touchpoint_table: string
  conversion_table: string
  time_range?: Record<string, string> | null
  model_params?: Record<string, any>
}

interface AttributionState {
  models: AttributionModel[]
  selectedModel: string
  params: AttributionParams
  result: any
  isLoading: boolean
}

interface AttributionActions {
  fetchModels: () => Promise<void>
  setModel: (model: string) => void
  setParams: (params: Partial<AttributionParams>) => void
  setResult: (result: any) => void
  setLoading: (loading: boolean) => void
  resetResult: () => void
}

type AttributionStore = AttributionState & AttributionActions

const defaultParams: AttributionParams = {
  datasource_id: 0,
  touchpoint_table: '',
  conversion_table: '',
  time_range: null,
  model_params: {},
}

const initialState: AttributionState = {
  models: [],
  selectedModel: '',
  params: { ...defaultParams },
  result: null,
  isLoading: false,
}

export const useAttributionStore = create<AttributionStore>()((set) => ({
  ...initialState,

  fetchModels: async () => {
    try {
      const models = await attributionApi.getAttributionModels()
      set({ models })
      if (models.length > 0 && !initialState.selectedModel) {
        set({ selectedModel: models[0].name })
      }
    } catch {
      // 错误已在拦截器中处理
    }
  },

  setModel: (model) => set({ selectedModel: model }),

  setParams: (partial) =>
    set((state) => ({ params: { ...state.params, ...partial } })),

  setResult: (result) => set({ result }),

  setLoading: (loading) => set({ isLoading: loading }),

  resetResult: () => set({ result: null }),
}))
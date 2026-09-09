import { useCallback, useEffect } from 'react'
import { message } from 'antd'
import { useAttributionStore } from '@/stores/attributionStore'
import * as attributionApi from '@/api/attribution'
import { useSSE } from './useSSE'

/**
 * useAttribution — 归因分析 hook
 *
 * 支持常规 API 调用和 SSE 流式两种分析模式。
 */
export function useAttribution() {
  const {
    models,
    selectedModel,
    params,
    result,
    isLoading,
    fetchModels,
    setModel,
    setParams,
    setResult,
    setLoading,
    resetResult,
  } = useAttributionStore()

  const { isConnected, connect, disconnect } = useSSE()

  /** 组件挂载时获取可用模型列表 */
  useEffect(() => {
    if (models.length === 0) {
      fetchModels()
    }
  }, [models.length, fetchModels])

  /** 执行归因分析（常规 API） */
  const runAnalysis = useCallback(async () => {
    if (!selectedModel) {
      message.warning('请选择归因模型')
      return
    }
    if (!params.datasource_id || !params.touchpoint_table || !params.conversion_table) {
      message.warning('请完善归因分析参数')
      return
    }

    setLoading(true)
    resetResult()

    try {
      const res = await attributionApi.analyzeAttribution({
        model: selectedModel,
        datasource_id: params.datasource_id,
        touchpoint_table: params.touchpoint_table,
        conversion_table: params.conversion_table,
        time_range: params.time_range,
        params: params.model_params,
      })
      setResult(res)
      message.success('归因分析完成')
    } catch {
      // 错误已在拦截器中处理
    } finally {
      setLoading(false)
    }
  }, [selectedModel, params, setLoading, resetResult, setResult])

  /** 通过 SSE 流式执行归因分析 */
  const runAnalysisStream = useCallback(async () => {
    if (!selectedModel) {
      message.warning('请选择归因模型')
      return
    }
    if (!params.datasource_id || !params.touchpoint_table || !params.conversion_table) {
      message.warning('请完善归因分析参数')
      return
    }

    setLoading(true)
    resetResult()

    connect({
      url: attributionApi.createAttributionSSEUrl(),
      method: 'POST',
      body: {
        model: selectedModel,
        datasource_id: params.datasource_id,
        touchpoint_table: params.touchpoint_table,
        conversion_table: params.conversion_table,
        time_range: params.time_range,
        params: params.model_params,
      },
      onEvent: (event) => {
        if (event.type === 'progress') {
          // 进度事件，可触发 UI 更新
        } else if (event.type === 'result') {
          setResult(event.data)
        }
      },
      onDone: () => {
        message.success('归因分析完成')
        setLoading(false)
      },
      onError: (err) => {
        message.error(`归因分析失败: ${err.message || '未知错误'}`)
        setLoading(false)
      },
    })
  }, [selectedModel, params, setLoading, resetResult, connect, setResult])

  /** 取消当前分析 */
  const cancelAnalysis = useCallback(() => {
    disconnect()
    setLoading(false)
  }, [disconnect, setLoading])

  return {
    models,
    selectedModel,
    params,
    result,
    isLoading,
    isConnected,
    setModel,
    setParams,
    setResult,
    resetResult,
    runAnalysis,
    runAnalysisStream,
    cancelAnalysis,
  }
}
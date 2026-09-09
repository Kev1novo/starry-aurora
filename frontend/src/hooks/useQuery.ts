import { useCallback } from 'react'
import { message } from 'antd'
import { useQueryStore, type ChatMessage } from '@/stores/queryStore'
import * as queriesApi from '@/api/queries'
import { createAttributionSSEUrl } from '@/api/attribution'
import { useSSE } from './useSSE'

/**
 * useQuery — 自然语言查询 hook
 *
 * 支持两种模式：
 * 1. 常规 API 调用 (askQuestion) — 一次请求拿到完整结果
 * 2. SSE 流式调用 — 逐步接收 SQL/结果/图表
 */
export function useQuery() {
  const {
    question,
    messages,
    isLoading,
    currentConversationId,
    setQuestion,
    addMessage,
    setLoading,
    clearMessages,
    setCurrentConversation,
  } = useQueryStore()

  const { isConnected, connect, disconnect } = useSSE()

  /** 提交问题（常规 API 模式） */
  const submit = useCallback(
    async (q?: string, datasourceId?: number | null) => {
      const query = q ?? question
      if (!query.trim()) return

      // 添加用户消息
      const userMessage: ChatMessage = { role: 'user', content: query }
      addMessage(userMessage)

      setLoading(true)

      try {
        const res = await queriesApi.askQuestion({
          question: query,
          datasource_id: datasourceId ?? null,
          conversation_id: currentConversationId,
        })

        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: res.explanation || res.sql || '查询完成',
          sql: res.sql,
          chart: res.chart_suggestion,
        }
        addMessage(assistantMessage)
      } catch {
        // 错误已在拦截器中显示
      } finally {
        setLoading(false)
      }
    },
    [question, currentConversationId, addMessage, setLoading],
  )

  /** 通过 SSE 流式提交问题 */
  const submitStream = useCallback(
    async (q?: string, datasourceId?: number | null) => {
      const query = q ?? question
      if (!query.trim()) return

      const userMessage: ChatMessage = { role: 'user', content: query }
      addMessage(userMessage)
      setLoading(true)

      let sqlAccumulator = ''
      let contentAccumulator = ''
      let chartResult: any = null

      connect({
        url: createAttributionSSEUrl(),
        method: 'POST',
        body: {
          question: query,
          datasource_id: datasourceId ?? null,
          conversation_id: currentConversationId,
        },
        onEvent: (event) => {
          if (event.type === 'sql') {
            sqlAccumulator += event.data
          } else if (event.type === 'explanation') {
            contentAccumulator += event.data
          } else if (event.type === 'chart') {
            chartResult = event.data
          }
        },
        onDone: () => {
          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: contentAccumulator || sqlAccumulator || '查询完成',
            sql: sqlAccumulator || undefined,
            chart: chartResult,
          }
          addMessage(assistantMessage)
          setLoading(false)
        },
        onError: (err) => {
          message.error(`流式查询失败: ${err.message || '未知错误'}`)
          setLoading(false)
        },
      })
    },
    [question, currentConversationId, addMessage, setLoading, connect],
  )

  const clear = useCallback(() => {
    disconnect()
    clearMessages()
  }, [disconnect, clearMessages])

  return {
    question,
    messages,
    isLoading,
    isConnected,
    currentConversationId,
    setQuestion,
    setCurrentConversation,
    submit,
    submitStream,
    clear,
  }
}
import { useState, useRef, useEffect, useCallback } from 'react'
import { Typography, Input, Button, Avatar, Spin, Alert, Tag, Space, Flex } from 'antd'
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  StopOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import { useAuthStore } from '@/stores/authStore'
import SqlPreview from './SqlPreview'
import ResultTable from './ResultTable'
import ResultChart from './ResultChart'
import type { ChartSuggestion } from './ResultChart'

const { Text, Paragraph } = Typography
const { TextArea } = Input

/** 单条消息 */
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sql?: string | null
  chartData?: any[] | null
  chartSuggestion?: ChartSuggestion | null
  resultData?: any[] | null
  isLoading?: boolean
  isError?: boolean
}

interface ChatPanelProps {
  conversationId?: string | null
  datasourceId?: number | null
}

let msgCounter = 0
const genId = () => `msg_${Date.now()}_${++msgCounter}`

/**
 * 聊天查询面板
 *
 * 核心交互组件：用户在输入框提问后通过 SSE 流式获取结果，
 * 逐步展示意图、SQL、结果表和图表推荐
 */
export default function ChatPanel({
  conversationId,
  datasourceId,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [streamStatus, setStreamStatus] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  /** 自动滚动到底部 */
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  /** 聚焦输入框 */
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  /** 更新最后一条 AI 消息 */
  const updateLastAssistant = useCallback((patch: Partial<Message>) => {
    setMessages((prev) => {
      const idx = prev.length - 1
      if (idx < 0 || prev[idx].role !== 'assistant') return prev
      const updated = [...prev]
      updated[idx] = { ...updated[idx], ...patch }
      return updated
    })
  }, [])

  /** 解析 SSE 行 */
  const parseSSELine = (line: string) => {
    if (line.startsWith('event: ')) {
      return { type: 'event', value: line.slice(7).trim() } as const
    }
    if (line.startsWith('data: ')) {
      return { type: 'data', value: line.slice(6).trim() } as const
    }
    return null
  }

  /** 提交问题 */
  const handleSubmit = async () => {
    const question = input.trim()
    if (!question || submitting) return

    setInput('')
    setSubmitting(true)
    setStreamStatus('正在分析问题...')

    // 添加用户消息
    setMessages((prev) => [
      ...prev,
      { id: genId(), role: 'user', content: question },
    ])

    // 添加 AI 加载占位
    const aiId = genId()
    setMessages((prev) => [
      ...prev,
      { id: aiId, role: 'assistant', content: '', isLoading: true },
    ])

    // 收集 SSE 数据
    let collectedSql: string | null = null
    let collectedResult: any[] | null = null
    let collectedChart: ChartSuggestion | null = null
    let collectedExplanation = ''

    const token = useAuthStore.getState().token
    const controller = new AbortController()
    abortRef.current = controller

    try {
      const response = await fetch('/api/v1/queries/ask/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          question,
          datasource_id: datasourceId ?? undefined,
          conversation_id: conversationId ?? undefined,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        throw new Error(`请求失败 (${response.status})`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('无法读取响应流')

      const decoder = new TextDecoder()
      let buffer = ''

      // SSE 逐块读取解析
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // 按 \n\n 分割事件
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || '' // 保留最后一个不完整的块

        let currentEvent: string | null = null

        for (const part of parts) {
          const lines = part.split('\n')
          for (const line of lines) {
            const parsed = parseSSELine(line)
            if (!parsed) continue

            if (parsed.type === 'event') {
              currentEvent = parsed.value
            } else if (parsed.type === 'data' && currentEvent) {
              try {
                const payload = JSON.parse(parsed.value)

                switch (currentEvent) {
                  case 'intent': {
                    const intentText = payload?.description || payload?.type || ''
                    setStreamStatus(`意图识别: ${intentText}`)
                    collectedExplanation += `[分析] ${intentText}\n`
                    break
                  }
                  case 'schema': {
                    const count = payload?.tables ?? payload?.count ?? ''
                    setStreamStatus(`已加载 ${count} 张表的 Schema`)
                    collectedExplanation += `[Schema] 已加载 ${count} 张表\n`
                    break
                  }
                  case 'sql': {
                    const sql = payload?.sql || payload?.statement || ''
                    if (sql) {
                      collectedSql = sql
                      setStreamStatus('SQL 已生成')
                      collectedExplanation += `[SQL] 已生成查询语句\n`
                    }
                    break
                  }
                  case 'result': {
                    const rows = payload?.rows || payload?.data || payload || []
                    if (Array.isArray(rows)) {
                      collectedResult = rows
                    }
                    // 尝试从 payload 中提取图表推荐
                    if (payload?.chart_suggestion || payload?.chart) {
                      const cs = payload?.chart_suggestion || payload?.chart
                      collectedChart = {
                        chartType: cs?.chartType || cs?.type || 'bar',
                        title: cs?.title || '',
                        xField: cs?.xField || cs?.x || '',
                        yField: cs?.yField || cs?.y || '',
                      }
                    }
                    setStreamStatus('查询完成，渲染结果')
                    break
                  }
                  case 'chart': {
                    // 单独的 chart 事件
                    collectedChart = {
                      chartType: payload?.chartType || payload?.type || 'bar',
                      title: payload?.title || '',
                      xField: payload?.xField || payload?.x || '',
                      yField: payload?.yField || payload?.y || '',
                    }
                    break
                  }
                  case 'error': {
                    const errMsg = payload?.message || payload?.error || '未知错误'
                    throw new Error(errMsg)
                  }
                  case 'done': {
                    // 完成标记，不处理
                    break
                  }
                }
              } catch (parseErr) {
                if (parseErr instanceof SyntaxError) {
                  // JSON 解析失败，忽略该事件
                  continue
                }
                throw parseErr
              }
            }
          }
        }
      }

      // 流结束，更新消息
      const finalContent =
        collectedExplanation || (collectedResult ? '查询已完成' : '')

      updateLastAssistant({
        content: finalContent,
        sql: collectedSql,
        resultData: collectedResult,
        chartSuggestion: collectedChart,
        isLoading: false,
      })

      setStreamStatus(null)
    } catch (err: any) {
      if (err.name === 'AbortError') {
        updateLastAssistant({
          content: '查询已取消',
          isLoading: false,
        })
      } else {
        updateLastAssistant({
          content: '',
          isError: true,
          isLoading: false,
        })
      }
      setStreamStatus(null)
    } finally {
      setSubmitting(false)
      abortRef.current = null
    }
  }

  /** 取消请求 */
  const handleCancel = () => {
    abortRef.current?.abort()
    setSubmitting(false)
    setStreamStatus(null)
  }

  /** 键盘快捷键：Enter 发送，Shift+Enter 换行 */
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* 消息列表 */}
      <div
        ref={listRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px 24px',
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: '#bbb',
              userSelect: 'none',
            }}
          >
            <ThunderboltOutlined style={{ fontSize: 48, marginBottom: 16, color: '#d9d9d9' }} />
            <Text type="secondary" style={{ fontSize: 16 }}>
              输入自然语言问题开始数据查询
            </Text>
            <Text type="secondary" style={{ fontSize: 13, marginTop: 8 }}>
              例如：上月各渠道的销售额是多少？
            </Text>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              marginBottom: 20,
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            {/* AI 消息 */}
            {msg.role === 'assistant' && (
              <div style={{ display: 'flex', gap: 10, maxWidth: '85%' }}>
                <Avatar
                  icon={<RobotOutlined />}
                  style={{
                    background: '#1677ff',
                    flexShrink: 0,
                    marginTop: 4,
                  }}
                />
                <div>
                  {/* 消息气泡 */}
                  <div
                    style={{
                      background: '#fff',
                      borderRadius: '0 12px 12px 12px',
                      padding: '12px 16px',
                      boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
                    }}
                  >
                    {msg.isLoading && !msg.content && !msg.sql && (
                      <Space>
                        <Spin size="small" />
                        <Text type="secondary">正在分析...</Text>
                      </Space>
                    )}

                    {msg.content && (
                      <Paragraph
                        style={{ marginBottom: 8, whiteSpace: 'pre-wrap' }}
                      >
                        {msg.content}
                      </Paragraph>
                    )}

                    {/* SQL 预览 */}
                    {msg.sql && <SqlPreview sql={msg.sql} />}

                    {/* 结果表格 */}
                    {msg.resultData && msg.resultData.length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <ResultTable data={msg.resultData} />
                      </div>
                    )}

                    {/* 图表 */}
                    {msg.chartSuggestion && msg.resultData && (
                      <div style={{ marginTop: 12 }}>
                        <ResultChart
                          chartSuggestion={msg.chartSuggestion}
                          data={msg.resultData}
                        />
                      </div>
                    )}

                    {/* 空结果 */}
                    {!msg.isLoading &&
                      !msg.isError &&
                      !msg.content &&
                      !msg.sql &&
                      !msg.resultData && (
                        <Text type="secondary">未返回结果</Text>
                      )}

                    {/* 错误 */}
                    {msg.isError && (
                      <Alert
                        type="error"
                        message="查询出错"
                        description="请重试或联系管理员"
                        showIcon
                        style={{ margin: 0 }}
                      />
                    )}

                    {/* 加载中的 SQL 和结果占位 */}
                    {msg.isLoading && (
                      <div style={{ marginTop: 8 }}>
                        {streamStatus && (
                          <Tag icon={<Spin size="small" />} color="processing">
                            {streamStatus}
                          </Tag>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* 用户消息 */}
            {msg.role === 'user' && (
              <div style={{ display: 'flex', gap: 10, maxWidth: '75%' }}>
                <div
                  style={{
                    background: '#1677ff',
                    color: '#fff',
                    borderRadius: '12px 12px 0 12px',
                    padding: '10px 16px',
                  }}
                >
                  <Text style={{ color: '#fff', whiteSpace: 'pre-wrap' }}>
                    {msg.content}
                  </Text>
                </div>
                <Avatar
                  icon={<UserOutlined />}
                  style={{
                    background: '#52c41a',
                    flexShrink: 0,
                    marginTop: 4,
                  }}
                />
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 底部输入区域 */}
      <div
        style={{
          borderTop: '1px solid #f0f0f0',
          padding: '12px 24px 16px',
          background: '#fff',
        }}
      >
        {streamStatus && (
          <div style={{ marginBottom: 8, textAlign: 'center' }}>
            <Tag icon={<Spin size="small" />} color="processing">
              {streamStatus}
            </Tag>
          </div>
        )}
        <Flex gap={8} align="end">
          <TextArea
            ref={inputRef as any}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入自然语言问题，Enter 发送，Shift+Enter 换行"
            autoSize={{ minRows: 1, maxRows: 6 }}
            disabled={submitting}
            style={{ flex: 1, borderRadius: 8 }}
          />
          {submitting ? (
            <Button
              danger
              icon={<StopOutlined />}
              onClick={handleCancel}
              style={{ height: 38 }}
            >
              停止
            </Button>
          ) : (
            <Button
              type="primary"
              icon={<SendOutlined />}
              onClick={handleSubmit}
              disabled={!input.trim()}
              style={{ height: 38 }}
            >
              发送
            </Button>
          )}
        </Flex>
      </div>
    </div>
  )
}
/**
 * 对话相关的类型定义
 */

/** 消息角色 */
export type MessageRole = 'user' | 'assistant' | 'system'

/** 消息状态 */
export type MessageStatus = 'sending' | 'sent' | 'completed' | 'failed'

/** 单条对话消息 */
export interface Message {
  /** 消息 ID */
  id: string
  /** 会话 ID */
  conversation_id: string
  /** 消息角色 */
  role: MessageRole
  /** 消息内容 */
  content: string
  /** 关联的 SQL（如果是查询类消息） */
  sql?: string
  /** 消息状态 */
  status: MessageStatus
  /** 创建时间 */
  created_at: string
}

/** 对话会话 */
export interface Conversation {
  /** 会话 ID */
  id: string
  /** 会话标题 */
  title: string
  /** 关联的数据源 ID */
  datasource_id?: number
  /** 消息数量 */
  message_count: number
  /** 创建时间 */
  created_at: string
  /** 最后活跃时间 */
  updated_at: string
}

/** 创建会话请求 */
export interface CreateConversationParams {
  /** 会话标题 */
  title?: string
  /** 关联数据源 ID */
  datasource_id?: number
}

/** 发送消息请求 */
export interface SendMessageParams {
  /** 消息内容（自然语言问题） */
  content: string
  /** 会话 ID */
  conversation_id?: string
  /** 关联数据源 */
  datasource_id?: number
}
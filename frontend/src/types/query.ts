/**
 * NL2SQL 查询相关的类型定义
 */

/** 查询请求参数 */
export interface QueryRequest {
  /** 自然语言问题 */
  question: string
  /** 会话 ID，用于多轮对话上下文 */
  conversation_id?: string
  /** 数据源 ID */
  datasource_id?: number
}

/** 查询意图识别结果 */
export interface QueryIntent {
  /** 查询类型 */
  type: 'aggregation' | 'detail' | 'trend' | 'comparison'
  /** 识别出的实体 */
  entities: {
    /** 时间范围描述 */
    time_range?: string
    /** 维度字段列表 */
    dimensions?: string[]
    /** 指标字段列表 */
    metrics?: string[]
    /** 过滤条件 */
    filters?: Record<string, unknown>
  }
}

/** 查询结果（结构化表格数据） */
export interface QueryResult {
  /** 列名列表 */
  columns: string[]
  /** 数据行 */
  rows: unknown[][]
  /** 总行数 */
  total: number
  /** 当前页码 */
  page?: number
}

/** 查询历史记录 */
export interface QueryHistory {
  /** 历史记录 ID */
  id: string
  /** 用户的自然语言问题 */
  question: string
  /** 生成的 SQL */
  sql: string
  /** 查询状态 */
  status: 'pending' | 'running' | 'completed' | 'failed'
  /** 创建时间 */
  created_at: string
}
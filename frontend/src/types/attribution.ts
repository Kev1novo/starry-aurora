/**
 * 归因分析相关的类型定义
 *
 * 占位阶段，后续阶段完善
 */

/** 归因分析方法 */
export type AttributionMethod = 'shapley' | 'mta' | 'markov' | 'custom'

/** 归因分析请求 */
export interface AttributionRequest {
  /** 数据源 ID */
  datasource_id: number
  /** 归因分析方法 */
  method: AttributionMethod
  /** 分析的时间范围 */
  start_date: string
  end_date: string
  /** 目标指标 */
  metric: string
  /** 维度拆分字段 */
  dimensions?: string[]
  /** 额外筛选条件 */
  filters?: Record<string, unknown>
}

/** 归因贡献项 */
export interface AttributionItem {
  /** 渠道/维度值 */
  name: string
  /** 贡献值 */
  value: number
  /** 贡献占比（百分比） */
  proportion: number
}

/** 归因分析结果 */
export interface AttributionResult {
  /** 分析方法 */
  method: AttributionMethod
  /** 总目标值 */
  total_value: number
  /** 各维度贡献明细 */
  items: AttributionItem[]
  /** 分析时间范围 */
  start_date: string
  end_date: string
}
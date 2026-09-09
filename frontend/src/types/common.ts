/**
 * 通用 TypeScript 类型定义
 */

/** 分页请求参数 */
export interface PaginationParams {
  /** 当前页码，从 1 开始 */
  page?: number
  /** 每页条数 */
  pageSize?: number
  /** 排序字段 */
  sortBy?: string
  /** 排序方向 */
  sortOrder?: 'ascend' | 'descend'
}

/** 分页响应数据 */
export interface PaginationResult<T> {
  /** 数据列表 */
  items: T[]
  /** 总条数 */
  total: number
  /** 当前页码 */
  page: number
  /** 每页条数 */
  pageSize: number
  /** 总页数 */
  totalPages: number
}

/** 统一 API 响应包装 */
export interface ApiResponse<T = unknown> {
  /** 业务状态码 */
  code: number
  /** 提示消息 */
  message: string
  /** 响应数据 */
  data: T
}

/** 列表查询响应（直接返回数组） */
export interface ListResponse<T> {
  code: number
  message: string
  data: T[]
}

/** 通用下拉选项 */
export interface SelectOption {
  label: string
  value: string | number
  disabled?: boolean
}

/** 通用状态枚举 */
export type Status = 'active' | 'inactive' | 'deleted'

/** 时间区间 */
export interface TimeRange {
  startTime: string
  endTime: string
}
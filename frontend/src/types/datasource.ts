/**
 * 数据源相关的类型定义
 */

/** 数据源类型 */
export type DataSourceType = 'mysql' | 'postgresql' | 'clickhouse'

/** 数据源连接状态 */
export type DataSourceStatus = 'connected' | 'disconnected' | 'error'

/** 数据源 */
export interface DataSource {
  /** 数据源 ID */
  id: number
  /** 数据源名称 */
  name: string
  /** 数据库类型 */
  type: DataSourceType
  /** 主机地址 */
  host: string
  /** 端口号 */
  port: number
  /** 数据库名称 */
  database_name: string
  /** 连接状态 */
  status: DataSourceStatus
  /** 创建时间 */
  created_at: string
}

/** 数据源详情（编辑时回填用） */
export interface DataSourceDetail extends DataSource {
  /** 用户名 */
  username: string
}

/** 表字段详情（对齐后端 SchemaMetaResponse） */
export interface ColumnField {
  /** 字段名 */
  column_name: string
  /** 数据类型 */
  data_type: string
  /** 是否可空 */
  is_nullable: boolean
  /** 默认值 */
  column_default: string | null
  /** 是否主键 */
  is_primary_key: boolean
  /** 字段注释 */
  column_comment: string | null
  /** 顺序 */
  ordinal_position: number
  /** 业务描述（用户自定义） */
  description?: string | null
  /** 是否外键 */
  is_foreign_key: boolean
  /** 是否有索引 */
  indexed: boolean
}

/** 表信息（对齐后端 SchemaTableResponse） */
export interface TableInfo {
  /** 表名 */
  table_name: string
  /** 字段列表 */
  columns: ColumnField[]
  /** 字段数 */
  column_count: number
}

/** 创建数据源请求 */
export interface CreateDataSourceParams {
  /** 数据源名称 */
  name: string
  /** 数据库类型 */
  type: DataSourceType
  /** 主机地址 */
  host: string
  /** 端口号 */
  port: number
  /** 数据库名称 */
  database_name: string
  /** 用户名 */
  username: string
  /** 密码 */
  password: string
}

/** 测试数据源连接请求 */
export interface TestConnectionParams {
  type: DataSourceType
  host: string
  port: number
  database_name: string
  username: string
  password: string
}

/** 测试连接结果 */
export interface TestConnectionResult {
  /** 是否成功 */
  success: boolean
  /** 延迟（毫秒） */
  latency_ms: number
  /** 错误信息 */
  message?: string
}

/** 数据源查询参数（API 使用 snake_case） */
export interface DataSourceQueryParams {
  page?: number
  page_size?: number
}

/** 同步 Schema 结果 */
export interface SyncSchemaResult {
  /** 同步的表数量 */
  tables_count: number
  /** 同步的字段数量 */
  fields_count: number
  /** 同步状态 */
  status: 'success' | 'partial' | 'failed'
  /** 错误信息 */
  message?: string
}
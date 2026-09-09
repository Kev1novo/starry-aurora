import client from '@/api/client'
import type { ApiResponse, PaginationResult } from '@/types/common'
import type {
  DataSource,
  CreateDataSourceParams,
  TestConnectionParams,
  TestConnectionResult,
  SyncSchemaResult,
  DataSourceQueryParams,
  TableInfo,
  ColumnField,
} from '@/types/datasource'

// ─── 数据源 CRUD ───────────────────────────────────────────────

/**
 * 获取数据源列表（分页）
 * @param params 分页查询参数
 */
export async function getDataSources(params?: DataSourceQueryParams) {
  const res = await client.get<ApiResponse<PaginationResult<DataSource>>>('/datasources', { params })
  return res.data
}

/**
 * 获取单个数据源详情
 * @param id 数据源 ID
 */
export async function getDataSource(id: number) {
  const res = await client.get<ApiResponse<DataSource>>(`/datasources/${id}`)
  return res.data
}

/**
 * 创建数据源
 * @param data 数据源创建参数
 */
export async function createDataSource(data: CreateDataSourceParams) {
  const res = await client.post<ApiResponse<DataSource>>('/datasources', data)
  return res.data
}

/**
 * 更新数据源
 * @param id 数据源 ID
 * @param data 待更新的字段
 */
export async function updateDataSource(id: number, data: Partial<CreateDataSourceParams>) {
  const res = await client.put<ApiResponse<DataSource>>(`/datasources/${id}`, data)
  return res.data
}

/**
 * 删除数据源
 * @param id 数据源 ID
 */
export async function deleteDataSource(id: number) {
  const res = await client.delete<ApiResponse<null>>(`/datasources/${id}`)
  return res.data
}

// ─── 连接与同步 ────────────────────────────────────────────────

/**
 * 测试数据源连接（已保存的数据源）
 * @param id 数据源 ID
 * @param data 可选覆盖的连接参数
 */
export async function testConnection(id: number, data?: Partial<TestConnectionParams>) {
  const res = await client.post<ApiResponse<TestConnectionResult>>(`/datasources/${id}/test`, data ?? {})
  return res.data
}

/**
 * 测试数据源连接（未保存的配置）
 * @param data 连接参数
 */
export async function testConnectionRaw(data: TestConnectionParams) {
  const res = await client.post<ApiResponse<TestConnectionResult>>('/datasources/test', data)
  return res.data
}

/**
 * 触发 Schema 同步
 * @param id 数据源 ID
 */
export async function syncSchema(id: number) {
  const res = await client.post<ApiResponse<SyncSchemaResult>>(`/datasources/${id}/sync`)
  return res.data
}

/**
 * 获取数据源的 Schema 列表（表列表）
 * @param id 数据源 ID
 * @param params 可选查询参数
 */
export async function getSchemas(id: number, params?: { table_name?: string }) {
  const res = await client.get<ApiResponse<TableInfo[]>>(`/datasources/${id}/schemas`, { params })
  return res.data
}

/**
 * 获取数据源的所有表（简略版）
 * @param id 数据源 ID
 */
export async function getTables(id: number) {
  const res = await client.get<ApiResponse<string[]>>(`/datasources/${id}/schemas/tables`)
  return res.data
}

/**
 * 更新字段的业务描述
 * @param datasourceId 数据源 ID
 * @param tableName 表名
 * @param columnName 字段名
 * @param businessDescription 业务描述
 */
export async function updateFieldDescription(
  datasourceId: number,
  tableName: string,
  columnName: string,
  businessDescription: string,
) {
  const res = await client.put<ApiResponse<ColumnField>>(
    `/datasources/${datasourceId}/schemas/tables/${tableName}/columns/${columnName}`,
    { business_description: businessDescription },
  )
  return res.data
}
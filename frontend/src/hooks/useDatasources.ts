import { useState, useCallback, useEffect, useRef } from 'react'
import { message } from 'antd'
import type { DataSource, DataSourceQueryParams } from '@/types/datasource'
import type { PaginationResult } from '@/types/common'
import * as datasourceApi from '@/api/datasources'

/**
 * useDatasources — 管理数据源列表的获取、刷新、删除等操作
 *
 * @param initialParams 初始查询参数
 */
export function useDatasources(initialParams?: DataSourceQueryParams) {
  const [datasources, setDatasources] = useState<DataSource[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(initialParams?.page ?? 1)
  const [pageSize, setPageSize] = useState(initialParams?.page_size ?? 10)
  const mountedRef = useRef(true)

  /** 请求数据源列表 */
  const fetch = useCallback(async (params?: DataSourceQueryParams) => {
    setLoading(true)
    try {
      const res = await datasourceApi.getDataSources(params ?? { page: 1, page_size: 10 })
      const data = res.data as PaginationResult<DataSource>
      setDatasources(data.items ?? [])
      setTotal(data.total ?? 0)
      setPage(data.page ?? 1)
      setPageSize(data.pageSize ?? 10)
    } catch {
      // 错误已在拦截器中统一处理
    } finally {
      if (mountedRef.current) {
        setLoading(false)
      }
    }
  }, [])

  /** 刷新当前分页 */
  const refresh = useCallback(() => {
    fetch({ page, page_size: pageSize })
  }, [fetch, page, pageSize])

  /** 切换分页 */
  const changePage = useCallback(
    (newPage: number, newPageSize: number) => {
      setPage(newPage)
      setPageSize(newPageSize)
      fetch({ page: newPage, page_size: newPageSize })
    },
    [fetch],
  )

  /** 删除数据源（后端删除 + 刷新列表） */
  const remove = useCallback(
    async (id: number) => {
      try {
        await datasourceApi.deleteDataSource(id)
        message.success('数据源已删除')
        refresh()
      } catch {
        // 错误已在拦截器中统一处理
      }
    },
    [refresh],
  )

  /** 同步 Schema */
  const doSyncSchema = useCallback(
    async (id: number) => {
      try {
        const res = await datasourceApi.syncSchema(id)
        const result = res.data
        message.success(
          `同步完成：${result.tables_count} 张表，${result.fields_count} 个字段`,
        )
        refresh()
      } catch {
        message.error('Schema 同步失败')
      }
    },
    [refresh],
  )

  useEffect(() => {
    mountedRef.current = true
    fetch(initialParams ?? { page: 1, page_size: 10 })

    return () => {
      mountedRef.current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    datasources,
    loading,
    total,
    page,
    pageSize,
    fetch,
    refresh,
    changePage,
    remove,
    doSyncSchema,
  }
}
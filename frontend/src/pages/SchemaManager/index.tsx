import { useState, useEffect, useCallback, useRef } from 'react'
import { Typography, Select, Spin, Card, Table, Input, Tag, Empty, message, InputRef } from 'antd'
import { SearchOutlined, TableOutlined, KeyOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { DataSource, TableInfo, ColumnField } from '@/types/datasource'
import { getDataSources, getSchemas, updateFieldDescription } from '@/api/datasources'

const { Title, Paragraph } = Typography
const { Option } = Select

/**
 * Schema 管理页面
 *
 * 选择数据源后展示所有表及字段详情，支持搜索和编辑业务描述
 */
export default function SchemaManagerPage() {
  const [datasources, setDatasources] = useState<DataSource[]>([])
  const [selectedDsId, setSelectedDsId] = useState<number | null>(null)
  const [tables, setTables] = useState<TableInfo[]>([])
  const [loadingDs, setLoadingDs] = useState(false)
  const [loadingSchema, setLoadingSchema] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [editingField, setEditingField] = useState<{ tableName: string; columnName: string } | null>(null)
  const [editValue, setEditValue] = useState('')
  const inputRef = useRef<InputRef>(null)
  const mountedRef = useRef(true)

  /** 加载数据源列表 */
  const fetchDatasources = useCallback(async () => {
    setLoadingDs(true)
    try {
      const res = await getDataSources({ page: 1, page_size: 100 })
      setDatasources(res.data?.items ?? [])
    } catch {
      // 错误已在拦截器中统一处理
    } finally {
      if (mountedRef.current) {
        setLoadingDs(false)
      }
    }
  }, [])

  /** 加载选中数据源的 Schema */
  const fetchSchemas = useCallback(async (dsId: number) => {
    setLoadingSchema(true)
    setTables([])
    try {
      const res = await getSchemas(dsId)
      setTables(res.data ?? [])
    } catch {
      // 错误已在拦截器中统一处理
    } finally {
      if (mountedRef.current) {
        setLoadingSchema(false)
      }
    }
  }, [])

  /** 数据源选择变化 */
  const handleDsChange = (value: number) => {
    setSelectedDsId(value)
    setSearchText('')
    setEditingField(null)
    fetchSchemas(value)
  }

  /** 开始编辑业务描述 */
  const handleStartEdit = (tableName: string, field: ColumnField) => {
    setEditingField({ tableName, columnName: field.column_name })
    setEditValue(field.description ?? '')
    setTimeout(() => inputRef.current?.focus(), 50)
  }

  /** 保存业务描述 */
  const handleSaveDescription = async (tableName: string, columnName: string) => {
    if (selectedDsId === null) return

    try {
      await updateFieldDescription(selectedDsId, tableName, columnName, editValue)
      message.success('业务描述已更新')

      // 就地更新本地状态
      setTables((prev) =>
        prev.map((t) =>
          t.table_name === tableName
            ? {
                ...t,
                columns: t.columns.map((f) =>
                  f.column_name === columnName ? { ...f, description: editValue } : f,
                ),
              }
            : t,
        ),
      )
    } catch {
      // 错误已在拦截器中统一处理
    } finally {
      setEditingField(null)
    }
  }

  /** 字段表格列定义 */
  const fieldColumns = (tableName: string): ColumnsType<ColumnField> => [
    {
      title: '字段名',
      dataIndex: 'column_name',
      key: 'column_name',
      width: 180,
      render: (name: string, record: ColumnField) => (
        <span>
          {record.is_primary_key && (
            <KeyOutlined style={{ color: '#faad14', marginRight: 4 }} title="主键" />
          )}
          {name}
        </span>
      ),
    },
    {
      title: '类型',
      dataIndex: 'data_type',
      key: 'data_type',
      width: 120,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: '可空',
      dataIndex: 'is_nullable',
      key: 'is_nullable',
      width: 64,
      render: (nullable: boolean) => (nullable ? '是' : '否'),
    },
    {
      title: '默认值',
      dataIndex: 'column_default',
      key: 'column_default',
      width: 120,
      render: (val: string | null) => (val ?? '-'),
    },
    {
      title: '注释',
      dataIndex: 'column_comment',
      key: 'column_comment',
      width: 200,
      render: (val: string | null) => val || '-',
    },
    {
      title: '业务描述',
      dataIndex: 'description',
      key: 'description',
      width: 220,
      render: (desc: string | undefined | null, record: ColumnField) => {
        const isEditing =
          editingField?.tableName === tableName && editingField?.columnName === record.column_name

        if (isEditing) {
          return (
            <Input
              ref={inputRef}
              size="small"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onPressEnter={() => handleSaveDescription(tableName, record.column_name)}
              onBlur={handleSaveDescription.bind(null, tableName, record.column_name)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setEditingField(null)
                  setEditValue('')
                }
              }}
              style={{ width: 180 }}
            />
          )
        }

        return (
          <span
            style={{
              cursor: 'pointer',
              color: desc ? undefined : '#bfbfbf',
              minHeight: 22,
              display: 'inline-block',
            }}
            onClick={() => handleStartEdit(tableName, record)}
            title="点击编辑"
          >
            {desc || '点击添加描述'}
          </span>
        )
      },
    },
  ]

  /** 根据搜索文本过滤表名和字段 */
  const filteredTables = tables
    .map((table) => {
      const tableMatch = searchText
        ? table.table_name.toLowerCase().includes(searchText.toLowerCase())
        : true

      if (tableMatch) {
        return table
      }

      // 按字段名过滤
      const matchedColumns = table.columns.filter((f) =>
        f.column_name.toLowerCase().includes(searchText.toLowerCase()),
      )
      return matchedColumns.length > 0 ? { ...table, columns: matchedColumns } : null
    })
    .filter(Boolean) as TableInfo[]

  useEffect(() => {
    mountedRef.current = true
    fetchDatasources()
    return () => {
      mountedRef.current = false
    }
  }, [fetchDatasources])

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={2}>数据表管理</Title>
        <Paragraph type="secondary">浏览数据源下的所有表和字段，支持编辑字段业务描述</Paragraph>
      </div>

      {/* 数据源选择 + 搜索 */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, alignItems: 'center' }}>
        <Spin spinning={loadingDs}>
          <Select
            placeholder="请选择数据源"
            style={{ width: 300 }}
            value={selectedDsId}
            onChange={handleDsChange}
            allowClear
            onClear={() => {
              setSelectedDsId(null)
              setTables([])
              setSearchText('')
            }}
          >
            {datasources.map((ds) => (
              <Option key={ds.id} value={ds.id}>
                {ds.name} ({ds.host}:{ds.port}/{ds.database_name})
              </Option>
            ))}
          </Select>
        </Spin>

        {selectedDsId && (
          <Input
            placeholder="搜索表名或字段名"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            allowClear
            style={{ width: 280 }}
          />
        )}
      </div>

      {/* Schema 内容 */}
      <Spin spinning={loadingSchema}>
        {!selectedDsId ? (
          <Empty description="请先选择一个数据源" />
        ) : filteredTables.length === 0 && !loadingSchema ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={searchText ? '未匹配到表或字段' : '该数据源暂无表数据，请先同步 Schema'}
          />
        ) : (
          filteredTables.map((table) => (
            <Card
              key={table.table_name}
              title={
                <span>
                  <TableOutlined style={{ marginRight: 8 }} />
                  {table.table_name}
                  <span style={{ color: '#8c8c8c', fontWeight: 'normal', marginLeft: 8, fontSize: 13 }}>
                    {table.column_count} 个字段
                  </span>
                </span>
              }
              style={{ marginBottom: 16 }}
              size="small"
            >
              <Table<ColumnField>
                rowKey="column_name"
                columns={fieldColumns(table.table_name)}
                dataSource={table.columns}
                pagination={false}
                size="small"
                scroll={{ x: 900 }}
              />
            </Card>
          ))
        )}
      </Spin>
    </div>
  )
}
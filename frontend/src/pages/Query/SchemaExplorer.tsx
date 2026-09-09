import { useEffect, useState, useMemo } from 'react'
import { Tree, Spin, Typography, Tag, Empty, Input } from 'antd'
import {
  DatabaseOutlined,
  TableOutlined,
  FieldStringOutlined,
  SearchOutlined,
  KeyOutlined,
} from '@ant-design/icons'
import type { DataNode } from 'antd/es/tree'
import { getSchemaFields } from '@/api/schemas'
import type { SchemaField } from '@/api/schemas'

const { Text } = Typography

interface SchemaExplorerProps {
  datasourceId: number | null
}

/**
 * Schema Explorer——展示选定数据源的表和字段结构
 *
 * 使用 Ant Design Tree 组件渲染为可展开的树形结构
 */
export default function SchemaExplorer({ datasourceId }: SchemaExplorerProps) {
  const [fields, setFields] = useState<SchemaField[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')

  useEffect(() => {
    if (!datasourceId) {
      setFields([])
      return
    }

    let cancelled = false
    setLoading(true)

    getSchemaFields(datasourceId)
      .then((data) => {
        if (!cancelled) setFields(data)
      })
      .catch(() => {
        if (!cancelled) setFields([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [datasourceId])

  /** 按表名分组，支持搜索过滤 */
  const treeData = useMemo<DataNode[]>(() => {
    const grouped = new Map<string, SchemaField[]>()
    fields.forEach((f) => {
      if (
        searchText &&
        !f.column_name.toLowerCase().includes(searchText.toLowerCase()) &&
        !f.table_name.toLowerCase().includes(searchText.toLowerCase())
      ) {
        return
      }
      const list = grouped.get(f.table_name) || []
      list.push(f)
      grouped.set(f.table_name, list)
    })

    return Array.from(grouped.entries()).map(([tableName, cols]) => ({
      key: `table:${tableName}`,
      title: (
        <span>
          <TableOutlined style={{ marginRight: 6, color: '#1677ff' }} />
          <Text code>{tableName}</Text>
          <Tag style={{ marginLeft: 6 }} color="default">
            {cols.length}
          </Tag>
        </span>
      ),
      children: cols.map((col) => ({
        key: `col:${tableName}.${col.column_name}`,
        icon: col.is_primary_key ? (
          <KeyOutlined style={{ color: '#faad14' }} />
        ) : (
          <FieldStringOutlined style={{ color: '#73c0de' }} />
        ),
        title: (
          <span>
            <Text>{col.column_name}</Text>
            <Text type="secondary" style={{ marginLeft: 6, fontSize: 12 }}>
              {col.data_type}
            </Text>
            {col.description && (
              <Text
                type="secondary"
                style={{ marginLeft: 6, fontSize: 11 }}
                ellipsis
              >
                — {col.description}
              </Text>
            )}
          </span>
        ),
      })),
    }))
  }, [fields, searchText])

  if (!datasourceId) {
    return (
      <div style={{ padding: 16, textAlign: 'center' }}>
        <DatabaseOutlined
          style={{ fontSize: 32, color: '#d9d9d9', marginBottom: 8 }}
        />
        <Text type="secondary" style={{ display: 'block' }}>
          请先选择数据源
        </Text>
      </div>
    )
  }

  return (
    <div style={{ padding: '12px 8px' }}>
      <div style={{ marginBottom: 12, padding: '0 4px' }}>
        <Input
          size="small"
          placeholder="搜索表名/字段名..."
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
        />
      </div>

      <Spin spinning={loading}>
        {treeData.length === 0 && !loading ? (
          <Empty description="暂无 Schema 数据" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <Tree
            showIcon
            defaultExpandedKeys={
              searchText
                ? treeData.slice(0, 3).map((n) => n.key as string)
                : treeData.slice(0, 1).map((n) => n.key as string)
            }
            treeData={treeData}
            style={{ fontSize: 13 }}
          />
        )}
      </Spin>
    </div>
  )
}
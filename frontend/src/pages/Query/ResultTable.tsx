import { useMemo } from 'react'
import { Table, Button, Space, Empty, Spin, message, Tooltip } from 'antd'
import { DownloadOutlined, TableOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

interface ResultTableProps {
  data: any[] | null
  loading?: boolean
}

/**
 * 查询结果表格
 *
 * 自动从数据第一行推断列定义，支持数据导出（JSON / CSV）
 */
export default function ResultTable({ data, loading = false }: ResultTableProps) {
  /** 根据数据自动生成列定义 */
  const columns = useMemo<ColumnsType<any>>(() => {
    if (!data || data.length === 0) return []

    const keys = Object.keys(data[0])
    return keys.map((key) => ({
      title: key,
      dataIndex: key,
      key,
      ellipsis: true,
      width: 150,
      render: (val: unknown) => {
        if (val === null || val === undefined) return '—'
        if (typeof val === 'object') return JSON.stringify(val)
        return String(val)
      },
    }))
  }, [data])

  /** 导出为 JSON 文件 */
  const exportJSON = () => {
    if (!data || data.length === 0) return
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    })
    downloadBlob(blob, 'query-result.json')
    message.success('JSON 已导出')
  }

  /** 导出为 CSV 文件 */
  const exportCSV = () => {
    if (!data || data.length === 0) return
    const keys = Object.keys(data[0])
    const header = keys.join(',')
    const rows = data.map((row) =>
      keys.map((k) => {
        const val = row[k]
        if (val === null || val === undefined) return ''
        const str = String(val)
        // 包含逗号或引号的字段需要包装
        return str.includes(',') || str.includes('"') || str.includes('\n')
          ? `"${str.replace(/"/g, '""')}"`
          : str
      }).join(','),
    )
    const csv = [header, ...rows].join('\n')
    const bom = '﻿' // 处理 Excel 中文乱码
    const blob = new Blob([bom + csv], { type: 'text/csv;charset=utf-8;' })
    downloadBlob(blob, 'query-result.csv')
    message.success('CSV 已导出')
  }

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin tip="查询执行中..." />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="暂无查询结果"
        style={{ padding: 40, margin: 0 }}
      />
    )
  }

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 8,
        }}
      >
        <Space>
          <TableOutlined />
          <span>
            查询结果（共 {data.length} 行）
          </span>
        </Space>
        <Space size={4}>
          <Tooltip title="导出 JSON">
            <Button size="small" icon={<DownloadOutlined />} onClick={exportJSON}>
              JSON
            </Button>
          </Tooltip>
          <Tooltip title="导出 CSV">
            <Button size="small" icon={<DownloadOutlined />} onClick={exportCSV}>
              CSV
            </Button>
          </Tooltip>
        </Space>
      </div>
      <Table
        dataSource={data.map((row, i) => ({ ...row, _rowKey: i }))}
        columns={columns}
        rowKey="_rowKey"
        size="small"
        scroll={{ x: 'max-content', y: 400 }}
        pagination={{
          pageSize: 50,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
        bordered
      />
    </div>
  )
}
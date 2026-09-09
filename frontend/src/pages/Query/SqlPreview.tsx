import { useState } from 'react'
import { Collapse, Typography, Spin, Button, Tooltip, message, Space } from 'antd'
import { CopyOutlined, CheckOutlined, CodeOutlined } from '@ant-design/icons'

const { Text, Paragraph } = Typography

interface SqlPreviewProps {
  sql: string | null
  loading?: boolean
}

/**
 * SQL 预览面板
 *
 * 折叠面板展示生成的 SQL，支持一键复制
 */
export default function SqlPreview({ sql, loading = false }: SqlPreviewProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    if (!sql) return
    try {
      await navigator.clipboard.writeText(sql)
      setCopied(true)
      message.success('SQL 已复制')
      setTimeout(() => setCopied(false), 2000)
    } catch {
      message.error('复制失败')
    }
  }

  return (
    <Collapse
      ghost
      size="small"
      items={[
        {
          key: 'sql',
          label: (
            <Space size={4}>
              <CodeOutlined />
              <span>生成的 SQL</span>
              {loading && <Spin size="small" style={{ marginLeft: 8 }} />}
            </Space>
          ),
          extra: sql && (
            <Tooltip title="复制 SQL">
              <Button
                type="text"
                size="small"
                icon={copied ? <CheckOutlined /> : <CopyOutlined />}
                onClick={(e) => {
                  e.stopPropagation()
                  handleCopy()
                }}
              />
            </Tooltip>
          ),
          children: loading ? (
            <div style={{ padding: '16px 0', textAlign: 'center' }}>
              <Spin tip="正在生成 SQL..." />
            </div>
          ) : sql ? (
            <div
              style={{
                background: '#f6f8fa',
                borderRadius: 6,
                padding: '12px 16px',
                overflowX: 'auto',
              }}
            >
              <Text code style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
                {sql}
              </Text>
            </div>
          ) : (
            <Paragraph
              type="secondary"
              style={{ margin: 0, padding: '8px 0' }}
            >
              等待生成...
            </Paragraph>
          ),
        },
      ]}
    />
  )
}
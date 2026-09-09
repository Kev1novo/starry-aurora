import { useEffect, useState, useCallback } from 'react'
import { Drawer, List, Typography, Input, Empty, Spin, Tag, Button, Space } from 'antd'
import {
  HistoryOutlined,
  SearchOutlined,
  CalendarOutlined,
} from '@ant-design/icons'
import * as conversationApi from '@/api/conversations'
import type { Conversation } from '@/api/conversations'
import dayjs from 'dayjs'

const { Text } = Typography

interface QueryHistoryProps {
  visible: boolean
  onClose: () => void
  onSelect: (conversationId: number) => void
}

/**
 * 查询历史记录抽屉
 *
 * 展示会话列表，支持搜索过滤，点击加载历史会话
 */
export default function QueryHistory({ visible, onClose, onSelect }: QueryHistoryProps) {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20

  /** 加载会话列表 */
  const fetchList = useCallback(async (p = 1) => {
    setLoading(true)
    try {
      const res = await conversationApi.listConversations(p, pageSize)
      if (p === 1) {
        setConversations(res.data)
      } else {
        setConversations((prev) => [...prev, ...res.data])
      }
      setTotal(res.total)
      setPage(p)
    } catch {
      // 错误已在拦截器中处理
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (visible) {
      fetchList(1)
    }
  }, [visible, fetchList])

  /** 过滤后的列表 */
  const filtered = searchText
    ? conversations.filter((c) =>
        c.title.toLowerCase().includes(searchText.toLowerCase()),
      )
    : conversations

  /** 加载更多 */
  const handleLoadMore = () => {
    if (conversations.length < total) {
      fetchList(page + 1)
    }
  }

  /** 选择会话 */
  const handleSelect = (conv: Conversation) => {
    onSelect(conv.id)
    onClose()
  }

  return (
    <Drawer
      title={
        <Space>
          <HistoryOutlined />
          <span>历史记录</span>
          <Tag>{total}</Tag>
        </Space>
      }
      placement="left"
      width={380}
      open={visible}
      onClose={onClose}
      extra={
        <Button type="text" size="small" onClick={() => fetchList(1)}>
          刷新
        </Button>
      }
    >
      <div style={{ marginBottom: 12 }}>
        <Input
          placeholder="搜索对话标题..."
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          allowClear
        />
      </div>

      <Spin spinning={loading && conversations.length === 0}>
        {filtered.length === 0 && !loading ? (
          <Empty
            description={searchText ? '未匹配到对话' : '暂无历史记录'}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        ) : (
          <List
            dataSource={filtered}
            renderItem={(item) => (
              <List.Item
                style={{
                  cursor: 'pointer',
                  padding: '10px 12px',
                  borderRadius: 6,
                  transition: 'background 0.2s',
                }}
                onMouseEnter={(e) => {
                  ;(e.currentTarget as HTMLElement).style.background = '#f5f5f5'
                }}
                onMouseLeave={(e) => {
                  ;(e.currentTarget as HTMLElement).style.background = 'transparent'
                }}
                onClick={() => handleSelect(item)}
              >
                <div style={{ width: '100%' }}>
                  <Text strong style={{ fontSize: 13 }} ellipsis>
                    {item.title}
                  </Text>
                  <div
                    style={{
                      marginTop: 4,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 12,
                    }}
                  >
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      <CalendarOutlined style={{ marginRight: 4 }} />
                      {dayjs(item.created_at).format('MM-DD HH:mm')}
                    </Text>
                    {item.workspace_type && (
                      <Tag style={{ fontSize: 11 }}>{item.workspace_type}</Tag>
                    )}
                  </div>
                </div>
              </List.Item>
            )}
          />
        )}

        {conversations.length < total && !searchText && (
          <div style={{ textAlign: 'center', marginTop: 12 }}>
            <Button type="link" loading={loading} onClick={handleLoadMore}>
              加载更多
            </Button>
          </div>
        )}
      </Spin>
    </Drawer>
  )
}
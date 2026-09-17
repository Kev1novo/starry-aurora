import { useEffect, useState, useCallback } from 'react'
import {
  Layout,
  Select,
  Button,
  Typography,
  Space,
  message,
  Spin,
  Tooltip,
  Badge,
} from 'antd'
import {
  DatabaseOutlined,
  HistoryOutlined,
  CodeOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons'
import { getDataSources } from '@/api/datasources'
import type { DataSource } from '@/types/datasource'
import { useConversationStore } from '@/stores/conversationStore'
import ChatPanel from './ChatPanel'
import SchemaExplorer from './SchemaExplorer'
import QueryHistory from './QueryHistory'

const { Content, Sider } = Layout
const { Title, Text } = Typography

/**
 * 数据查询页面
 *
 * 布局结构：
 * - 顶部：数据源选择器 + 会话管理
 * - 中间主区域：ChatPanel 聊天查询
 * - 右侧边栏：SchemaExplorer（可折叠）
 */
export default function QueryPage() {
  // ─── 数据源 ──────────────────────────────────────────────────────
  const [datasources, setDatasources] = useState<DataSource[]>([])
  const [selectedDsId, setSelectedDsId] = useState<number | null>(null)
  const [dsLoading, setDsLoading] = useState(true)

  // ─── 侧边栏与历史 ─────────────────────────────────────────────────
  const [schemaCollapsed, setSchemaCollapsed] = useState(true)
  const [historyOpen, setHistoryOpen] = useState(false)

  // ─── 会话 ─────────────────────────────────────────────────────────
  const {
    conversations,
    currentId,
    fetchConversations,
    selectConversation,
    createConversation,
  } = useConversationStore()

  /** 加载数据源列表 */
  useEffect(() => {
    let cancelled = false
    setDsLoading(true)

    getDataSources({ page: 1, page_size: 100 })
      .then((res) => {
        if (!cancelled) {
          const items = res.data?.items || []
          setDatasources(items)
          // 默认选中 demo 数据源，没有则选第一个
          if (items.length > 0 && !selectedDsId) {
            const demo = items.find((ds) =>
              ds.name.toLowerCase().includes('demo'),
            )
            setSelectedDsId(demo?.id ?? items[0].id)
          }
        }
      })
      .catch(() => {
        if (!cancelled) setDatasources([])
      })
      .finally(() => {
        if (!cancelled) setDsLoading(false)
      })

    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /** 加载会话列表 */
  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  /** 创建新对话 */
  const handleNewConversation = async () => {
    const conv = await createConversation('新查询', 'query')
    if (conv) {
      message.success('已创建新对话')
    }
  }

  /** 从历史记录选择会话 */
  const handleHistorySelect = useCallback(
    (convId: number) => {
      selectConversation(convId)
    },
    [selectConversation],
  )

  return (
    <div className="query-page" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      {/* ─── 页面顶部 ─────────────────────────────────────────── */}
      <div
        style={{
          padding: '12px 24px',
          background: '#fff',
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}
      >
        <Space size={16}>
          <Title level={4} style={{ margin: 0 }}>
            <CodeOutlined style={{ marginRight: 8 }} />
            数据查询
          </Title>

          {/* 数据源选择 */}
          <Spin spinning={dsLoading} size="small">
            <Select
              style={{ width: 260 }}
              placeholder="选择数据源"
              loading={dsLoading}
              value={selectedDsId}
              onChange={setSelectedDsId}
              allowClear
              options={datasources.map((ds) => ({
                label: (
                  <Space size={4}>
                    <DatabaseOutlined />
                    <span>{ds.name}</span>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      ({ds.type})
                    </Text>
                  </Space>
                ),
                value: ds.id,
              }))}
            />
          </Spin>

          {/* 会话选择 */}
          <Select
            style={{ width: 200 }}
            placeholder="选择对话"
            value={currentId}
            onChange={(val) => selectConversation(val)}
            allowClear
            options={conversations.map((c) => ({
              label: c.title,
              value: c.id,
            }))}
          />
          <Button size="small" onClick={handleNewConversation}>
            新建对话
          </Button>
        </Space>

        <Space>
          <Tooltip title="历史记录">
            <Badge count={conversations.length} size="small" offset={[-4, 4]}>
              <Button
                icon={<HistoryOutlined />}
                onClick={() => setHistoryOpen(true)}
              >
                历史
              </Button>
            </Badge>
          </Tooltip>

          {/* Schema 侧边栏开关 */}
          <Tooltip title={schemaCollapsed ? '展开 Schema' : '收起 Schema'}>
            <Button
              icon={schemaCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setSchemaCollapsed((v) => !v)}
            />
          </Tooltip>
        </Space>
      </div>

      {/* ─── 主体区域 ─────────────────────────────────────────── */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {/* 左侧主内容 */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            maxWidth: schemaCollapsed ? '100%' : 900,
            margin: '0 auto',
            width: '100%',
            background: '#f5f5f5',
          }}
        >
          <Content
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              background: '#fff',
              margin: 12,
              borderRadius: 8,
              overflow: 'hidden',
              boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
            }}
          >
            <ChatPanel
              conversationId={currentId ? String(currentId) : null}
              datasourceId={selectedDsId}
            />
          </Content>
        </div>

        {/* 右侧 Schema 侧边栏 */}
        {!schemaCollapsed && (
          <Sider
            width={320}
            style={{
              background: '#fff',
              borderLeft: '1px solid #f0f0f0',
              overflow: 'auto',
            }}
          >
            <div
              style={{
                padding: '12px 16px',
                borderBottom: '1px solid #f0f0f0',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <Text strong>
                <DatabaseOutlined style={{ marginRight: 6 }} />
                Schema 结构
              </Text>
            </div>
            <SchemaExplorer datasourceId={selectedDsId} />
          </Sider>
        )}
      </div>

      {/* ─── 历史记录抽屉 ─────────────────────────────────────── */}
      <QueryHistory
        visible={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onSelect={handleHistorySelect}
      />
    </div>
  )
}
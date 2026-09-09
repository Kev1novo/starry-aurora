import { Card, Row, Col, Typography } from 'antd'
import {
  SearchOutlined,
  PartitionOutlined,
  DatabaseOutlined,
  TableOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

const { Title, Paragraph } = Typography

/** 快捷入口卡片配置 */
interface QuickEntry {
  key: string
  title: string
  description: string
  icon: React.ReactNode
  path: string
}

const quickEntries: QuickEntry[] = [
  {
    key: 'query',
    title: '数据查询',
    description: '灵活查询多维数据，支持自定义过滤与聚合',
    icon: <SearchOutlined style={{ fontSize: 32, color: '#1677ff' }} />,
    path: '/query',
  },
  {
    key: 'attribution',
    title: '归因分析',
    description: '多维度归因模型，洞察数据驱动因素',
    icon: <PartitionOutlined style={{ fontSize: 32, color: '#52c41a' }} />,
    path: '/attribution',
  },
  {
    key: 'datasources',
    title: '数据源管理',
    description: '连接与管理各类数据源，支持实时同步',
    icon: <DatabaseOutlined style={{ fontSize: 32, color: '#faad14' }} />,
    path: '/datasources',
  },
  {
    key: 'schemas',
    title: 'Schema 管理',
    description: '定义和管理数据模型，灵活配置字段映射',
    icon: <TableOutlined style={{ fontSize: 32, color: '#ff4d4f' }} />,
    path: '/schemas',
  },
]

/**
 * 工作台首页
 *
 * 欢迎信息 + 快捷入口卡片
 */
export default function Dashboard() {
  const { user } = useAuthStore()
  const navigate = useNavigate()

  return (
    <div className="page-container">
      {/* 页面头部 */}
      <div className="page-header">
        <Title level={2}>欢迎回来，{user?.username || '用户'}</Title>
        <Paragraph type="secondary">
          智数归因平台为您提供全方位的数据查询与分析服务
        </Paragraph>
      </div>

      {/* 快捷入口 */}
      <Row gutter={[16, 16]}>
        {quickEntries.map((entry) => (
          <Col xs={24} sm={12} lg={6} key={entry.key}>
            <Card
              hoverable
              onClick={() => navigate(entry.path)}
              style={{ textAlign: 'center', height: '100%' }}
            >
              <div style={{ marginBottom: 16 }}>{entry.icon}</div>
              <Card.Meta
                title={entry.title}
                description={entry.description}
              />
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  )
}
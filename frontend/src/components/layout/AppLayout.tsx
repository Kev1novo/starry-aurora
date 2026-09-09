import { Layout } from 'antd'
import { Outlet } from 'react-router-dom'
import Sidebar from '@/components/layout/Sidebar'
import HeaderBar from '@/components/layout/Header'

const { Content, Sider } = Layout

/**
 * 主布局组件
 *
 * Ant Design Layout 布局：左侧 Sider 菜单 + 顶部 Header + 中央 Content（Outlet 渲染子页面）
 */
export default function AppLayout() {
  return (
    <Layout style={{ height: '100vh' }}>
      {/* 侧边栏 */}
      <Sider width={220} style={{ background: '#001529' }}>
        <Sidebar />
      </Sider>

      <Layout>
        {/* 顶部导航 */}
        <HeaderBar />

        {/* 内容区域 */}
        <Content
          style={{
            margin: 0,
            background: '#f5f5f5',
            overflow: 'auto',
            height: 'calc(100vh - 64px)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
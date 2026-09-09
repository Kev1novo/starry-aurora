import { Layout, Dropdown, Avatar, Space, Typography } from 'antd'
import { UserOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import type { MenuProps } from 'antd'

const { Text } = Typography

/**
 * 顶部导航栏
 *
 * 显示当前用户信息，提供用户菜单（设置、退出登录）
 */
export default function HeaderBar() {
  const { user, logout: doLogout } = useAuthStore()
  const navigate = useNavigate()

  /** 处理退出登录 */
  const handleLogout = async () => {
    doLogout()
    navigate('/login', { replace: true })
  }

  /** 跳转到用户设置 */
  const goToSettings = () => {
    navigate('/settings')
  }

  /** 下拉菜单配置 */
  const items: MenuProps['items'] = [
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '用户设置',
      onClick: goToSettings,
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ]

  return (
    <Layout.Header
      style={{
        background: '#fff',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'flex-end',
        borderBottom: '1px solid #f0f0f0',
      }}
    >
      <Dropdown menu={{ items }} placement="bottomRight">
        <Space style={{ cursor: 'pointer' }}>
          <Avatar icon={<UserOutlined />} src={user?.avatar} />
          <Text>{user?.username || '用户'}</Text>
        </Space>
      </Dropdown>
    </Layout.Header>
  )
}
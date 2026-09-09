import { useNavigate, useLocation } from 'react-router-dom'
import { Menu } from 'antd'
import {
  DashboardOutlined,
  SearchOutlined,
  PartitionOutlined,
  DatabaseOutlined,
  TableOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import type { MenuProps } from 'antd'

/** 侧边菜单项配置 */
type MenuItem = Required<MenuProps>['items'][number]

const menuItems: MenuItem[] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: '工作台',
  },
  {
    key: '/query',
    icon: <SearchOutlined />,
    label: '数据查询',
  },
  {
    key: '/attribution',
    icon: <PartitionOutlined />,
    label: '归因分析',
  },
  {
    key: '/datasources',
    icon: <DatabaseOutlined />,
    label: '数据源管理',
  },
  {
    key: '/schemas',
    icon: <TableOutlined />,
    label: 'Schema 管理',
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: '系统设置',
  },
]

/**
 * 侧边导航菜单
 *
 * 根据当前路由高亮对应菜单项，点击跳转
 */
export default function Sidebar() {
  const navigate = useNavigate()
  const location = useLocation()

  /** 当前选中菜单项 */
  const selectedKey = '/' + location.pathname.split('/')[1]

  /** 菜单点击处理 */
  const handleClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Logo / 平台名称 */}
      <div
        style={{
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          fontSize: 18,
          fontWeight: 600,
          borderBottom: '1px solid rgba(255,255,255,0.1)',
        }}
      >
        智数归因
      </div>

      {/* 菜单 */}
      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        items={menuItems}
        onClick={handleClick}
        style={{ flex: 1, borderRight: 0 }}
      />
    </div>
  )
}
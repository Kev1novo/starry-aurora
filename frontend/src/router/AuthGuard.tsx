import { Navigate, useLocation, Outlet } from 'react-router-dom'
import { Spin } from 'antd'
import { useAuthStore } from '@/stores/authStore'

interface AuthGuardProps {
  children?: React.ReactNode
}

/**
 * 路由守卫组件
 *
 * 检查认证状态：
 * - initialized 为 false（尚未初始化） -> 显示加载中 Spin
 * - 未认证 -> 跳转到 /login，并记录来源路径（登录后可回跳）
 * - 已认证 -> 渲染子组件 / Outlet
 */
export default function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, initialized } = useAuthStore()
  const location = useLocation()

  // 初始化中，显示加载状态
  if (!initialized) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
        }}
      >
        <Spin size="large" tip="验证登录状态..." />
      </div>
    )
  }

  // 未认证，跳转登录
  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  // 已认证，渲染子组件或嵌套路由 Outlet
  return <>{children || <Outlet />}</>
}
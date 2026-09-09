import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import AuthGuard from '@/router/AuthGuard'
import AppLayout from '@/components/layout/AppLayout'

/* 懒加载页面组件 */
const Login = lazy(() => import('@/pages/Login'))
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const Query = lazy(() => import('@/pages/Query'))
const Attribution = lazy(() => import('@/pages/Attribution'))
const DataSources = lazy(() => import('@/pages/DataSource'))
const SchemaManager = lazy(() => import('@/pages/SchemaManager'))
const Settings = lazy(() => import('@/pages/Settings'))

/**
 * 懒加载时的加载占位
 */
function LazyLoad({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
          <Spin size="large" />
        </div>
      }
    >
      {children}
    </Suspense>
  )
}

/**
 * 应用路由定义
 *
 * /              -> 重定向到 /dashboard
 * /login         -> 登录页（无需认证）
 * 其他页面       -> 放在 AppLayout 内，由 AuthGuard 守卫
 */
export default function AppRouter() {
  return (
    <Routes>
      {/* 根路径重定向 */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />

      {/* 公开路由 */}
      <Route path="/login" element={<LazyLoad><Login /></LazyLoad>} />

      {/* 需要认证的路由 */}
      <Route
        element={
          <AuthGuard>
            <AppLayout />
          </AuthGuard>
        }
      >
        <Route path="/dashboard" element={<LazyLoad><Dashboard /></LazyLoad>} />
        <Route path="/query" element={<LazyLoad><Query /></LazyLoad>} />
        <Route path="/attribution" element={<LazyLoad><Attribution /></LazyLoad>} />
        <Route path="/datasources" element={<LazyLoad><DataSources /></LazyLoad>} />
        <Route path="/schemas" element={<LazyLoad><SchemaManager /></LazyLoad>} />
        <Route path="/settings" element={<LazyLoad><Settings /></LazyLoad>} />
      </Route>

      {/* 404 兜底 */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
import { useEffect } from 'react'
import { ConfigProvider } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { BrowserRouter } from 'react-router-dom'
import AppRouter from '@/router'
import { useAuthStore } from '@/stores/authStore'

/**
 * 根组件
 * 提供 Ant Design 中文国际化、路由上下文
 */
function App() {
  useEffect(() => {
    useAuthStore.getState().initAuth()
  }, [])

  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    </ConfigProvider>
  )
}

export default App
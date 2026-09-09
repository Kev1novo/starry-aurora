import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { message } from 'antd'
import { useAuthStore } from '@/stores/authStore'

/**
 * Axios 实例，统一配置 baseURL、请求/响应拦截
 */
const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * 请求拦截器：自动附加 Authorization header
 */
client.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const { token } = useAuthStore.getState()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

/**
 * 响应拦截器：统一错误处理
 *
 * - 401 -> 尝试刷新 token，失败则跳转登录
 * - 其他错误 -> 弹出错误提示
 */
client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const status = error.response?.status

    if (status === 401) {
      // 尝试刷新 token
      const { refreshToken: storedRefreshToken, setToken, setRefreshToken, logout } = useAuthStore.getState()

      if (storedRefreshToken) {
        try {
          const res = await axios.post('/api/v1/auth/refresh', { refresh_token: storedRefreshToken })
          const data = res.data.data || res.data
          const newToken = data.access_token
          const newRefreshToken = data.refresh_token
          setToken(newToken)
          if (newRefreshToken) setRefreshToken(newRefreshToken)

          // 重试原始请求
          if (error.config) {
            error.config.headers.Authorization = `Bearer ${newToken}`
            return client(error.config)
          }
        } catch {
          // 刷新失败，清除状态并跳转登录
          logout()
          window.location.href = '/login'
        }
      } else {
        logout()
        window.location.href = '/login'
      }
    } else {
      // 提取后端错误信息
      const errorMsg =
        (error.response?.data as { message?: string })?.message ||
        error.message ||
        '请求失败'

      message.error(errorMsg)
    }

    return Promise.reject(error)
  },
)

export default client
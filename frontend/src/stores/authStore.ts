import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { LoginParams, RegisterParams } from '@/api/auth'
import * as authApi from '@/api/auth'

/** 用户信息 */
export interface UserInfo {
  id: number
  username: string
  email: string
  avatar?: string
}

/** 认证状态 */
interface AuthState {
  token: string | null
  refreshToken: string | null
  user: UserInfo | null
  /** 是否正在请求 */
  loading: boolean
  /** 是否已完成初始化（检查 token 有效性） */
  initialized: boolean

  /** 登录 */
  login: (params: LoginParams) => Promise<void>
  /** 注册 */
  register: (params: RegisterParams) => Promise<void>
  /** 设置 token */
  setToken: (token: string) => void
  /** 设置 refreshToken */
  setRefreshToken: (token: string) => void
  /** 退出登录 */
  logout: () => void
  /** 从 /users/me 获取当前用户信息 */
  fetchUser: () => Promise<void>
  /** 应用启动时初始化认证状态 */
  initAuth: () => Promise<void>
  /** 是否已通过认证（有 token 且用户信息已加载） */
  isAuthenticated: () => boolean
}

/**
 * 认证状态管理
 *
 * 使用 zustand/persist 中间件将 token 和用户信息持久化到 localStorage
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      loading: false,
      initialized: false,

      login: async (params: LoginParams) => {
        set({ loading: true });
        try {
          const apiRes = await authApi.login(params.username, params.password);
          const body = (apiRes as any).data || apiRes;
          set({
            token: body.access_token,
            refreshToken: body.refresh_token,
            user: body.user || null,
            loading: false,
            initialized: true,
          });
        } catch (error) {
          set({ loading: false });
          throw error;
        }
      },

      register: async (params: RegisterParams) => {
        set({ loading: true });
        try {
          const apiRes = await authApi.register(params.username, params.email, params.password);
          const body = (apiRes as any).data || apiRes;
          set({
            token: body.access_token,
            refreshToken: body.refresh_token,
            user: body.user || null,
            loading: false,
          });
        } catch (error) {
          set({ loading: false });
          throw error;
        }
      },

      setToken: (token: string) => set({ token }),
      setRefreshToken: (refreshToken: string) => set({ refreshToken }),

      logout: () => {
        set({ token: null, refreshToken: null, user: null, initialized: false });
      },

      /** 获取当前用户信息 */
      fetchUser: async () => {
        try {
          const res = await authApi.getMe()
          set({ user: res.data || (res as unknown as UserInfo) })
        } catch {
          // 不清除 token——由调用方决定失败处理方式
        }
      },

      /** 应用初始化：如有 token 则校验并获取用户信息 */
      initAuth: async () => {
        const { token, fetchUser } = get()
        if (token) {
          try {
            await fetchUser()
          } catch {
            // fetchUser 失败（如 token 过期）不清除状态，让页面显示 token 过期前的内容
            // 后续 API 调用时 axos 拦截器会负责刷新 token 或跳转登录
          }
        }
        set({ initialized: true })
      },

      /** 判断是否已认证 */
      isAuthenticated: () => {
        const { token } = get()
        return !!token
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
    }
  )
)
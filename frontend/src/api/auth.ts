import client from '@/api/client'
import type { ApiResponse } from '@/types/common'

/** 登录请求参数 */
export interface LoginParams {
  username: string
  password: string
}

/** 注册请求参数 */
export interface RegisterParams {
  username: string
  email: string
  password: string
}

/** 认证响应数据 */
export interface AuthResult {
  access_token: string
  refresh_token: string
  token_type?: string
  user: {
    id: number
    username: string
    email: string
    avatar?: string
  }
}

/**
 * 登录
 * @param username 用户名
 * @param password 密码
 */
export async function login(username: string, password: string) {
  const res = await client.post<ApiResponse<AuthResult>>('/auth/login', { username, password })
  return res.data
}

/**
 * 注册
 * @param username 用户名
 * @param email 邮箱
 * @param password 密码
 */
export async function register(username: string, email: string, password: string) {
  const res = await client.post<ApiResponse<AuthResult>>('/auth/register', { username, email, password })
  return res.data
}

/**
 * 刷新 token
 * @param refreshToken 刷新令牌
 */
export async function refreshToken(refreshToken: string) {
  const res = await client.post<ApiResponse<{ access_token: string; refresh_token: string }>>('/auth/refresh', { refresh_token: refreshToken })
  return res.data
}

/**
 * 退出登录
 */
export async function logout() {
  const res = await client.post<ApiResponse<null>>('/auth/logout')
  return res.data
}

/**
 * 获取当前登录用户信息
 */
export async function getMe() {
  const res = await client.get<ApiResponse<AuthResult['user']>>('/users/me')
  return res.data
}
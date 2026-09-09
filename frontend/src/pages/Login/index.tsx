import { useState } from 'react'
import { Form, Input, Button, Card, Typography, message, Checkbox } from 'antd'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

const { Title, Text } = Typography

/** 登录表单字段 */
interface LoginFormValues {
  username: string
  password: string
  remember?: boolean
}

/** 注册表单字段 */
interface RegisterFormValues {
  username: string
  email: string
  password: string
  confirmPassword: string
}

/**
 * 登录 / 注册页面
 *
 * 支持切换登录和注册模式
 * - 登录：用户名 + 密码 + 记住我
 * - 注册：用户名 + 邮箱 + 密码 + 确认密码
 */
export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const [isRegister, setIsRegister] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { login, register } = useAuthStore()

  /** 来源路径（登录后回跳） */
  const from = (location.state as { from?: string })?.from || '/dashboard'

  /** 切换登录/注册模式 */
  const toggleMode = () => {
    setIsRegister((prev) => !prev)
  }

  /** 登录表单提交 */
  const handleLogin = async (values: LoginFormValues) => {
    setLoading(true)
    try {
      await login({ username: values.username, password: values.password })
      message.success('登录成功')
      navigate(from, { replace: true })
    } catch {
      // 错误已由请求拦截器处理
    } finally {
      setLoading(false)
    }
  }

  /** 注册表单提交 */
  const handleRegister = async (values: RegisterFormValues) => {
    setLoading(true)
    try {
      await register({
        username: values.username,
        email: values.email,
        password: values.password,
      })
      message.success('注册成功，请登录')
      setIsRegister(false)
    } catch {
      // 错误已由请求拦截器处理
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#f0f2f5',
      }}
    >
      <Card
        style={{
          width: 420,
          boxShadow: '0 4px 24px rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <Title level={3} style={{ marginBottom: 4 }}>智数归因平台</Title>
          <Text type="secondary">
            {isRegister ? '创建新账户' : '请登录以继续'}
          </Text>
        </div>

        {isRegister ? (
          /* 注册表单 */
          <Form
            name="register"
            size="large"
            onFinish={handleRegister}
            autoComplete="off"
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input prefix={<UserOutlined />} placeholder="用户名" />
            </Form.Item>

            <Form.Item
              name="email"
              rules={[
                { required: true, message: '请输入邮箱' },
                { type: 'email', message: '请输入有效的邮箱地址' },
              ]}
            >
              <Input prefix={<MailOutlined />} placeholder="邮箱" />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[
                { required: true, message: '请输入密码' },
                { min: 6, message: '密码至少 6 个字符' },
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>

            <Form.Item
              name="confirmPassword"
              dependencies={['password']}
              rules={[
                { required: true, message: '请确认密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'))
                  },
                }),
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="确认密码" />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>
                注册
              </Button>
            </Form.Item>

            <div style={{ textAlign: 'center' }}>
              <Text>已有账户？</Text>
              <Button type="link" onClick={toggleMode} style={{ padding: '0 4px' }}>
                立即登录
              </Button>
            </div>
          </Form>
        ) : (
          /* 登录表单 */
          <Form
            name="login"
            size="large"
            onFinish={handleLogin}
            autoComplete="off"
            initialValues={{ remember: true }}
          >
            <Form.Item
              name="username"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input prefix={<UserOutlined />} placeholder="用户名" />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: '请输入密码' }]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="密码" />
            </Form.Item>

            <Form.Item>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Form.Item name="remember" valuePropName="checked" noStyle>
                  <Checkbox>记住我</Checkbox>
                </Form.Item>
              </div>
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>
                登录
              </Button>
            </Form.Item>

            <div style={{ textAlign: 'center' }}>
              <Text>还没有账户？</Text>
              <Button type="link" onClick={toggleMode} style={{ padding: '0 4px' }}>
                立即注册
              </Button>
            </div>
          </Form>
        )}
      </Card>
    </div>
  )
}
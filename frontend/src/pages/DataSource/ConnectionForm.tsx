import { useState } from 'react'
import { Form, Input, Select, Button, Row, Col, Alert, Space } from 'antd'
import { ApiOutlined } from '@ant-design/icons'
import type { DataSourceType, CreateDataSourceParams, TestConnectionResult } from '@/types/datasource'
import { testConnectionRaw } from '@/api/datasources'

const { Item } = Form
const { Option } = Select

/** 数据源类型选项 */
const DS_TYPE_OPTIONS: { label: string; value: DataSourceType; defaultPort: number }[] = [
  { label: 'MySQL', value: 'mysql', defaultPort: 3306 },
  { label: 'PostgreSQL', value: 'postgresql', defaultPort: 5432 },
  { label: 'ClickHouse', value: 'clickhouse', defaultPort: 8123 },
]

/** 默认端口映射 */
const DEFAULT_PORTS: Record<DataSourceType, number> = {
  mysql: 3306,
  postgresql: 5432,
  clickhouse: 8123,
}

export interface ConnectionFormProps {
  /** 初始值（编辑时传入） */
  initialValues?: Partial<CreateDataSourceParams>
  /** 提交回调 */
  onSubmit: (values: CreateDataSourceParams) => Promise<void>
  /** 取消回调 */
  onCancel: () => void
  /** 提交中 */
  submitting?: boolean
  /** 表单模式 */
  mode?: 'create' | 'edit'
}

/**
 * ConnectionForm — 数据源连接表单
 *
 * 支持创建和编辑两种模式，内置类型切换时自动更新默认端口
 */
export default function ConnectionForm({
  initialValues,
  onSubmit,
  onCancel,
  submitting = false,
  mode = 'create',
}: ConnectionFormProps) {
  const [form] = Form.useForm<CreateDataSourceParams>()
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<TestConnectionResult | null>(null)

  /** 数据源类型变化时自动填充默认端口 */
  const handleTypeChange = (value: DataSourceType) => {
    form.setFieldsValue({ port: DEFAULT_PORTS[value] })
    setTestResult(null)
  }

  /** 测试连接 */
  const handleTestConnection = async () => {
    try {
      const values = await form.validateFields()
      setTesting(true)
      setTestResult(null)
      const res = await testConnectionRaw(values)
      setTestResult(res.data)
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'errorFields' in err) {
        // 表单校验未通过，不处理
        return
      }
      setTestResult({ success: false, latency_ms: 0, message: '请求失败' })
    } finally {
      setTesting(false)
    }
  }

  /** 提交表单 */
  const handleFinish = async (values: CreateDataSourceParams) => {
    await onSubmit(values)
  }

  return (
    <Form
      form={form}
      layout="vertical"
      initialValues={initialValues ?? { type: 'mysql', port: 3306 }}
      onFinish={handleFinish}
    >
      <Row gutter={16}>
        <Col span={12}>
          <Item
            label="数据源名称"
            name="name"
            rules={[{ required: true, message: '请输入数据源名称' }]}
          >
            <Input placeholder="例如：生产数据库" maxLength={64} />
          </Item>
        </Col>
        <Col span={12}>
          <Item
            label="数据库类型"
            name="type"
            rules={[{ required: true, message: '请选择数据库类型' }]}
          >
            <Select onChange={handleTypeChange}>
              {DS_TYPE_OPTIONS.map((opt) => (
                <Option key={opt.value} value={opt.value}>
                  {opt.label}
                </Option>
              ))}
            </Select>
          </Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={8}>
          <Item
            label="主机地址"
            name="host"
            rules={[{ required: true, message: '请输入主机地址' }]}
          >
            <Input placeholder="localhost 或 IP" />
          </Item>
        </Col>
        <Col span={4}>
          <Item label="端口" name="port" rules={[{ required: true, message: '请输入端口' }]}>
            <Input type="number" />
          </Item>
        </Col>
        <Col span={12}>
          <Item
            label="数据库名"
            name="database_name"
            rules={[{ required: true, message: '请输入数据库名' }]}
          >
            <Input placeholder="数据库名称" />
          </Item>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="数据库用户名" />
          </Item>
        </Col>
        <Col span={12}>
          <Item
            label="密码"
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="数据库密码" />
          </Item>
        </Col>
      </Row>

      {/* 测试连接结果 */}
      {testResult && (
        <Alert
          type={testResult.success ? 'success' : 'error'}
          showIcon
          message={
            testResult.success
              ? `连接成功，延迟 ${testResult.latency_ms}ms`
              : testResult.message || '连接失败'
          }
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setTestResult(null)}
        />
      )}

      {/* 底部操作按钮 */}
      <Space>
        <Button onClick={handleTestConnection} loading={testing} icon={<ApiOutlined />}>
          测试连接
        </Button>
        <Button type="primary" htmlType="submit" loading={submitting}>
          {mode === 'create' ? '创建' : '保存'}
        </Button>
        <Button onClick={onCancel}>取消</Button>
      </Space>
    </Form>
  )
}
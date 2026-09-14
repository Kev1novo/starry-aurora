import { useState } from 'react'
import { Typography, Button, Table, Tag, Drawer, Popconfirm, Space, Spin, Empty, message } from 'antd'
import {
  PlusOutlined,
  ApiOutlined,
  SyncOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { DataSource, CreateDataSourceParams, DataSourceDetail, TestConnectionResult } from '@/types/datasource'
import { useDatasources } from '@/hooks/useDatasources'
import { createDataSource, updateDataSource, getDataSource, testConnection as testDsConnection } from '@/api/datasources'
import ConnectionForm from './ConnectionForm'

const { Title, Paragraph } = Typography

/** 数据源类型 → 中文映射 */
const DS_TYPE_LABEL: Record<string, string> = {
  mysql: 'MySQL',
  postgresql: 'PostgreSQL',
  clickhouse: 'ClickHouse',
}

/** 连接状态颜色映射 */
const STATUS_COLOR: Record<string, string> = {
  connected: 'success',
  disconnected: 'default',
  error: 'error',
}

/** 连接状态中文映射 */
const STATUS_LABEL: Record<string, string> = {
  connected: '已连接',
  disconnected: '未连接',
  error: '异常',
}

/**
 * 数据源管理页面
 *
 * 支持数据源列表展示、创建、编辑、删除、测试连接、同步 Schema
 */
export default function DataSourcePage() {
  const { datasources, loading, total, page, pageSize, changePage, refresh, remove, doSyncSchema } =
    useDatasources()

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editingValues, setEditingValues] = useState<CreateDataSourceParams | undefined>(undefined)
  const [submitting, setSubmitting] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [syncingId, setSyncingId] = useState<number | null>(null)

  /** 打开新建抽屉 */
  const handleOpenCreate = () => {
    setEditingId(null)
    setEditingValues(undefined)
    setDrawerOpen(true)
  }

  /** 打开编辑抽屉（先获取详情） */
  const handleOpenEdit = async (record: DataSource) => {
    setEditingId(record.id)
    setEditingValues(undefined)
    setDrawerOpen(true)
    try {
      const res = await getDataSource(record.id)
      const detail = res.data as DataSourceDetail
      setEditingValues({
        name: detail.name,
        type: detail.type as 'mysql' | 'postgresql' | 'clickhouse',
        host: detail.host,
        port: detail.port,
        database_name: detail.database_name,
        username: detail.username,
        password: '',
      })
    } catch {
      message.error('获取数据源详情失败')
    }
  }

  /** 关闭抽屉 */
  const handleCloseDrawer = () => {
    setDrawerOpen(false)
    setEditingId(null)
    setEditingValues(undefined)
  }

  /** 提交创建/更新 */
  const handleSubmit = async (values: CreateDataSourceParams) => {
    setSubmitting(true)
    try {
      if (editingId !== null) {
        const patch: Record<string, unknown> = { ...values }
        if (!patch.password) delete patch.password
        await updateDataSource(editingId, patch)
      } else {
        await createDataSource(values)
      }
      handleCloseDrawer()
      refresh()
    } finally {
      setSubmitting(false)
    }
  }

  /** 测试连接（已保存的数据源） */
  const handleTestConnection = async (id: number) => {
    setTestingId(id)
    try {
      const res = await testDsConnection(id)
      const result = res.data as TestConnectionResult
      if (result.success) {
        message.success(`连接成功，延迟 ${result.latency_ms}ms`)
      } else {
        message.error(result.message || '连接失败')
      }
      refresh()
    } catch {
      // 错误已在拦截器中统一处理
    } finally {
      setTestingId(null)
    }
  }

  /** 同步 Schema */
  const handleSyncSchema = async (id: number) => {
    setSyncingId(id)
    try {
      await doSyncSchema(id)
    } finally {
      setSyncingId(null)
    }
  }

  /** 表格列定义 */
  const columns: ColumnsType<DataSource> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 180,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type: string) => DS_TYPE_LABEL[type] ?? type,
    },
    {
      title: '主机',
      dataIndex: 'host',
      key: 'host',
      width: 150,
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
      width: 80,
    },
    {
      title: '数据库',
      dataIndex: 'database_name',
      key: 'database_name',
      width: 140,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={STATUS_COLOR[status] ?? 'default'}>{STATUS_LABEL[status] ?? status}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 260,
      render: (_: unknown, record: DataSource) => (
        <Space>
          <Button
            size="small"
            icon={<ApiOutlined />}
            loading={testingId === record.id}
            onClick={() => handleTestConnection(record.id)}
          >
            测试
          </Button>
          <Button
            size="small"
            icon={<SyncOutlined />}
            loading={syncingId === record.id}
            onClick={() => handleSyncSchema(record.id)}
          >
            同步
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleOpenEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确认删除"
            description={`确定要删除数据源「${record.name}」吗？`}
            onConfirm={() => remove(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Title level={2}>数据源管理</Title>
          <Paragraph type="secondary">连接与管理各类数据源，支持实时同步</Paragraph>
        </div>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={refresh}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
            新增数据源
          </Button>
        </Space>
      </div>

      {/* 数据源表格 */}
      <Spin spinning={loading}>
        {datasources.length > 0 ? (
          <Table<DataSource>
            rowKey="id"
            columns={columns}
            dataSource={datasources}
            pagination={{
              current: page,
              pageSize,
              total,
              showSizeChanger: true,
              showTotal: (t: number) => `共 ${t} 条`,
              onChange: changePage,
            }}
            scroll={{ x: 1100 }}
          />
        ) : (
          !loading && (
            <Empty description="暂无数据源，点击上方「新增数据源」开始连接" />
          )
        )}
      </Spin>

      {/* 新增/编辑抽屉 */}
      <Drawer
        title={editingId !== null ? '编辑数据源' : '新增数据源'}
        open={drawerOpen}
        onClose={handleCloseDrawer}
        width={560}
        destroyOnClose
      >
        <ConnectionForm
          mode={editingId !== null ? 'edit' : 'create'}
          initialValues={editingValues}
          onSubmit={handleSubmit}
          onCancel={handleCloseDrawer}
          submitting={submitting}
        />
      </Drawer>
    </div>
  )
}
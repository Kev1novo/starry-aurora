import { Card, Form, Select, Input, DatePicker, Button, message } from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

interface ParamConfigProps {
  datasources: Array<{ id: number; name: string }>
  onRun: (params: {
    datasource_id: number
    touchpoint_table: string
    conversion_table: string
    time_range?: { start: string; end: string }
    model_params?: Record<string, any>
  }) => void
  loading?: boolean
}

/**
 * ParamConfig — 归因分析参数配置表单
 *
 * 提供数据源选择、触点表名、转化表名、时间范围等参数输入。
 * 必填字段校验通过后启用"运行分析"按钮。
 */
export default function ParamConfig({ datasources, onRun, loading }: ParamConfigProps) {
  const [form] = Form.useForm()

  /** 检查必填字段是否已填写 */
  const checkRequired = async () => {
    try {
      await form.validateFields(['datasource_id', 'touchpoint_table', 'conversion_table'])
      return true
    } catch {
      return false
    }
  }

  const handleRun = async () => {
    const ok = await checkRequired()
    if (!ok) {
      message.warning('请填写所有必填字段')
      return
    }

    const values = form.getFieldsValue()
    const params: Parameters<typeof onRun>[0] = {
      datasource_id: values.datasource_id,
      touchpoint_table: values.touchpoint_table,
      conversion_table: values.conversion_table,
    }

    // 处理时间范围
    if (values.time_range && values.time_range[0] && values.time_range[1]) {
      params.time_range = {
        start: values.time_range[0].format('YYYY-MM-DD'),
        end: values.time_range[1].format('YYYY-MM-DD'),
      }
    }

    onRun(params)
  }

  return (
    <Card title="分析参数配置" size="small">
      <Form form={form} layout="vertical" size="small">
        <Form.Item
          label="数据源"
          name="datasource_id"
          rules={[{ required: true, message: '请选择数据源' }]}
        >
          <Select
            placeholder="请选择数据源"
            allowClear
            showSearch
            optionFilterProp="label"
            notFoundContent="暂无数据源"
          >
            {(datasources || []).map((ds) => (
              <Select.Option key={ds.id} value={ds.id} label={ds.name}>
                {ds.name}
              </Select.Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          label="触点表名"
          name="touchpoint_table"
          rules={[{ required: true, message: '请输入触点表名' }]}
          tooltip="存储用户触点/事件数据的表名"
        >
          <Input placeholder="例如：touchpoints" allowClear />
        </Form.Item>

        <Form.Item
          label="转化表名"
          name="conversion_table"
          rules={[{ required: true, message: '请输入转化表名' }]}
          tooltip="存储转化/成交数据的表名"
        >
          <Input placeholder="例如：conversions" allowClear />
        </Form.Item>

        <Form.Item label="时间范围" name="time_range">
          <RangePicker
            style={{ width: '100%' }}
            placeholder={['开始日期', '结束日期']}
            disabledDate={(current) => current && current.isAfter(dayjs().endOf('day'))}
          />
        </Form.Item>

        <Form.Item style={{ marginBottom: 0 }}>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleRun}
            loading={loading}
            block
          >
            {loading ? '分析中...' : '运行分析'}
          </Button>
        </Form.Item>
      </Form>
    </Card>
  )
}
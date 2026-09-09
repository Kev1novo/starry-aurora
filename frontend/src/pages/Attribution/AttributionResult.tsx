import { useMemo } from 'react'
import { Row, Col, Card, Statistic, Table, Typography, Skeleton, Empty, Tag } from 'antd'
import {
  NumberOutlined,
  DollarOutlined,
  RiseOutlined,
} from '@ant-design/icons'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// 注册 ECharts 组件（按需加载）
echarts.use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const { Text } = Typography

export interface TouchpointItem {
  channel: string
  touch_count: number
  contribution: number
  contribution_pct: number
}

interface AttributionResultProps {
  result: {
    model?: string
    total_conversions?: number
    total_revenue?: number
    touchpoints?: TouchpointItem[]
    chart_data?: any
    insights?: string[]
  } | null
  loading?: boolean
}

/** 模型中文名称映射 */
const MODEL_LABELS: Record<string, string> = {
  first_touch: '首次触点',
  last_touch: '末次触点',
  linear: '线性归因',
  time_decay: '时间衰减',
  position_decay: '位置衰减（U型）',
  data_driven: '数据驱动（Shapley）',
}

/**
 * AttributionResult — 归因分析结果展示
 *
 * 包含摘要统计、触点贡献表格、贡献度柱状图、洞察建议。
 */
export default function AttributionResult({ result, loading }: AttributionResultProps) {
  const barChartOption = useMemo(() => {
    if (!result?.touchpoints || result.touchpoints.length === 0) return null

    const sorted = [...result.touchpoints].sort(
      (a, b) => b.contribution_pct - a.contribution_pct,
    )

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const p = params[0]
          const item = sorted[p.dataIndex]
          return (
            `${item.channel}<br/>` +
            `贡献值: ${item.contribution.toFixed(2)}<br/>` +
            `贡献占比: ${(item.contribution_pct * 100).toFixed(1)}%<br/>` +
            `触点次数: ${item.touch_count.toLocaleString()}`
          )
        },
      },
      grid: { left: 20, right: 20, bottom: 30, top: 10, containLabel: true },
      xAxis: {
        type: 'category',
        data: sorted.map((t) => t.channel),
        axisLabel: {
          rotate: sorted.length > 6 ? 35 : 0,
          fontSize: 11,
        },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
        },
      },
      series: [
        {
          type: 'bar',
          data: sorted.map((t) => ({
            value: t.contribution_pct,
            itemStyle: {
              color:
                t.contribution_pct === sorted[0].contribution_pct
                  ? '#1677ff'
                  : '#91caff',
            },
          })),
          barMaxWidth: 48,
          label: {
            show: true,
            position: 'top',
            formatter: (p: any) => `${(p.value * 100).toFixed(1)}%`,
            fontSize: 11,
          },
        },
      ],
    }
  }, [result])

  /** 表格列定义 */
  const columns = [
    {
      title: '渠道',
      dataIndex: 'channel',
      key: 'channel',
      width: 140,
      render: (v: string) => <Text strong>{v}</Text>,
    },
    {
      title: '触点次数',
      dataIndex: 'touch_count',
      key: 'touch_count',
      width: 110,
      align: 'right' as const,
      render: (v: number) => v?.toLocaleString() || '-',
      sorter: (a: TouchpointItem, b: TouchpointItem) => a.touch_count - b.touch_count,
    },
    {
      title: '贡献值',
      dataIndex: 'contribution',
      key: 'contribution',
      width: 120,
      align: 'right' as const,
      render: (v: number) => (v != null ? v.toFixed(2) : '-'),
      sorter: (a: TouchpointItem, b: TouchpointItem) => a.contribution - b.contribution,
    },
    {
      title: '贡献占比',
      dataIndex: 'contribution_pct',
      key: 'contribution_pct',
      width: 120,
      align: 'right' as const,
      render: (v: number) =>
        v != null ? (
          <Tag color={v >= 0.3 ? 'blue' : v >= 0.15 ? 'cyan' : 'default'}>
            {(v * 100).toFixed(1)}%
          </Tag>
        ) : (
          '-'
        ),
      sorter: (a: TouchpointItem, b: TouchpointItem) => a.contribution_pct - b.contribution_pct,
      defaultSortOrder: 'descend' as const,
    },
  ]

  // 加载态
  if (loading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 6 }} />
      </Card>
    )
  }

  // 空态
  if (!result) {
    return (
      <Card>
        <Empty description="请选择模型并配置参数后运行分析" />
      </Card>
    )
  }

  const modelLabel = MODEL_LABELS[result.model || ''] || result.model || ''

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* 模型标识 */}
      {modelLabel && (
        <div>
          <Tag color="blue" style={{ fontSize: 14, padding: '2px 12px' }}>
            当前模型：{modelLabel}
          </Tag>
        </div>
      )}

      {/* 摘要统计卡片 */}
      <Row gutter={16}>
        <Col span={8}>
          <Card size="small" hoverable>
            <Statistic
              title="总转化数"
              value={result.total_conversions ?? '-'}
              prefix={<NumberOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" hoverable>
            <Statistic
              title="总收入"
              value={result.total_revenue ?? '-'}
              precision={2}
              prefix={<DollarOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" hoverable>
            <Statistic
              title="触及渠道数"
              value={result.touchpoints?.length ?? result.touchpoints?.length ?? '-'}
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 贡献柱状图 */}
      {barChartOption && (
        <Card title="渠道贡献占比" size="small">
          <ReactEChartsCore
            echarts={echarts}
            option={barChartOption}
            style={{ height: 320 }}
            notMerge
            lazyUpdate
          />
        </Card>
      )}

      {/* 触点贡献表格 */}
      {result.touchpoints && result.touchpoints.length > 0 && (
        <Card title="触点贡献明细" size="small">
          <Table
            dataSource={result.touchpoints}
            columns={columns}
            rowKey="channel"
            pagination={false}
            size="small"
            locale={{ emptyText: '暂无触点数据' }}
          />
        </Card>
      )}

      {/* 洞察建议 */}
      {result.insights && result.insights.length > 0 && (
        <Card title="分析洞察" size="small">
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {result.insights.map((insight, idx) => (
              <li key={idx} style={{ marginBottom: 8, lineHeight: 1.6 }}>
                <Text>{insight}</Text>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  )
}
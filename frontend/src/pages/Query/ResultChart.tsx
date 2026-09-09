import { useMemo, useEffect, useState } from 'react'
import { Card, Empty, Segmented } from 'antd'
import { BarChartOutlined, LineChartOutlined, PieChartOutlined } from '@ant-design/icons'
import { BarChart, LineChart, PieChart } from '@/components/charts'

export interface ChartSuggestion {
  chartType: 'bar' | 'line' | 'pie'
  title?: string
  xField?: string
  yField?: string
}

interface ResultChartProps {
  chartSuggestion?: ChartSuggestion | null
  data: any[] | null
}

/** 图表类型切换选项 */
const CHART_TYPE_OPTIONS = [
  { label: '柱状图', value: 'bar', icon: <BarChartOutlined /> },
  { label: '折线图', value: 'line', icon: <LineChartOutlined /> },
  { label: '饼图', value: 'pie', icon: <PieChartOutlined /> },
]

/**
 * 查询结果图表展示
 *
 * 将表格数据按 chartSuggestion 的 xField/yField 映射为图表组件所需格式
 * 支持在 bar / line / pie 间手动切换
 */
export default function ResultChart({ chartSuggestion, data }: ResultChartProps) {
  const [chartType, setChartType] = useState<string | undefined>()

  /** 当前实际使用的图表类型（手动切换优先） */
  const activeType = chartType || chartSuggestion?.chartType

  /** 将行数据转为 {name, value}[] 格式 */
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return []

    const xField = chartSuggestion?.xField
    if (!xField) return []

    const yField =
      chartSuggestion?.yField ||
      Object.keys(data[0]).find((k) => typeof data[0][k] === 'number') ||
      ''

    return data.map((row) => ({
      name: String(row[xField] ?? ''),
      value: Number(row[yField] ?? 0),
    }))
  }, [data, chartSuggestion])

  /** 当推荐图表类型变化时同步（允许手动覆盖） */
  useEffect(() => {
    if (chartSuggestion?.chartType) {
      setChartType(undefined)
    }
  }, [chartSuggestion?.chartType])

  if (!chartSuggestion || !data || data.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description="暂无图表数据"
        style={{ padding: 32 }}
      />
    )
  }

  const renderChart = () => {
    switch (activeType) {
      case 'bar':
        return (
          <BarChart
            data={chartData}
            title={chartSuggestion.title}
            xAxisLabel={chartSuggestion.xField}
            yAxisLabel={chartSuggestion.yField}
            height={350}
          />
        )
      case 'line':
        return (
          <LineChart
            data={chartData}
            title={chartSuggestion.title}
            xAxisLabel={chartSuggestion.xField}
            yAxisLabel={chartSuggestion.yField}
            height={350}
          />
        )
      case 'pie':
        return (
          <PieChart
            data={chartData}
            title={chartSuggestion.title}
            height={350}
          />
        )
      default:
        return null
    }
  }

  return (
    <Card
      size="small"
      title={
        <span style={{ fontSize: 13 }}>
          {chartSuggestion.title || '数据可视化'}
        </span>
      }
      extra={
        <Segmented
          size="small"
          value={activeType}
          options={CHART_TYPE_OPTIONS}
          onChange={(val) => setChartType(val as string)}
        />
      }
    >
      {renderChart()}
    </Card>
  )
}
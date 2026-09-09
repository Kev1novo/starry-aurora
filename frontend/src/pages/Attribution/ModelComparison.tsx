import { useMemo, useState } from 'react'
import { Card, Checkbox, Tag, Empty, Typography, Space } from 'antd'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const { Text } = Typography

/** 模型中文名称映射 */
const MODEL_LABELS: Record<string, string> = {
  first_touch: '首次触点',
  last_touch: '末次触点',
  linear: '线性归因',
  time_decay: '时间衰减',
  position_decay: '位置衰减（U型）',
  data_driven: '数据驱动（Shapley）',
}

/** 调色板 */
const COLOR_PALETTE = [
  '#1677ff', '#52c41a', '#faad14', '#ff4d4f',
  '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16',
]

interface ModelResult {
  model: string
  touchpoints: Array<{ channel: string; contribution_pct: number }>
}

interface ModelComparisonProps {
  results: ModelResult[]
}

/**
 * ModelComparison — 多模型归因结果对比
 *
 * 支持勾选多个模型，以分组柱状图展示各渠道在所选模型下的贡献占比差异。
 */
export default function ModelComparison({ results }: ModelComparisonProps) {
  // 默认全选
  const defaultChecked = results.map((r) => r.model)
  const [checkedModels, setCheckedModels] = useState<string[]>(defaultChecked)

  /** 所有渠道（去重） */
  const allChannels = useMemo(() => {
    const channelSet = new Set<string>()
    for (const r of results) {
      for (const t of r.touchpoints || []) {
        channelSet.add(t.channel)
      }
    }
    return Array.from(channelSet)
  }, [results])

  /** 分组柱状图配置 */
  const barOption = useMemo(() => {
    if (results.length === 0 || allChannels.length === 0) return null

    const selectedResults = results.filter((r) => checkedModels.includes(r.model))
    if (selectedResults.length === 0) return null

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      legend: {
        type: 'scroll',
        top: 0,
        data: selectedResults.map((r) => MODEL_LABELS[r.model] || r.model),
      },
      grid: { left: 20, right: 20, bottom: 30, top: 40, containLabel: true },
      xAxis: {
        type: 'category',
        data: allChannels,
        axisLabel: {
          rotate: allChannels.length > 6 ? 35 : 0,
          fontSize: 11,
        },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (v: number) => `${(v * 100).toFixed(0)}%`,
        },
      },
      series: selectedResults.map((r, idx) => {
        // 建立渠道 → contribution_pct 的查找表
        const channelMap = new Map<string, number>()
        for (const t of r.touchpoints || []) {
          channelMap.set(t.channel, t.contribution_pct)
        }

        return {
          name: MODEL_LABELS[r.model] || r.model,
          type: 'bar',
          barMaxWidth: 32,
          data: allChannels.map((ch) => channelMap.get(ch) ?? 0),
          itemStyle: { color: COLOR_PALETTE[idx % COLOR_PALETTE.length] },
        }
      }),
    }
  }, [results, checkedModels, allChannels])

  if (!results || results.length === 0) {
    return (
      <Card title="模型对比">
        <Empty description="暂无对比数据" />
      </Card>
    )
  }

  return (
    <Card title="模型对比" size="small">
      {/* 模型选择 */}
      <div style={{ marginBottom: 16 }}>
        <Space direction="vertical" size={8}>
          <Text type="secondary">选择要对比的模型：</Text>
          <Checkbox.Group
            value={checkedModels}
            onChange={(values) => setCheckedModels(values as string[])}
          >
            <Space wrap>
              {results.map((r, idx) => (
                <Checkbox key={r.model} value={r.model}>
                  <Tag color={COLOR_PALETTE[idx % COLOR_PALETTE.length]}>
                    {MODEL_LABELS[r.model] || r.model}
                  </Tag>
                </Checkbox>
              ))}
            </Space>
          </Checkbox.Group>
        </Space>
      </div>

      {/* 图表 */}
      {barOption && checkedModels.length > 0 ? (
        <ReactEChartsCore
          echarts={echarts}
          option={barOption}
          style={{ height: 400 }}
          notMerge
          lazyUpdate
        />
      ) : (
        <Empty description="请至少选择一个模型" style={{ padding: '40px 0' }} />
      )}
    </Card>
  )
}
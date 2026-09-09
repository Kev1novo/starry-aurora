import { useMemo } from 'react'
import { Card, Empty, Skeleton } from 'antd'
import ReactEChartsCore from 'echarts-for-react/lib/core'
import * as echarts from 'echarts/core'
import { SankeyChart } from 'echarts/charts'
import {
  TooltipComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([SankeyChart, TooltipComponent, CanvasRenderer])

interface TouchpointFlowProps {
  data: Array<{ channel: string; touch_count: number }> | null
  loading?: boolean
}

/**
 * TouchpointFlow — 用户触点旅程桑基图
 *
 * 将触点数据转换为 start → channel → conversion 的桑基图，
 * 直观展示用户在各渠道间的流转路径。
 */
export default function TouchpointFlow({ data, loading }: TouchpointFlowProps) {
  const sankeyOption = useMemo(() => {
    if (!data || data.length === 0) return null

    const nodes: Array<{ name: string; itemStyle?: { color: string } }> = [
      { name: '用户入口', itemStyle: { color: '#1677ff' } },
      ...data.map((d) => ({ name: d.channel })),
      { name: '完成转化', itemStyle: { color: '#52c41a' } },
    ]

    const links: Array<{ source: string; target: string; value: number }> = [
      // 入口到各渠道
      ...data.map((d) => ({
        source: '用户入口',
        target: d.channel,
        value: d.touch_count,
      })),
      // 各渠道到转化
      ...data.map((d) => ({
        source: d.channel,
        target: '完成转化',
        value: Math.round(d.touch_count * 0.3) || 1, // 模拟转化流向
      })),
    ]

    return {
      tooltip: {
        trigger: 'item',
        triggerOn: 'mousemove',
        formatter: (params: any) => {
          if (params.dataType === 'edge') {
            return `${params.data.source} → ${params.data.target}<br/>流转量: ${params.data.value.toLocaleString()}`
          }
          return `${params.name}<br/>${params.value ? `总量: ${params.value.toLocaleString()}` : ''}`
        },
      },
      series: [
        {
          type: 'sankey',
          layout: 'none',
          layoutIterations: 32,
          emphasis: { focus: 'adjacency' },
          nodeAlign: 'justify',
          nodeWidth: 20,
          nodeGap: 12,
          draggable: true,
          data: nodes,
          links,
          label: {
            fontSize: 12,
            fontWeight: 500,
          },
          lineStyle: {
            color: 'gradient',
            curveness: 0.5,
            opacity: 0.4,
          },
        },
      ],
    }
  }, [data])

  if (loading) {
    return (
      <Card title="触点旅程">
        <Skeleton active paragraph={{ rows: 8 }} />
      </Card>
    )
  }

  if (!data || data.length === 0 || !sankeyOption) {
    return (
      <Card title="触点旅程">
        <Empty description="暂无触点数据" />
      </Card>
    )
  }

  return (
    <Card title="触点旅程" size="small">
      <ReactEChartsCore
        echarts={echarts}
        option={sankeyOption}
        style={{ height: 400 }}
        notMerge
        lazyUpdate
      />
    </Card>
  )
}
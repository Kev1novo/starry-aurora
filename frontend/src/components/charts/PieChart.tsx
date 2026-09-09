import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

interface PieDataItem {
  name: string;
  value: number;
}

interface PieChartProps {
  data: PieDataItem[];
  title?: string;
  height?: number;
  roseType?: boolean;
  showLegend?: boolean;
}

const DEFAULT_COLORS = [
  '#5470c6', '#91cc75', '#fac858', '#ee6666',
  '#73c0de', '#3ba272', '#fc8452', '#9a60b4',
  '#ea7ccc', '#1a7b9a',
];

const PieChart: React.FC<PieChartProps> = ({
  data,
  title,
  height = 400,
  roseType = false,
  showLegend = true,
}) => {
  const option = useMemo(() => {
    const total = data.reduce((sum, item) => sum + item.value, 0);

    return {
      title: title
        ? {
            text: title,
            left: 'center',
            textStyle: { fontSize: 14 },
          }
        : undefined,
      tooltip: {
        trigger: 'item' as const,
        formatter: (params: any) => {
          const percent = total > 0
            ? ((params.value / total) * 100).toFixed(1)
            : '0.0';
          return `${params.name}<br/>数值: ${params.value} (${percent}%)`;
        },
      },
      legend: showLegend
        ? {
            orient: 'vertical' as const,
            right: 10,
            top: title ? 40 : 10,
            type: 'scroll' as const,
          }
        : undefined,
      series: [
        {
          type: 'pie',
          radius: roseType ? ['15%', '55%'] : '55%',
          center: ['40%', '55%'],
          roseType: roseType ? 'area' as const : undefined,
          itemStyle: {
            borderRadius: 6,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: data.length <= 10,
            formatter: '{b}: {d}%',
          },
          emphasis: {
            label: { show: true, fontWeight: 'bold' },
            itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' },
          },
          data,
          color: DEFAULT_COLORS,
        },
      ],
    };
  }, [data, title, roseType, showLegend]);

  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <Empty description="暂无数据" />
      </div>
    );
  }

  return (
    <ReactECharts
      option={option}
      style={{ height, width: '100%' }}
      notMerge
    />
  );
};

export default PieChart;
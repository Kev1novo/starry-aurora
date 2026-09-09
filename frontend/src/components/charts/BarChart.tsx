import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

interface BarDataItem {
  name: string;
  value: number;
}

interface BarChartProps {
  data: BarDataItem[];
  title?: string;
  height?: number;
  xAxisLabel?: string;
  yAxisLabel?: string;
  color?: string;
}

const BarChart: React.FC<BarChartProps> = ({
  data,
  title,
  height = 400,
  xAxisLabel,
  yAxisLabel,
  color = '#5470c6',
}) => {
  const option = useMemo(() => {
    const names = data.map((item) => item.name);
    const values = data.map((item) => item.value);

    return {
      title: title
        ? {
            text: title,
            left: 'center',
            textStyle: { fontSize: 14 },
          }
        : undefined,
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: { type: 'shadow' as const },
        formatter: (params: any) => {
          const p = params[0];
          if (!p) return '';
          return `${p.name}<br/>${yAxisLabel || '值'}: ${p.value}`;
        },
      },
      grid: {
        left: 60,
        right: 30,
        top: title ? 50 : 20,
        bottom: 40,
      },
      xAxis: {
        type: 'category' as const,
        data: names,
        name: xAxisLabel,
        nameLocation: 'center' as const,
        nameGap: 35,
        axisLabel: {
          rotate: names.length > 8 ? 45 : 0,
          interval: 0,
        },
      },
      yAxis: {
        type: 'value' as const,
        name: yAxisLabel,
        nameLocation: 'center' as const,
        nameGap: 50,
      },
      series: [
        {
          type: 'bar',
          data: values,
          itemStyle: {
            color,
            borderRadius: [4, 4, 0, 0],
          },
          barMaxWidth: 60,
        },
      ],
    };
  }, [data, title, xAxisLabel, yAxisLabel, color]);

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

export default BarChart;
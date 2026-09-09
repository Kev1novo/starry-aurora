import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

interface LineDataItem {
  name: string;
  value: number;
}

interface LineChartProps {
  data: LineDataItem[];
  title?: string;
  height?: number;
  smooth?: boolean;
  showArea?: boolean;
  xAxisLabel?: string;
  yAxisLabel?: string;
}

const LineChart: React.FC<LineChartProps> = ({
  data,
  title,
  height = 400,
  smooth = false,
  showArea = false,
  xAxisLabel,
  yAxisLabel,
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
          type: 'line',
          data: values,
          smooth,
          areaStyle: showArea ? { opacity: 0.25 } : undefined,
          lineStyle: { width: 2 },
          symbol: 'circle',
          symbolSize: 6,
          emphasis: {
            focus: 'series' as const,
            itemStyle: { borderWidth: 2 },
          },
        },
      ],
    };
  }, [data, title, smooth, showArea, xAxisLabel, yAxisLabel]);

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

export default LineChart;
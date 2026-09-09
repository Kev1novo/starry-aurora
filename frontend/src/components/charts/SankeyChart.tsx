import React, { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import { Empty } from 'antd';

interface SankeyLink {
  source: string;
  target: string;
  value: number;
}

interface SankeyChartProps {
  links: SankeyLink[];
  title?: string;
  height?: number;
}

const SankeyChart: React.FC<SankeyChartProps> = ({
  links,
  title,
  height = 400,
}) => {
  const option = useMemo(() => {
    const nodeSet = new Set<string>();
    links.forEach((link) => {
      nodeSet.add(link.source);
      nodeSet.add(link.target);
    });

    const nodes = Array.from(nodeSet).map((name) => ({ name }));

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
        triggerOn: 'mousemove' as const,
        formatter: (params: any) => {
          if (params.dataType === 'edge') {
            return `${params.data.source} > ${params.data.target}<br/>流量: ${params.data.value}`;
          }
          return `${params.data.name}`;
        },
      },
      series: [
        {
          type: 'sankey',
          layout: 'none' as const,
          layoutIterations: 32,
          emphasis: {
            focus: 'adjacency' as const,
          },
          nodeAlign: 'left' as const,
          lineStyle: {
            curveness: 0.5,
          },
          label: {
            fontSize: 12,
          },
          data: nodes,
          links,
        },
      ],
    };
  }, [links, title]);

  if (!links || links.length === 0) {
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

export default SankeyChart;
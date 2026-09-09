import React, { ReactNode } from 'react';
import { Empty } from 'antd';

interface EmptyStateProps {
  description?: string;
  action?: ReactNode;
}

const EmptyState: React.FC<EmptyStateProps> = ({
  description = '暂无数据',
  action,
}) => {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '48px 0',
        width: '100%',
      }}
    >
      <Empty
        description={description}
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      >
        {action && <div style={{ marginTop: 16 }}>{action}</div>}
      </Empty>
    </div>
  );
};

export default EmptyState;
import React from 'react';
import { Spin } from 'antd';

interface LoadingProps {
  tip?: string;
  fullscreen?: boolean;
}

const Loading: React.FC<LoadingProps> = ({
  tip = '加载中...',
  fullscreen = false,
}) => {
  if (fullscreen) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: '100vh',
          width: '100%',
        }}
      >
        <Spin size="large" tip={tip} />
      </div>
    );
  }

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
      <Spin tip={tip} />
    </div>
  );
};

export default Loading;
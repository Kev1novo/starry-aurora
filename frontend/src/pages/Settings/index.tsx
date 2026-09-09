import { Typography } from 'antd'

const { Title, Paragraph } = Typography

/**
 * 系统设置页面（占位）
 */
export default function SettingsPage() {
  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={2}>系统设置</Title>
        <Paragraph type="secondary">管理平台配置与个性化设置</Paragraph>
      </div>
    </div>
  )
}
import { Card, Row, Col, Typography, Tag } from 'antd'
import { CheckCircleFilled } from '@ant-design/icons'

const { Text, Paragraph } = Typography

/** 模型中文名称映射 */
const MODEL_LABELS: Record<string, string> = {
  first_touch: '首次触点',
  last_touch: '末次触点',
  linear: '线性归因',
  time_decay: '时间衰减',
  position_decay: '位置衰减（U型）',
  data_driven: '数据驱动（Shapley）',
}

interface ModelSelectorProps {
  models: Array<{ name: string; description: string }>
  selected: string
  onSelect: (name: string) => void
}

/**
 * ModelSelector — 归因模型选择卡片网格
 *
 * 以 Card 网格展示每个归因模型，高亮当前选中的模型。
 */
export default function ModelSelector({ models, selected, onSelect }: ModelSelectorProps) {
  if (!models || models.length === 0) {
    return (
      <Card title="选择归因模型" size="small">
        <Text type="secondary">暂无可用模型</Text>
      </Card>
    )
  }

  return (
    <Card title="选择归因模型" size="small">
      <Row gutter={[12, 12]}>
        {models.map((model) => {
          const isSelected = selected === model.name
          const label = MODEL_LABELS[model.name] || model.name

          return (
            <Col span={24} key={model.name}>
              <Card
                hoverable
                size="small"
                onClick={() => onSelect(model.name)}
                style={{
                  borderColor: isSelected ? '#1677ff' : undefined,
                  background: isSelected ? '#e6f4ff' : undefined,
                  cursor: 'pointer',
                  position: 'relative',
                  transition: 'all 0.2s',
                }}
                bodyStyle={{ padding: '10px 16px' }}
              >
                {isSelected && (
                  <CheckCircleFilled
                    style={{
                      position: 'absolute',
                      top: 6,
                      right: 8,
                      color: '#1677ff',
                      fontSize: 16,
                    }}
                  />
                )}
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Tag color={isSelected ? 'primary' : 'default'}>{label}</Tag>
                  {isSelected && <Tag color="blue">已选</Tag>}
                </div>
                <Paragraph
                  type="secondary"
                  style={{ margin: '4px 0 0', fontSize: 13, lineHeight: 1.5 }}
                >
                  {model.description || '暂无描述'}
                </Paragraph>
              </Card>
            </Col>
          )
        })}
      </Row>
    </Card>
  )
}
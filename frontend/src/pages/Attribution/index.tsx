import { useState, useEffect, useCallback } from 'react'
import { Row, Col, Tabs, message, Typography } from 'antd'
import * as attributionApi from '@/api/attribution'
import * as datasourceApi from '@/api/datasources'
import { useAttributionStore } from '@/stores/attributionStore'
import ModelSelector from './ModelSelector'
import ParamConfig from './ParamConfig'
import AttributionResult from './AttributionResult'
import TouchpointFlow from './TouchpointFlow'
import ModelComparison from './ModelComparison'

const { Title, Paragraph } = Typography

/**
 * AttributionPage — 归因分析主页面
 *
 * 布局：
 *  - 顶部：两列布局，左侧模型选择、右侧参数配置
 *  - 中部：运行分析按钮
 *  - 底部：Tabs 切换（结果 / 触点流 / 模型对比）
 */
export default function AttributionPage() {
  const {
    models,
    selectedModel,
    result,
    isLoading,
    fetchModels,
    setModel,
    setLoading,
    setResult,
    resetResult,
  } = useAttributionStore()

  const [datasources, setDatasources] = useState<Array<{ id: number; name: string }>>([])

  /** 收集所有结果（用于模型对比） */
  const [allResults, setAllResults] = useState<
    Array<{ model: string; touchpoints: Array<{ channel: string; contribution_pct: number }> }>
  >([])

  /** 初始化：获取模型列表和数据源列表 */
  useEffect(() => {
    fetchModels()
    fetchDatasources()
  }, [fetchModels])

  const fetchDatasources = useCallback(async () => {
    try {
      const res = await datasourceApi.getDataSources({ page: 1, page_size: 100 })
      const data = res.data as { items: Array<{ id: number; name: string }> }
      setDatasources(data.items || [])
    } catch {
      // 错误已在拦截器中处理
    }
  }, [])

  /** 执行分析 */
  const handleRun = useCallback(
    async (params: {
      datasource_id: number
      touchpoint_table: string
      conversion_table: string
      time_range?: { start: string; end: string }
      model_params?: Record<string, any>
    }) => {
      if (!selectedModel) {
        message.warning('请先选择归因模型')
        return
      }

      setLoading(true)
      resetResult()

      try {
        const requestData: attributionApi.AttributionRequest = {
          model: selectedModel,
          datasource_id: params.datasource_id,
          touchpoint_table: params.touchpoint_table,
          conversion_table: params.conversion_table,
          time_range: params.time_range
            ? { start: params.time_range.start, end: params.time_range.end }
            : null,
          params: params.model_params,
        }

        const res = await attributionApi.analyzeAttribution(requestData)
        setResult(res)

        // 收集结果用于模型对比
        if (res && res.touchpoints) {
          setAllResults((prev) => {
            const existing = prev.find((r) => r.model === selectedModel)
            if (existing) {
              return prev.map((r) =>
                r.model === selectedModel
                  ? { model: selectedModel, touchpoints: res.touchpoints }
                  : r,
              )
            }
            return [
              ...prev,
              { model: selectedModel, touchpoints: res.touchpoints },
            ]
          })
        }

        message.success('分析完成')
      } catch {
        // 错误已在拦截器中处理
      } finally {
        setLoading(false)
      }
    },
    [selectedModel, setLoading, resetResult, setResult],
  )

  /** 切换模型时重置对比选项（不清除已有结果） */
  const handleModelSelect = useCallback(
    (name: string) => {
      setModel(name)
    },
    [setModel],
  )

  return (
    <div className="page-container">
      <div className="page-header">
        <Title level={2}>归因分析</Title>
        <Paragraph type="secondary">
          多维度归因模型，洞察数据驱动因素
        </Paragraph>
      </div>

      {/* 顶部：模型选择 + 参数配置 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} md={10}>
          <ModelSelector
            models={models}
            selected={selectedModel}
            onSelect={handleModelSelect}
          />
        </Col>
        <Col xs={24} md={14}>
          <ParamConfig
            datasources={datasources}
            onRun={handleRun}
            loading={isLoading}
          />
        </Col>
      </Row>

      {/* 结果区域 */}
      <div
        style={{
          background: '#fff',
          borderRadius: 8,
          padding: 16,
          minHeight: 200,
        }}
      >
        <Tabs
          defaultActiveKey="result"
          items={[
            {
              key: 'result',
              label: '归因结果',
              children: (
                <AttributionResult
                  result={result}
                  loading={isLoading}
                />
              ),
            },
            {
              key: 'flow',
              label: '触点旅程',
              children: (
                <TouchpointFlow
                  data={result?.touchpoints || null}
                  loading={isLoading}
                />
              ),
            },
            {
              key: 'compare',
              label: '模型对比',
              children: (
                <ModelComparison results={allResults} />
              ),
            },
          ]}
        />
      </div>
    </div>
  )
}
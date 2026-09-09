import type { ThemeConfig } from 'antd'

/**
 * Ant Design 主题配置
 *
 * 定义全局主色、圆角、字体等设计 token
 */
export const themeConfig: ThemeConfig = {
  token: {
    // 主色
    colorPrimary: '#1677ff',
    // 成功色
    colorSuccess: '#52c41a',
    // 警告色
    colorWarning: '#faad14',
    // 错误色
    colorError: '#ff4d4f',
    // 信息色
    colorInfo: '#1677ff',
    // 圆角
    borderRadius: 6,
    // 字体大小
    fontSize: 14,
    // 字体系列
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    // 间距
    paddingLG: 24,
    marginLG: 24,
  },
  components: {
    Menu: {
      itemBg: 'transparent',
    },
    Button: {
      controlHeight: 36,
    },
    Card: {
      paddingLG: 20,
    },
  },
}
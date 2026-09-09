"""实体提取——从自然语言查询中提取时间、指标、维度、表名、条件等结构化信息"""

import re
from typing import Any


class EntityExtractor:
    """
    基于规则 + 关键词匹配的实体提取器。
    从 NL 查询中识别业务实体，返回结构化字典。
    """

    # ---------- 时间表达式 ----------
    _TIME_PATTERNS: list[re.Pattern] = [
        # 具体日期：2024年1月、2024-01-01
        re.compile(r"\d{4}[-/年]\d{1,2}(?:[-/月]\d{1,2})?"),
        # 相对时间：昨天、今天、上周、本月、上月、去年同期
        re.compile(r"(昨天|今天|明天|前天|上周|本周|下周|本月|上月|下月|今年|去年|明年|去年同期|上季度|本季度|下季度)"),
        # 时间段：最近N天/周/月/年
        re.compile(r"(最近|过去|近)\s*\d+\s*(天|日|周|月|年)"),
        # 范围：从...到...，...至...
        re.compile(r"(?:从|自)?\s*\S+\s*(?:到|至|以来)\s*\S+"),
        # 第N季度
        re.compile(r"第\s*\d\s*季度"),
    ]

    # ---------- 指标关键词 ----------
    _METRIC_KEYWORDS: list[str] = [
        "销售额",
        "收入",
        "利润",
        "毛利",
        "成本",
        "订单量",
        "订单数",
        "用户数",
        "DAU",
        "MAU",
        "GMV",
        "转化率",
        "客单价",
        "ARPU",
        "ARPPU",
        "留存率",
        "复购率",
        "点击率",
        "CTR",
        "CVR",
        "ROI",
        "LTV",
        "数量",
        "金额",
        "占比",
        "同比",
        "环比",
        "增长率",
        "SUM",
        "COUNT",
        "AVG",
        "MAX",
        "MIN",
        "平均值",
        "合计",
        "总计",
    ]

    # ---------- 维度关键词 ----------
    _DIMENSION_KEYWORDS: list[str] = [
        "按.*分组",
        "按.*分",
        "按.*维度",
        "按",
        "分",
        "城市",
        "省份",
        "地区",
        "渠道",
        "类目",
        "品类",
        "分类",
        "品牌",
        "店铺",
        "门店",
        "部门",
        "产品",
        "商品",
        "SKU",
        "时段",
        "月份",
        "日期",
        "周",
        "季度",
        "年份",
        "用户",
        "客户",
        "会员",
        "等级",
        "性别",
        "年龄段",
        "设备",
        "平台",
        "来源",
        "媒介",
    ]

    # ---------- 条件关键词 ----------
    _CONDITION_PATTERNS: list[re.Pattern] = [
        re.compile(r"(大于|大于等于|超过|>\s*=?\s*)\d+(?:?\d*"),
        re.compile(r"(小于|小于等于|低于|<=\s*\d+(?:?\d*)"),
        re.compile(r"(等于|==|=)\s*\d+(?:\.\d+)?"),
        re.compile(r"(在|属于)\s*.+\s*(中|里|内)"),
        re.compile(r"(不为空|不为 null|null|空|为空)"),
        re.compile(r"(排除|除?了|不包含|包含|含有)"),
        re.compile(r"(前|后|top|bottom)\s*\d+"),
        re.compile(r"(且|并且|and|或|or|同时)"),
    ]

    def extract_entities(self, text: str) -> dict[str, Any]:
        """
        从查询文本中提取业务实体。

        Args:
            text: 自然语言查询

        Returns:
            {
                "time": [...],       # 时间表达式列表
                "metrics": [...],    # 指标/度量关键词
                "dimensions": [...], # 维度/分组关键词
                "tables": [...],     # 疑似表名
                "conditions": [...], # 条件/过滤表达式
            }
        """
        if not text or not text.strip():
            return {"time": [], "metrics": [], "dimensions": [], "tables": [], "conditions": []}

        entities = {
            "time": self._extract_time(text),
            "metrics": self._extract_metrics(text),
            "dimensions": self._extract_dimensions(text),
            "tables": self._extract_tables(text),
            "conditions": self._extract_conditions(text),
        }
        return entities

    def _extract_time(self, text: str) -> list[str]:
        matches: list[str] = []
        for pattern in self._TIME_PATTERNS:
            found = pattern.findall(text)
            matches.extend(m.strip() for m in found if m.strip())
        return list(dict.fromkeys(matches))

    def _extract_metrics(self, text: str) -> list[str]:
        found = []
        # 精确命中 metric 关键词列表
        for keyword in self._METRIC_KEYWORDS:
            if re.search(re.escape(keyword), text, re.IGNORECASE):
                found.append(keyword)
        return list(dict.fromkeys(found))

    def _extract_dimensions(self, text: str) -> list[str]:
        found = []
        for keyword in self._DIMENSION_KEYWORDS:
            if re.search(re.escape(keyword), text, re.IGNORECASE):
                found.append(keyword)
        return list(dict.fromkeys(found))

    def _extract_tables(self, text: str) -> list[str]:
        """尝试识别疑似表名——驼峰风格、下划线风格、或出现在 from/table 后的词"""
        matches = []

        # from/table/表 后紧跟的词
        table_indicators = re.findall(r'(?:from|table|表)\s+(\w+)', text, re.IGNORECASE)
        matches.extend(table_indicators)

        # 驼峰命名 或 下划线命名：识别符合命名规范的 token
        tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', text)
        for token in tokens:
            if re.match(r'^[a-z]+_[a-z]+(?:_[a-z]+)*$', token):
                # 下划线风格表名
                matches.append(token)
            elif re.match(r'^[A-Z][a-z]+[A-Z][a-zA-Z0-9]*$', token):
                # PascalCase 风格表名
                matches.append(token)

        return list(dict.fromkeys(matches))

    def _extract_conditions(self, text: str) -> list[str]:
        matches: list[str] = []
        for pattern in self._CONDITION_PATTERNS:
            found = pattern.findall(text)
            matches.extend(m.strip() for m in found if m.strip())
        return list(dict.fromkeys(matches))


# 全局默认实例
entity_extractor = EntityExtractor()
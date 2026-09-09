"""自定义归因——基于用户定义规则的加权分配"""

from typing import Any

import pandas as pd

from app.agents.attribution_models.base import BaseAttributionModel
from app.agents.attribution_models.registry import registry


@registry.register("custom")
class CustomAttribution(BaseAttributionModel):
    name = "custom"
    description = "自定义归因——通过 rule_weights 为每个渠道手动指定权重，按比例分配转化价值"

    async def calculate(
        self,
        touchpoints: pd.DataFrame,
        conversions: pd.DataFrame,
        **params,
    ) -> dict[str, Any]:
        """
        按用户定义的渠道权重分配转化价值。
        每条转化路径中，触点的权重由 rule_weights 决定，按比例分配。

        Args:
            touchpoints: 触点表，至少含 [user_id, channel, timestamp, conversion_id]
            conversions: 转化表，至少含 [conversion_id, user_id, value]
            **params:
                rule_weights: dict[str, float]，渠道名称 -> 权重，必填
                default_weight: 未在 rule_weights 中定义的渠道的默认权重（默认 0）
                normalize: 是否在每个路径内归一化权重（默认 True）

        Returns:
            {"model": "custom", "attributions": {channel: value}, "summary": ...}
        """
        self._validate_columns(touchpoints, conversions)

        rule_weights: dict[str, float] = params.get("rule_weights", {})
        if not rule_weights:
            raise ValueError("custom 模型需要提供 rule_weights 参数")

        default_weight = params.get("default_weight", 0.0)
        normalize = params.get("normalize", True)

        merged = touchpoints.merge(
            conversions[["conversion_id", "user_id", "value"]],
            on="user_id",
            suffixes=("", "_conv"),
        )

        def distribute(group: pd.DataFrame) -> pd.DataFrame:
            group = group.copy()
            group["raw_weight"] = group["channel"].map(
                lambda ch: rule_weights.get(ch, default_weight)
            )
            total_weight = group["raw_weight"].sum()
            if total_weight <= 0:
                # 所有渠道权重均为 0，则均分
                group["weight"] = 1.0 / len(group)
            elif normalize:
                group["weight"] = group["raw_weight"] / total_weight
            else:
                group["weight"] = group["raw_weight"]
            group["attributed"] = group["weight"] * group["value"]
            return group

        attributed = merged.groupby("conversion_id", group_keys=False).apply(distribute)

        summary_value = attributed.groupby("channel")["attributed"].sum().to_dict()
        total = conversions["value"].sum()

        return {
            "model": self.name,
            "attributions": summary_value,
            "summary": {
                "total_conversion_value": float(total),
                "allocated_value": float(sum(summary_value.values())),
                "rule_weights": rule_weights,
                "default_weight": default_weight,
                "normalize": normalize,
                "channel_breakdown": {
                    ch: {"value": float(v), "share": round(v / total, 4) if total else 0}
                    for ch, v in summary_value.items()
                },
            },
        }

    def validate_params(self, params: dict) -> bool:
        rule_weights = params.get("rule_weights")
        if not isinstance(rule_weights, dict) or not rule_weights:
            return False
        if any(not isinstance(v, (int, float)) or v < 0 for v in rule_weights.values()):
            return False
        return True

    def _validate_columns(self, touchpoints: pd.DataFrame, conversions: pd.DataFrame) -> None:
        required_tp = {"user_id", "channel", "timestamp", "conversion_id"}
        required_cv = {"conversion_id", "user_id", "value"}
        missing_tp = required_tp - set(touchpoints.columns)
        missing_cv = required_cv - set(conversions.columns)
        if missing_tp:
            raise ValueError(f"touchpoints 缺少列: {missing_tp}")
        if missing_cv:
            raise ValueError(f"conversions 缺少列: {missing_cv}")
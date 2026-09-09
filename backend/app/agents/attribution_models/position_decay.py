"""位置归因（U 型）——首位和末位获得更多功劳，中间均分剩余"""

from typing import Any

import pandas as pd

from app.agents.attribution_models.base import BaseAttributionModel
from app.agents.attribution_models.registry import registry


@registry.register("position_decay")
class PositionDecayAttribution(BaseAttributionModel):
    name = "position_decay"
    description = "位置归因（U 型）——首位和末位各获 40%，中间均分剩余 20%"

    async def calculate(
        self,
        touchpoints: pd.DataFrame,
        conversions: pd.DataFrame,
        **params,
    ) -> dict[str, Any]:
        """
        对每条转化路径，首尾触点各获得 first_weight / last_weight，中间触点均分剩余。
        默认 40-20-40 U 型分配。

        Args:
            touchpoints: 触点表，至少含 [user_id, channel, timestamp, conversion_id]
            conversions: 转化表，至少含 [conversion_id, user_id, value]
            **params:
                first_weight: 首位权重比例（默认 0.4）
                last_weight: 末位权重比例（默认 0.4）

        Returns:
            {"model": "position_decay", "attributions": {channel: value}, "summary": ...}
        """
        self._validate_columns(touchpoints, conversions)

        first_weight = params.get("first_weight", 0.4)
        last_weight = params.get("last_weight", 0.4)

        merged = touchpoints.merge(
            conversions[["conversion_id", "user_id", "value"]],
            on="user_id",
            suffixes=("", "_conv"),
        )

        def distribute(group: pd.DataFrame) -> pd.DataFrame:
            group = group.copy()
            n = len(group)
            if n == 1:
                group["weight"] = 1.0
            elif n == 2:
                group["weight"] = [first_weight + last_weight, first_weight + last_weight]
            else:
                weights = [0.0] * n
                weights[0] = first_weight
                weights[-1] = last_weight
                middle = 1.0 - first_weight - last_weight
                for i in range(1, n - 1):
                    weights[i] = middle / (n - 2)
                group["weight"] = weights
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
                "first_weight": first_weight,
                "last_weight": last_weight,
                "channel_breakdown": {
                    ch: {"value": float(v), "share": round(v / total, 4) if total else 0}
                    for ch, v in summary_value.items()
                },
            },
        }

    def validate_params(self, params: dict) -> bool:
        first_weight = params.get("first_weight", 0.4)
        last_weight = params.get("last_weight", 0.4)
        if not (0 <= first_weight <= 1) or not (0 <= last_weight <= 1):
            return False
        if first_weight + last_weight > 1:
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
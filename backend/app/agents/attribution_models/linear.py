"""线性归因——每个触点获得均等功劳"""

from typing import Any

import pandas as pd

from app.agents.attribution_models.base import BaseAttributionModel
from app.agents.attribution_models.registry import registry


@registry.register("linear")
class LinearAttribution(BaseAttributionModel):
    name = "linear"
    description = "线性归因——转化路径上每个触点平分功劳"

    async def calculate(
        self,
        touchpoints: pd.DataFrame,
        conversions: pd.DataFrame,
        **params,
    ) -> dict[str, Any]:
        """
        对每条转化记录，路径上所有触点均分该转化的价值。

        Args:
            touchpoints: 触点表，至少含 [user_id, channel, timestamp, conversion_id]
            conversions: 转化表，至少含 [conversion_id, user_id, value]

        Returns:
            {"model": "linear", "attributions": {channel: value}, "summary": ...}
        """
        self._validate_columns(touchpoints, conversions)

        merged = touchpoints.merge(
            conversions[["conversion_id", "user_id", "value"]],
            on="user_id",
            suffixes=("", "_conv"),
        )

        # 每个 conversion_id 内有 n 个触点，每个分到 value / n
        def distribute(group: pd.DataFrame) -> pd.DataFrame:
            n = len(group)
            group = group.copy()
            group["attributed"] = group["value"] / n
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
                "total_touchpoints": int(len(touchpoints)),
                "channel_breakdown": {
                    ch: {"value": float(v), "share": round(v / total, 4) if total else 0}
                    for ch, v in summary_value.items()
                },
            },
        }

    def validate_params(self, params: dict) -> bool:
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
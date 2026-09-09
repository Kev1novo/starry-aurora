"""首次触碰归因——100% 功劳归第一个触点"""

from typing import Any

import pandas as pd

from app.agents.attribution_models.base import BaseAttributionModel
from app.agents.attribution_models.registry import registry


@registry.register("first_touch")
class FirstTouchAttribution(BaseAttributionModel):
    name = "first_touch"
    description = "首次触碰归因——100% 功劳归第一个触点"

    async def calculate(
        self,
        touchpoints: pd.DataFrame,
        conversions: pd.DataFrame,
        **params,
    ) -> dict[str, Any]:
        """
        对每条转化记录，取该用户时间上最早的触点，将转化价值全部分配给它。

        Args:
            touchpoints: 触点表, 至少含 [user_id, channel, timestamp, conversion_id]
            conversions: 转化表, 至少含 [conversion_id, user_id, value]

        Returns:
            {"model": "first_touch", "attributions": {channel: value}, "summary": ...}
        """
        self._validate_columns(touchpoints, conversions)

        df = touchpoints.merge(
            conversions[["conversion_id", "user_id", "value"]],
            on="user_id",
            suffixes=("", "_conv"),
        )

        # 每个 conversion_id 取第一个（最早）触点
        first_idx = df.groupby("conversion_id")["timestamp"].idxmin()
        first_touchpoints = df.loc[first_idx]

        # 按渠道汇总
        summary_value = first_touchpoints.groupby("channel")["value"].sum().to_dict()
        total = conversions["value"].sum()

        return {
            "model": self.name,
            "attributions": summary_value,
            "summary": {
                "total_conversion_value": float(total),
                "allocated_value": float(sum(summary_value.values())),
                "touchpoint_count": int(len(first_touchpoints)),
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
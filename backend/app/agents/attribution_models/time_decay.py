"""时间衰减归因——按时间指数衰减，越靠近转化的触点权重越大"""

import math
from typing import Any

import pandas as pd

from app.agents.attribution_models.base import BaseAttributionModel
from app.agents.attribution_models.registry import registry


@registry.register("time_decay")
class TimeDecayAttribution(BaseAttributionModel):
    name = "time_decay"
    description = "时间衰减归因——按时间指数衰减，越靠近转化的触点权重越大"

    async def calculate(
        self,
        touchpoints: pd.DataFrame,
        conversions: pd.DataFrame,
        **params,
    ) -> dict[str, Any]:
        """
        对每条转化路径，按时间距离转化的远近分配权重。
        使用指数衰减函数: w = exp(-decay_rate * normalized_age)
        其中 normalized_age 在 [0, 1] 之间（0=最早, 1=最晚）。

        Args:
            touchpoints: 触点表，至少含 [user_id, channel, timestamp, conversion_id]
            conversions: 转化表，至少含 [conversion_id, user_id, value]
            **params:
                decay_rate: 衰减速率（默认 1.0），越大尾部衰减越快
                half_life: 半衰期比例（0~1），与 decay_rate 二选一

        Returns:
            {"model": "time_decay", "attributions": {channel: value}, "summary": ...}
        """
        self._validate_columns(touchpoints, conversions)

        decay_rate = params.get("decay_rate", 1.0)
        half_life = params.get("half_life", None)
        if half_life is not None:
            # 从半衰期推导 decay_rate: exp(-rate * half_life) = 0.5 => rate = -ln(0.5) / half_life
            decay_rate = -math.log(0.5) / half_life

        merged = touchpoints.merge(
            conversions[["conversion_id", "user_id", "value"]],
            on="user_id",
            suffixes=("", "_conv"),
        )

        def distribute(group: pd.DataFrame) -> pd.DataFrame:
            group = group.copy()
            ts = group["timestamp"]
            t_min, t_max = ts.min(), ts.max()
            if t_min == t_max:
                group["weight"] = 1.0 / len(group)
            else:
                # 归一化: 最早=0, 最晚=1
                normalized = (ts - t_min) / (t_max - t_min)
                # 最新触点 = 最高权重
                weights = normalized.apply(lambda x: math.exp(decay_rate * x))
                total_weight = weights.sum()
                group["weight"] = weights / total_weight
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
                "decay_rate": decay_rate,
                "channel_breakdown": {
                    ch: {"value": float(v), "share": round(v / total, 4) if total else 0}
                    for ch, v in summary_value.items()
                },
            },
        }

    def validate_params(self, params: dict) -> bool:
        decay_rate = params.get("decay_rate")
        half_life = params.get("half_life")
        if decay_rate is not None and half_life is not None:
            return False  # 二选一
        if decay_rate is not None and (not isinstance(decay_rate, (int, float)) or decay_rate <= 0):
            return False
        if half_life is not None and (not isinstance(half_life, (int, float)) or not 0 < half_life < 1):
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
"""数据驱动归因——基于 Shapley 值的多触点公平分配"""

import itertools
import math
import random
from typing import Any

import pandas as pd

from app.agents.attribution_models.base import BaseAttributionModel
from app.agents.attribution_models.registry import registry


@registry.register("data_driven")
class DataDrivenAttribution(BaseAttributionModel):
    name = "data_driven"
    description = "数据驱动归因——基于 Shapley 值的公平分配，考虑各渠道在所有渠道组合中的边际贡献"

    @property
    def requires_shapley(self) -> bool:
        return True

    async def calculate(
        self,
        touchpoints: pd.DataFrame,
        conversions: pd.DataFrame,
        **params,
    ) -> dict[str, Any]:
        """
        使用 Shapley 值计算每个渠道的归因权重。
        Shapley value = sum_{S ⊆ N\\{i}} (|S|!(|N|-|S|-1)!/|N|!) * (v(S∪{i}) - v(S))

        Args:
            touchpoints: 触点表，至少含 [user_id, channel, timestamp, conversion_id]
            conversions: 转化表，至少含 [conversion_id, user_id, value]
            **params:
                n_samples: Shapley 近似采样次数（默认 0=精确计算，最多 12 个渠道）
                random_state: 随机种子

        Returns:
            {"model": "data_driven", "attributions": {channel: value}, "summary": ...}
        """
        self._validate_columns(touchpoints, conversions)

        n_samples = params.get("n_samples", 0)
        random_state = params.get("random_state", 42)

        # 构建每个 conversion_id 的渠道组合
        merged = touchpoints.merge(
            conversions[["conversion_id", "user_id", "value"]],
            on="user_id",
            suffixes=("", "_conv"),
        )

        # 每个 conversion_id 涉及的渠道集合及转化价值
        conversion_channels = (
            merged.groupby("conversion_id")
            .agg(channels=("channel", lambda x: frozenset(x.unique())), value=("value", "first"))
            .reset_index()
        )

        all_channels = sorted({ch for channels in conversion_channels["channels"] for ch in channels})
        n = len(all_channels)
        channel_index = {ch: i for i, ch in enumerate(all_channels)}

        # 将转化数据转为 (channel_set, value) 对列表
        path_data = list(zip(conversion_channels["channels"], conversion_channels["value"]))

        # 价值函数 v(S): 给定渠道子集 S，返回涉及 S 中任意渠道的转化价值之和
        def value_function(subset: frozenset) -> float:
            if not subset:
                return 0.0
            return sum(
                value for channels, value in path_data if channels & subset
            )

        if n <= 12 or n_samples == 0:
            # 精确 Shapley
            shapley_values = self._exact_shapley(all_channels, value_function)
        else:
            # 近似 Shapley（蒙特卡洛采样）
            shapley_values = self._approx_shapley(
                all_channels, value_function, n_samples=n_samples, random_state=random_state
            )

        # 将 Shapley 值按比例映射到总转化价值
        total_value = conversions["value"].sum()
        shapley_total = sum(shapley_values.values())
        scaling = total_value / shapley_total if shapley_total else 1.0
        attributions = {ch: v * scaling for ch, v in shapley_values.items()}

        return {
            "model": self.name,
            "attributions": attributions,
            "summary": {
                "total_conversion_value": float(total_value),
                "allocated_value": float(sum(attributions.values())),
                "total_channels": n,
                "shapley_method": "exact" if (n <= 12 or n_samples == 0) else "approx",
                "channel_breakdown": {
                    ch: {
                        "value": float(v),
                        "share": round(v / total_value, 4) if total_value else 0,
                        "shapley_raw": float(shapley_values[ch]),
                    }
                    for ch, v in attributions.items()
                },
            },
        }

    def _exact_shapley(
        self,
        all_channels: list[str],
        value_function,
    ) -> dict[str, float]:
        """精确计算 Shapley 值——枚举所有子集"""
        n = len(all_channels)
        shapley_values = {ch: 0.0 for ch in all_channels}

        for i, player in enumerate(all_channels):
            others = [ch for j, ch in enumerate(all_channels) if j != i]
            r = n - 1
            for subset_size in range(n):
                for coalition in itertools.combinations(others, subset_size):
                    s = frozenset(coalition)
                    s_with_i = frozenset(coalition + (player,))
                    marginal = value_function(s_with_i) - value_function(s)
                    weight = (
                        math.factorial(subset_size) * math.factorial(r - subset_size)
                    ) / math.factorial(n)
                    shapley_values[player] += marginal * weight

        return shapley_values

    def _approx_shapley(
        self,
        all_channels: list[str],
        value_function,
        n_samples: int = 1000,
        random_state: int = 42,
    ) -> dict[str, float]:
        """蒙特卡洛近似 Shapley 值——通过随机排列采样"""
        rng = random.Random(random_state)
        n = len(all_channels)
        shapley_values = {ch: 0.0 for ch in all_channels}

        for _ in range(n_samples):
            perm = all_channels.copy()
            rng.shuffle(perm)
            # 按排列顺序逐个添加渠道，记录边际贡献
            current_set: set[str] = set()
            prev_value = value_function(frozenset())
            for player in perm:
                current_set.add(player)
                new_value = value_function(frozenset(current_set))
                shapley_values[player] += new_value - prev_value
                prev_value = new_value

        # 平均
        for ch in shapley_values:
            shapley_values[ch] /= n_samples

        return shapley_values

    def validate_params(self, params: dict) -> bool:
        n_samples = params.get("n_samples", 0)
        if not isinstance(n_samples, int) or n_samples < 0:
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
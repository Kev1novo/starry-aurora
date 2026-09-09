"""归因模型抽象基类"""
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class BaseAttributionModel(ABC):
    """归因计算模型抽象基类"""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def calculate(self, touchpoints: pd.DataFrame, conversions: pd.DataFrame, **params) -> dict[str, Any]:
        ...

    @abstractmethod
    def validate_params(self, params: dict) -> bool:
        ...

    @property
    def requires_shapley(self) -> bool:
        return False
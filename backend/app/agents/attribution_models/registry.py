"""归因模型注册表——@register 装饰器实现零侵入插件式扩展"""
from typing import Any

from app.agents.attribution_models.base import BaseAttributionModel


class ModelRegistry:
    """归因模型注册表"""

    def __init__(self):
        self._models: dict[str, type[BaseAttributionModel]] = {}

    def register(self, name: str = ""):
        """装饰器注册"""

        def decorator(cls):
            model_name = name or cls.__name__.lower().replace("attribution", "")
            self._models[model_name] = cls
            return cls

        return decorator

    def get(self, name: str) -> BaseAttributionModel:
        cls = self._models.get(name)
        if not cls:
            raise KeyError(f"未知归因模型: {name}，可用: {list(self._models.keys())}")
        return cls()

    def list_models(self) -> list[dict[str, Any]]:
        return [
            {"name": name, "description": cls.description}
            for name, cls in self._models.items()
        ]


# 全局注册表实例
registry = ModelRegistry()
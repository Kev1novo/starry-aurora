"""Agent 抽象基类"""
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """所有 Agent 的抽象基类"""

    name: str = ""
    description: str = ""

    @abstractmethod
    async def run(self, input_data: dict, **kwargs) -> dict[str, Any]:
        ...

    @abstractmethod
    async def validate_input(self, input_data: dict) -> bool:
        ...

    def parse_result(self, result: dict) -> dict[str, Any]:
        return result
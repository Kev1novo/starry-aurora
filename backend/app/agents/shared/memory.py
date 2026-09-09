"""对话记忆管理——上下文窗口管理与摘要"""
from typing import Any, Optional


class ConversationMemory:
    """对话记忆管理"""

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.history: list[dict] = []

    def add_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]

    def get_context(self) -> list[dict]:
        return self.history

    def clear(self) -> None:
        self.history.clear()
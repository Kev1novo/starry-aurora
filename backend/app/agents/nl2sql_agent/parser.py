"""LLM 响应 JSON 提取工具"""
import json
import re
from typing import Any, Optional


def extract_json(raw: str) -> Optional[dict[str, Any]]:
    """从 LLM 响应文本中尝试提取 JSON 对象

    策略依次尝试：
    1. 直接 json.loads
    2. ```json ... ``` 代码块
    3. 首个 { 到末个 }

    Returns:
        dict 或 None（提取失败）
    """
    # 策略 1: 直接解析
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # 策略 2: ```json ... ``` 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 策略 3: 从头 { 到尾 }
    brace_start = raw.find("{")
    brace_end = raw.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(raw[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    return None
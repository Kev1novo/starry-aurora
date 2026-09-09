"""
结构化日志工具
基于标准库 logging 提供 JSON 格式的结构化日志输出。
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings


class JsonFormatter(logging.Formatter):
    """
    JSON 格式日志格式化器
    将日志记录输出为结构化的 JSON 行，便于日志中心收集和检索。
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # 携带 extra 中的额外字段
        if hasattr(record, "extra"):
            for key, value in record.extra.items():
                log_entry[key] = value

        # 异常信息
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    level: Optional[str] = None,
    fmt: Optional[str] = None,
) -> logging.Logger:
    """
    配置全局日志
    Args:
        level: 日志级别，默认从 settings 读取
        fmt: 日志格式，"json" 或 "text"
    Returns:
        根日志记录器
    """
    log_level = (level or settings.LOG_LEVEL).upper()
    log_format = fmt or settings.LOG_FORMAT

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # 清除已有 handler，避免重复配置
    root_logger.handlers.clear()

    # 控制台输出
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if log_format == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root_logger.addHandler(handler)

    # 关闭第三方库的干扰日志
    logging.getLogger("passlib").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的结构化日志记录器
    Args:
        name: 日志记录器名称，通常为 __name__
    Returns:
        logging.Logger 实例
    """
    return logging.getLogger(name)
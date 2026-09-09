"""
ASGI 入口
作为 uvicorn 的启动目标，提供应用实例和直接运行入口。
"""

import uvicorn

from app.main import create_app

app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.asgi:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
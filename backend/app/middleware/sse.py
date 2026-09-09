"""SSE (Server-Sent Events) 响应工具"""
from typing import AsyncGenerator

from fastapi.responses import StreamingResponse


class EventSourceResponse(StreamingResponse):
    """SSE 流式响应封装"""

    def __init__(self, event_generator: AsyncGenerator[dict, None], status_code: int = 200):
        super().__init__(
            content=self._serialize(event_generator),
            status_code=status_code,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @staticmethod
    async def _serialize(event_generator: AsyncGenerator[dict, None]) -> AsyncGenerator[bytes, None]:
        async for event in event_generator:
            yield f"event: {event['event']}\ndata: {event['data']}\n\n".encode("utf-8")
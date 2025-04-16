import asyncio
from typing import Dict, List

class SSEManager:
    _instance = None
    channels: Dict[str, asyncio.Queue] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def publish(cls, trace_id: str, event: str, data: dict):
        if trace_id in cls.channels:
            await cls.channels[trace_id].put({
                "event": event,
                "data": data
            })

    @classmethod
    def subscribe(cls, trace_id: str) -> asyncio.Queue:
        cls.channels[trace_id] = asyncio.Queue()
        return cls.channels[trace_id]

    @classmethod
    def unsubscribe(cls, trace_id: str):
        if trace_id in cls.channels:
            del cls.channels[trace_id]
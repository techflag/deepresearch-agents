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
    async def publish(cls, client_id: str, event: str, data: dict):
        if client_id in cls.channels:
            await cls.channels[client_id].put({
                "event": event,
                "data": data
            })

    @classmethod
    def subscribe(cls, client_id: str) -> asyncio.Queue:
        cls.channels[client_id] = asyncio.Queue()
        return cls.channels[client_id]

    @classmethod
    def unsubscribe(cls, client_id: str):
        if client_id in cls.channels:
            del cls.channels[client_id]
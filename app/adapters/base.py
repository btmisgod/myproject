from abc import ABC, abstractmethod
from typing import Any


class BaseAdapter(ABC):
    name: str

    @abstractmethod
    async def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


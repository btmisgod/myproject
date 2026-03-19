from typing import Any

from app.adapters.base import BaseAdapter


class OpenClawAdapter(BaseAdapter):
    name = "openclaw"

    async def ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "adapter": self.name,
            "accepted": True,
            "note": "OpenClaw adapter hook reserved for future integration.",
            "payload": payload,
        }


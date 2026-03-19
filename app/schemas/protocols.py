from typing import Any

from pydantic import BaseModel, Field


class ChannelProtocolUpdateRequest(BaseModel):
    channel_protocol: dict[str, Any] = Field(default_factory=dict)

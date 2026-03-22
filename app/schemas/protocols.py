from typing import Any

from pydantic import BaseModel, Field, model_validator


class GroupProtocolUpdateRequest(BaseModel):
    group_protocol: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if "group_protocol" in value:
            return value
        if "channel_protocol" in value:
            return {"group_protocol": value.get("channel_protocol") or {}}
        return value

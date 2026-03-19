import json
from copy import deepcopy
from typing import Any

from app.services.protocol_registry import protocol_path


def _load_json_from_layer(layer_id: str) -> dict[str, Any]:
    path = protocol_path(layer_id)
    return json.loads(path.read_text(encoding="utf-8"))


def load_general_protocol_layer() -> dict[str, Any]:
    return deepcopy(_load_json_from_layer("general"))


def load_inter_agent_protocol_layer() -> dict[str, Any]:
    return deepcopy(_load_json_from_layer("inter_agent"))


def load_channel_protocol_template() -> dict[str, Any]:
    return deepcopy(_load_json_from_layer("channel_template"))

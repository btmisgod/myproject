from typing import Any


def success(data: Any, message: str = "ok") -> dict[str, Any]:
    return {"success": True, "message": message, "data": data}


def error(message: str, *, code: str = "error", details: Any | None = None) -> dict[str, Any]:
    payload = {"success": False, "message": message, "error": {"code": code}}
    if details is not None:
        payload["error"]["details"] = details
    return payload


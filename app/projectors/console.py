import logging
from typing import Any

from app.projectors.base import Projector

logger = logging.getLogger(__name__)


class ConsoleProjector(Projector):
    name = "console"

    def project(self, event: dict[str, Any]) -> None:
        logger.info(
            "console_projection",
            extra={
                "projector": self.name,
                "sequence_id": int(event.get("sequence_id") or 0),
                "event_type": str(event.get("event_type") or ""),
                "group_id": str(event.get("group_id")) if event.get("group_id") else None,
            },
        )


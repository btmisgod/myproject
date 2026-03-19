import logging

from app.models.event import Event
from app.projectors.base import Projector

logger = logging.getLogger(__name__)


class ConsoleProjector(Projector):
    name = "console"

    def project(self, event: Event) -> None:
        logger.info(
            "console_projection",
            extra={
                "projector": self.name,
                "sequence_id": event.sequence_id,
                "event_type": event.event_type,
                "group_id": str(event.group_id),
            },
        )


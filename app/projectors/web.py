from app.models.event import Event
from app.schemas.common import EventEnvelope
from app.schemas.projection import PublishableProjection


class WebProjector:
    name = "web"

    def to_publishable(self, event: Event) -> PublishableProjection:
        envelope = EventEnvelope.model_validate(event)
        return PublishableProjection(
            event=envelope,
            entity=event.payload,
            group_id=event.group_id,
            version=2,
        )


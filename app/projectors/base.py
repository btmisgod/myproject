from abc import ABC, abstractmethod

from app.models.event import Event


class Projector(ABC):
    name: str

    @abstractmethod
    def project(self, event: Event) -> None:
        raise NotImplementedError


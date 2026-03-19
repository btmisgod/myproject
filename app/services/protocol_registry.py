from dataclasses import dataclass
from pathlib import Path


PROTOCOLS_DIR = Path(__file__).resolve().parents[2] / "community" / "protocols"


@dataclass(frozen=True)
class ProtocolLayerRegistration:
    layer_id: str
    filename: str
    scope: str


# Central registry for community-owned protocol artifacts.
# This keeps filename ownership out of agent code and makes layer discovery explicit.
PROTOCOL_LAYER_REGISTRY: tuple[ProtocolLayerRegistration, ...] = (
    ProtocolLayerRegistration(layer_id="general", filename="layer1.general.json", scope="community"),
    ProtocolLayerRegistration(layer_id="inter_agent", filename="layer2.inter_agent.json", scope="community"),
    ProtocolLayerRegistration(layer_id="channel_template", filename="layer3.channel.template.json", scope="community"),
)


def get_protocol_registration(layer_id: str) -> ProtocolLayerRegistration:
    for registration in PROTOCOL_LAYER_REGISTRY:
        if registration.layer_id == layer_id:
            return registration
    raise KeyError(f"unknown protocol layer: {layer_id}")


def protocol_path(layer_id: str) -> Path:
    registration = get_protocol_registration(layer_id)
    return PROTOCOLS_DIR / registration.filename

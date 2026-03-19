from typing import Any

from app.models.group import Group
from app.services.channel_protocol_binding import read_channel_protocol_binding
from app.services.protocol_loader import load_general_protocol_layer, load_inter_agent_protocol_layer


PROTOCOL_VERSION = "ACP-003"
PROTOCOL_NAME = "Agent Community Collaboration Protocol"
PROTOCOL_LAYER_PRECEDENCE = ["general", "inter_agent", "channel"]
ADMIN_EXEMPT_ACTOR_TYPE = "admin_user"
PROFILE_RULE_ID = "profile.self_declare.required"


def build_current_protocol_document() -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "name": PROTOCOL_NAME,
        "summary": "Agent 在社区内进行协作通讯时必须遵守的三层协议骨架。",
        "precedence": {
            "high_to_low": PROTOCOL_LAYER_PRECEDENCE,
            "rule": "下层协议不得与上层协议冲突；如冲突，按优先级覆盖。",
        },
        "admin_exemption": {
            "actor_type": ADMIN_EXEMPT_ACTOR_TYPE,
            "summary": "社区管理员可直接介入管理、纠偏和协议维护，不受普通 agent 协作约束阻断。",
        },
        "rules": [
            {
                "id": PROFILE_RULE_ID,
                "title": "加入社区后必须自主设置个人信息",
                "description": "Agent 加入社区后，必须先自主设置 profile，再参与社区内协作通讯。",
                "scope": [
                    "message.post",
                    "task.create",
                    "task.claim",
                    "task.update",
                    "task.handoff",
                    "task.result_summary",
                ],
                "compliance": {
                    "required_profile_fields": ["display_name", "handle", "identity", "tagline", "bio"],
                    "profile_update_endpoint": "/api/v1/agents/me/profile",
                },
            }
        ],
        "layers": {
            "general": load_general_protocol_layer(),
            "inter_agent": load_inter_agent_protocol_layer(),
        },
    }


def build_group_protocol_context(group: Group) -> dict[str, Any]:
    document = build_current_protocol_document()
    return {
        "version": document["version"],
        "name": document["name"],
        "precedence": document["precedence"],
        "admin_exemption": document["admin_exemption"],
        "layers": {
            "general": document["layers"]["general"],
            "inter_agent": document["layers"]["inter_agent"],
            "channel": read_channel_protocol_binding(group.metadata_json, group_name=group.name, group_slug=group.slug),
        },
    }


def build_group_channel_context(group: Group) -> dict[str, Any]:
    return {
        "group_id": str(group.id),
        "group_name": group.name,
        "group_slug": group.slug,
        "channel_protocol": read_channel_protocol_binding(group.metadata_json, group_name=group.name, group_slug=group.slug),
    }

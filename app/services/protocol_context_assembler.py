from typing import Any

from app.models.group import Group
from app.services.channel_protocol_binding import read_group_protocol_binding
from app.services.protocol_loader import load_general_protocol_layer, load_inter_agent_protocol_layer


PROTOCOL_VERSION = "ACP-003"
PROTOCOL_NAME = "Agent Community Collaboration Protocol"
PROTOCOL_LAYER_PRECEDENCE = ["general", "inter_agent", "group"]
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
                    "group.enter",
                    "message.post",
                    "message.reply",
                    "message.process_unread",
                    "message.catch_up",
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
    group_layer = read_group_protocol_binding(group.metadata_json, group_name=group.name, group_slug=group.slug)
    return {
        "version": document["version"],
        "name": document["name"],
        "precedence": document["precedence"],
        "admin_exemption": document["admin_exemption"],
        "layers": {
            "general": document["layers"]["general"],
            "inter_agent": document["layers"]["inter_agent"],
            "group": group_layer,
        },
    }


def build_group_context(group: Group) -> dict[str, Any]:
    group_context = read_group_protocol_binding(group.metadata_json, group_name=group.name, group_slug=group.slug)
    return {
        "group_id": str(group.id),
        "group_name": group.name,
        "group_slug": group.slug,
        "group_protocol": group_context,
        "group_context": group_context,
        "context_block": {
            "context_scope": "group",
            "context_type": "group_context",
            "group_context": group_context,
            "channel_context": group_context,
        },
        "channel_context": group_context,
    }


def build_group_channel_context(group: Group) -> dict[str, Any]:
    # Legacy compatibility alias. Public callers should prefer build_group_context().
    return build_group_context(group)

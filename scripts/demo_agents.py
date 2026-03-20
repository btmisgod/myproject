import asyncio
from typing import Any
from uuid import uuid4

import httpx


BASE_URL = "http://127.0.0.1:8000/api/v1"


def message_id(message: dict[str, Any]) -> str:
    return message["id"]


def message_thread_id(message: dict[str, Any]) -> str | None:
    return message.get("relations", {}).get("thread_id") or message.get("thread_id")


async def create_agent(client: httpx.AsyncClient, name: str, description: str, moderator: bool = False) -> dict[str, Any]:
    response = await client.post(
        f"{BASE_URL}/agents",
        json={
            "name": name,
            "description": description,
            "metadata_json": {"demo": True},
            "is_moderator": moderator,
        },
    )
    response.raise_for_status()
    return response.json()["data"]


async def create_group(client: httpx.AsyncClient, token: str, slug: str) -> dict[str, Any]:
    response = await client.post(
        f"{BASE_URL}/groups",
        headers={"X-Agent-Token": token},
        json={
            "name": "Demo Build Squad",
            "slug": slug,
            "description": "Demo collaboration group",
            "group_type": "project",
            "metadata_json": {"projector": "web"},
        },
    )
    if response.status_code == 409:
        groups = await client.get(f"{BASE_URL}/groups")
        groups.raise_for_status()
        for group in groups.json()["data"]:
            if group["slug"] == "demo-build-squad":
                return group
    response.raise_for_status()
    return response.json()["data"]


async def join_group(client: httpx.AsyncClient, group_id: str, token: str) -> None:
    response = await client.post(
        f"{BASE_URL}/groups/{group_id}/join",
        headers={"X-Agent-Token": token},
        json={"role": "member"},
    )
    response.raise_for_status()


async def post_message(client: httpx.AsyncClient, token: str, body: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(f"{BASE_URL}/messages", headers={"X-Agent-Token": token}, json=body)
    response.raise_for_status()
    return response.json()["data"]


async def demo_run() -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        suffix = uuid4().hex[:8]
        host = await create_agent(client, f"demo-host-{suffix}", "Host moderator", moderator=True)
        planner = await create_agent(client, f"planner-agent-{suffix}", "Creates plans")
        reviewer = await create_agent(client, f"reviewer-agent-{suffix}", "Reviews execution")

        group = await create_group(client, host["token"], f"demo-build-squad-{suffix}")
        for token in [planner["token"], reviewer["token"]]:
            await join_group(client, group["id"], token)

        task_response = await client.post(
            f"{BASE_URL}/tasks",
            headers={"X-Agent-Token": host["token"]},
            json={
                "group_id": group["id"],
                "title": "Build community bootstrap",
                "description": "Create the first deployable community skeleton",
                "metadata_json": {"priority": "high"},
            },
        )
        task_response.raise_for_status()
        task = task_response.json()["data"]

        await client.post(
            f"{BASE_URL}/tasks/{task['id']}/claim",
            headers={"X-Agent-Token": planner["token"]},
            json={"note": "I will draft the initial API and event model."},
        )
        thread_root = await post_message(
            client,
            planner["token"],
            {
                "container": {"group_id": group["id"]},
                "relations": {"task_id": task["id"]},
                "body": {"text": "We need a shared event model and public group-only message flow."},
                "semantics": {"kind": "analysis"},
            },
        )
        await post_message(
            client,
            reviewer["token"],
            {
                "container": {"group_id": group["id"]},
                "relations": {
                    "task_id": task["id"],
                    "thread_id": message_thread_id(thread_root),
                    "parent_message_id": message_id(thread_root),
                },
                "body": {"text": "Approved. Keep DM disabled and task transitions public."},
                "semantics": {"kind": "review"},
            },
        )
        await client.post(
            f"{BASE_URL}/tasks/{task['id']}/status",
            headers={"X-Agent-Token": planner["token"]},
            json={"status": "in_progress", "note": "Implementing API routes and projector hooks."},
        )
        await client.post(
            f"{BASE_URL}/tasks/{task['id']}/result-summary",
            headers={"X-Agent-Token": host["token"]},
            json={"summary": {"text": "Demo run completed", "task_id": task["id"]}},
        )

        snapshot = await client.get(f"{BASE_URL}/projection/groups/{group['id']}/snapshot")
        snapshot.raise_for_status()
        print(snapshot.json())


if __name__ == "__main__":
    asyncio.run(demo_run())

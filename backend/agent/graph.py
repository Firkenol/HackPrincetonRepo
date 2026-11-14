"""Builds the deepagents agent: an orchestrator and three subagents.

    orchestrator      delegates with the task tool; has no claim or check tools
    listing-reader    extraction only: record_claims
    physics-checker   the six check tools and lookup_form_factor; never calculates
    report-writer     assemble_report; adds no numbers

Each subagent has its own tools, system prompt and skills folder under
backend/skills/<subagent>/. Subagents do not inherit the orchestrator's skills.

A deepagents subagent receives only the task text the orchestrator writes, so the
listing itself, text or image, is handed to the listing reader by ListingMiddleware.
The reader sees the input exactly as submitted, and the orchestrator never sees it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from deepagents import FilesystemPermission, SubAgent, create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import AgentMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from agent.prompts import (
    LISTING_READER,
    LISTING_READER_PROMPT,
    ORCHESTRATOR_PROMPT,
    PHYSICS_CHECKER,
    PHYSICS_CHECKER_PROMPT,
    REPORT_WRITER,
    REPORT_WRITER_PROMPT,
    SUBAGENT_DESCRIPTIONS,
)
from agent.tools import RunState, build_toolsets

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
ORCHESTRATOR = "orchestrator"

# The agents' filesystem is the skills folder, mounted read-only. virtual_mode keeps
# every path inside it. Subagents inherit these permissions.
_READ_ONLY = [FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")]

_PROMPTS = {
    LISTING_READER: LISTING_READER_PROMPT,
    PHYSICS_CHECKER: PHYSICS_CHECKER_PROMPT,
    REPORT_WRITER: REPORT_WRITER_PROMPT,
}


class ListingMiddleware(AgentMiddleware):
    """Shows the listing reader the submitted listing, right after its task message.

    The listing is added to each model request and is not written to the agent's
    state, so an image is not copied into the orchestrator's history.
    """

    def __init__(self, listing_content: str | list[dict[str, Any]]) -> None:
        super().__init__()
        self._listing = HumanMessage(content=listing_content)

    def _with_listing(self, request):
        messages = list(request.messages)
        return request.override(messages=[*messages[:1], self._listing, *messages[1:]])

    def wrap_model_call(self, request, handler):
        return handler(self._with_listing(request))

    async def awrap_model_call(self, request, handler):
        return await handler(self._with_listing(request))


def build_subagents(state: RunState, listing_content: str | list[dict[str, Any]]) -> list[SubAgent]:
    toolsets = build_toolsets(state)
    subagents: list[SubAgent] = []
    for name in (LISTING_READER, PHYSICS_CHECKER, REPORT_WRITER):
        spec: SubAgent = {
            "name": name,
            "description": SUBAGENT_DESCRIPTIONS[name],
            "system_prompt": _PROMPTS[name],
            "tools": toolsets[name],
            "skills": [f"/{name}/"],
        }
        if name == LISTING_READER:
            spec["middleware"] = [ListingMiddleware(listing_content)]
        subagents.append(spec)
    return subagents


def build_agent(model: BaseChatModel, state: RunState, listing_content: str | list[dict[str, Any]]):
    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=ORCHESTRATOR_PROMPT,
        subagents=build_subagents(state, listing_content),
        backend=FilesystemBackend(root_dir=SKILLS_DIR, virtual_mode=True),
        permissions=_READ_ONLY,
        name=ORCHESTRATOR,
    )

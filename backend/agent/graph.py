"""Builds the deepagents agent: model, tools, skills.

Phase 2 is one agent. Phase 4 splits it into the listing-reader, physics-checker and
report-writer subagents.
"""

from __future__ import annotations

from pathlib import Path

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.language_models.chat_models import BaseChatModel

from agent.prompts import SYSTEM_PROMPT
from agent.tools import RunState, build_tools

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"

# The agent's filesystem is the skills folder, mounted read-only. virtual_mode keeps
# every path inside it.
_READ_ONLY = [FilesystemPermission(operations=["write"], paths=["/**"], mode="deny")]


def build_agent(model: BaseChatModel, state: RunState):
    return create_deep_agent(
        model=model,
        tools=build_tools(state),
        system_prompt=SYSTEM_PROMPT,
        backend=FilesystemBackend(root_dir=SKILLS_DIR, virtual_mode=True),
        skills=["/"],
        permissions=_READ_ONLY,
        name="orchestrator",
    )

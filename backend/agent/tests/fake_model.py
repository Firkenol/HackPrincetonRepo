"""A scripted chat model for tests: replays prepared replies, no network.

Each call to the model returns the next reply in the script. A reply is either a
list of tool calls or a final text. The model records every prompt it was sent and
the tools that were bound to it, so tests can check the agent wiring.
"""

from __future__ import annotations

from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from agent.tools import ASSEMBLE_REPORT, CHECK_TOOL_NAMES, RECORD_CLAIMS
from claimcheck.models import Claims


def calls(*names_and_args: tuple[str, dict]) -> AIMessage:
    """An assistant turn that calls the given tools."""
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": f"call-{name}-{index}", "type": "tool_call"}
            for index, (name, args) in enumerate(names_and_args)
        ],
    )


def record(claims: Claims) -> AIMessage:
    return calls((RECORD_CLAIMS, {"claims": claims.model_dump(mode="json", exclude_none=True)}))


def all_checks() -> AIMessage:
    return calls(*((name, {}) for name in CHECK_TOOL_NAMES))


def assemble() -> AIMessage:
    return calls((ASSEMBLE_REPORT, {}))


def full_script(claims: Claims, closing: str = "The report is ready.") -> list[AIMessage]:
    """The turn sequence the system prompt asks for."""
    return [record(claims), all_checks(), assemble(), AIMessage(content=closing)]


class ScriptedChatModel(BaseChatModel):
    script: list[AIMessage]
    prompts: list[list[BaseMessage]] = Field(default_factory=list)
    bound_tools: list[str] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedChatModel":
        names = []
        for tool in tools:
            if isinstance(tool, dict):
                names.append(tool.get("name") or tool.get("function", {}).get("name", "?"))
            else:
                names.append(getattr(tool, "name", getattr(tool, "__name__", "?")))
        self.bound_tools[:] = names
        return self

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs: Any) -> ChatResult:
        index = len(self.prompts)
        self.prompts.append(list(messages))
        if index >= len(self.script):
            raise AssertionError("the agent asked the scripted model for more turns than the script has")
        return ChatResult(generations=[ChatGeneration(message=self.script[index])])

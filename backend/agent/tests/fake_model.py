"""A scripted chat model for tests: replays prepared replies, no network.

Each call to the model returns the next reply in the script. A reply is either a
list of tool calls or a final text. The orchestrator and the three subagents share
the one model, and the agent runs them one after another, so a script is simply the
turns in the order they happen:

    orchestrator   task -> listing-reader
    listing-reader record_claims, then a closing sentence
    orchestrator   task -> physics-checker
    physics-checker the six checks, then a closing sentence
    orchestrator   task -> report-writer
    report-writer  assemble_report, then a closing sentence
    orchestrator   a closing sentence

The model records every prompt it was sent and the tools bound for that prompt, so
tests can check the agent wiring.
"""

from __future__ import annotations

import itertools
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from agent.prompts import LISTING_READER, PHYSICS_CHECKER, REPORT_WRITER
from agent.tools import ASSEMBLE_REPORT, CHECK_TOOL_NAMES, RECORD_CLAIMS
from claimcheck.models import Claims

TASK = "task"
FULL_SCRIPT_TURNS = 10

_call_numbers = itertools.count()


def calls(*names_and_args: tuple[str, dict]) -> AIMessage:
    """An assistant turn that calls the given tools."""
    return AIMessage(
        content="",
        tool_calls=[
            {"name": name, "args": args, "id": f"call-{name}-{next(_call_numbers)}", "type": "tool_call"}
            for name, args in names_and_args
        ],
    )


def say(text: str = "Done.") -> AIMessage:
    """An assistant turn that ends an agent's work with a sentence."""
    return AIMessage(content=text)


def delegate(subagent: str, description: str = "Please do your step.") -> AIMessage:
    """An orchestrator turn that hands work to a subagent."""
    return calls((TASK, {"description": description, "subagent_type": subagent}))


_UNIT_FIELDS = (
    ("nominal_voltage_v", "nominal_voltage", "V"),
    ("capacity_mah", "capacity", "mAh"),
    ("energy_wh", "energy", "Wh"),
    ("output_capacity_mah", "output_capacity", "mAh"),
    ("shelf_life_years", "shelf_life", "years"),
)
_SAME_FIELDS = ("product_type", "chemistry", "form_factors", "cell_count", "printed_codes", "printed_terms")


def as_extraction(claims: Claims) -> dict:
    """Claims written the way a model passes them to record_claims: each value with its unit."""
    data = claims.model_dump(mode="json", exclude_none=True)
    out = {key: data[key] for key in _SAME_FIELDS if key in data}
    for source, target, unit in _UNIT_FIELDS:
        if source in data:
            out[target] = {**data[source], "unit": unit}
    if "weight" in data:
        weight = dict(data["weight"])
        out["weight"] = {"value": weight.pop("value_g"), "unit": "g", **weight}
    if "dimensions" in data:
        dims = dict(data["dimensions"])
        out["dimensions"] = {
            "length": dims.pop("length_mm"),
            "width": dims.pop("width_mm"),
            "height": dims.pop("height_mm"),
            "unit": "mm",
            **dims,
        }
    return out


def record(claims: Claims) -> AIMessage:
    return calls((RECORD_CLAIMS, {"claims": as_extraction(claims)}))


def all_checks() -> AIMessage:
    return calls(*((name, {}) for name in CHECK_TOOL_NAMES))


def assemble() -> AIMessage:
    return calls((ASSEMBLE_REPORT, {}))


def reader_turns(*turns: AIMessage, closing: str = "The claims are recorded.") -> list[AIMessage]:
    """The orchestrator's delegation to the listing reader, then the reader's own turns."""
    return [delegate(LISTING_READER), *turns, say(closing)]


def checker_turns(*turns: AIMessage, closing: str = "The checks have run.") -> list[AIMessage]:
    return [delegate(PHYSICS_CHECKER), *(turns or (all_checks(),)), say(closing)]


def writer_turns(*turns: AIMessage, closing: str = "The report is ready.") -> list[AIMessage]:
    return [delegate(REPORT_WRITER), *(turns or (assemble(),)), say(closing)]


def full_script(claims: Claims, closing: str = "The report is ready.") -> list[AIMessage]:
    """The turn sequence the system prompts ask for. closing is every agent's last sentence."""
    return [
        *reader_turns(record(claims), closing=closing),
        *checker_turns(closing=closing),
        *writer_turns(closing=closing),
        say(closing),
    ]


class ScriptedChatModel(BaseChatModel):
    script: list[AIMessage]
    prompts: list[list[BaseMessage]] = Field(default_factory=list)
    # the tools bound when each prompt was sent, same index as prompts
    tools_per_prompt: list[list[str]] = Field(default_factory=list)
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
        self.tools_per_prompt.append(list(self.bound_tools))
        if index >= len(self.script):
            raise AssertionError("the agent asked the scripted model for more turns than the script has")
        return ChatResult(generations=[ChatGeneration(message=self.script[index])])

    def prompts_with_tool(self, tool: str) -> list[list[BaseMessage]]:
        """The prompts sent to whichever agent has the given tool."""
        return [prompt for prompt, tools in zip(self.prompts, self.tools_per_prompt, strict=True) if tool in tools]

    def reader_prompts(self) -> list[list[BaseMessage]]:
        return self.prompts_with_tool(RECORD_CLAIMS)

    def orchestrator_prompts(self) -> list[list[BaseMessage]]:
        return self.prompts_with_tool(TASK)

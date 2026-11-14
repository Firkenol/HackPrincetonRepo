"""The agent's tools. Every number in a report comes from here, never from the model.

Each subagent gets only its own tools:

- listing-reader   record_claims. It reads the listing, text or image, into a
                   ListingExtraction; the tool converts units in Python and stores
                   the contract's Claims object.
- physics-checker  lookup_form_factor and the six check tools. The checks take no
                   arguments: they run the Phase 1 check functions on the recorded
                   claims, so no model can alter a value between extraction and
                   arithmetic.
- report-writer    assemble_report, which builds the report in Python.

Tools are built per run around a RunState, which holds what that run recorded. The
three subagents share one RunState; that is how claims pass from one to the next
without any model copying them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from langchain_core.tools import BaseTool, StructuredTool, ToolException

from agent.extraction import ListingExtraction
from agent.prompts import LISTING_READER, PHYSICS_CHECKER, REPORT_WRITER
from claimcheck import constants
from claimcheck.checks import ALL_CHECKS
from claimcheck.models import CheckResult, Claims, EvidenceReport
from claimcheck.verdict import evaluate

RECORD_CLAIMS = "record_claims"
LOOKUP_FORM_FACTOR = "lookup_form_factor"
ASSEMBLE_REPORT = "assemble_report"
CHECK_TOOL_NAMES = tuple(check.__name__ for check in ALL_CHECKS)
TOOL_NAMES = (RECORD_CLAIMS, LOOKUP_FORM_FACTOR, *CHECK_TOOL_NAMES, ASSEMBLE_REPORT)

# Which subagent owns which tools. No tool belongs to two subagents.
TOOLS_BY_AGENT = {
    LISTING_READER: (RECORD_CLAIMS,),
    PHYSICS_CHECKER: (LOOKUP_FORM_FACTOR, *CHECK_TOOL_NAMES),
    REPORT_WRITER: (ASSEMBLE_REPORT,),
}

_CHECK_DESCRIPTIONS = {
    "check_label_consistency": "Check 1. Tests whether the stated Wh equals stated V x Ah.",
    "check_form_factor_bound": "Check 2. Tests the stated capacity against the energy a standard size code can hold.",
    "check_dimension_bound": "Check 3. Tests energy per litre from the stated product dimensions against the ceiling for the chemistry.",
    "check_weight_bound": "Check 4. Tests energy per kilogram from the stated product weight against the ceiling for the chemistry.",
    "check_label_contradiction": "Check 5. Compares the stated chemistry with codes and wording printed on the product.",
    "check_chemistry_mismatch": "Check 6. Looks for a claim that is unusual for the stated chemistry.",
}
_CHECK_SUFFIX = " Takes no arguments: it runs on the claims saved by record_claims and returns the full working."


@dataclass
class RunState:
    """What one run has recorded so far."""

    claims: Claims | None = None
    checks: dict[str, CheckResult] = field(default_factory=dict)
    report: EvidenceReport | None = None


def _require_claims(state: RunState) -> Claims:
    if state.claims is None:
        raise ToolException(f"No claims are recorded yet. Call {RECORD_CLAIMS} first.")
    return state.claims


def build_tools(state: RunState) -> list[BaseTool]:
    def record_claims(claims: ListingExtraction) -> str:
        converted = claims.to_claims()
        state.claims = converted
        state.checks.clear()
        state.report = None
        return json.dumps({"recorded": True, "claims": converted.model_dump(mode="json", exclude_none=True)})

    def lookup_form_factor(code: str) -> str:
        form_factor = constants.FORM_FACTORS.get(code.strip().upper())
        if form_factor is None:
            known = ", ".join(sorted(constants.FORM_FACTORS))
            return json.dumps({"known": False, "code": code, "known_codes": known})
        return json.dumps(
            {
                "known": True,
                "code": form_factor.code,
                "max_diameter_mm": form_factor.diameter_mm.value,
                "max_height_mm": form_factor.height_mm.value,
                "source": form_factor.diameter_mm.source.title,
            }
        )

    def make_check(check) -> BaseTool:
        def run() -> str:
            result = check(_require_claims(state))
            state.checks[result.check_id] = result
            return result.model_dump_json()

        return StructuredTool.from_function(
            run,
            name=check.__name__,
            description=_CHECK_DESCRIPTIONS[check.__name__] + _CHECK_SUFFIX,
            handle_tool_error=True,
        )

    def assemble_report() -> str:
        report = evaluate(_require_claims(state))
        state.report = report
        return json.dumps(
            {
                "verdict": report.verdict.value,
                "verdict_reason": report.verdict_reason,
                "routing": report.routing.value,
                "routing_reason": report.routing_reason,
                "not_assessed": report.not_assessed,
            }
        )

    return [
        StructuredTool.from_function(
            record_claims,
            name=RECORD_CLAIMS,
            description=(
                "Save what the listing text or image states. Call this once. Give each value "
                "in the unit shown; conversion happens inside the tool. Leave out every field the listing does "
                "not state. Never include a seller, store or brand name. Calling it again replaces the saved "
                "claims. Returns the claims as stored, in standard units."
            ),
            handle_tool_error=True,
        ),
        StructuredTool.from_function(
            lookup_form_factor,
            name=LOOKUP_FORM_FACTOR,
            description="Look up the standard dimensions of a battery size code such as 18650, 21700, AA or AAA.",
            handle_tool_error=True,
        ),
        *(make_check(check) for check in ALL_CHECKS),
        StructuredTool.from_function(
            assemble_report,
            name=ASSEMBLE_REPORT,
            description=(
                "Build the evidence report from the saved claims: verdict, routing and all six checks. "
                "Takes no arguments. Call it once."
            ),
            handle_tool_error=True,
        ),
    ]


def build_toolsets(state: RunState) -> dict[str, list[BaseTool]]:
    """The tools of one run, grouped by the subagent that may call them."""
    by_name = {tool.name: tool for tool in build_tools(state)}
    return {agent: [by_name[name] for name in names] for agent, names in TOOLS_BY_AGENT.items()}

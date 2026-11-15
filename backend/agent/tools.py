"""The agent's tools. Every number in a report comes from here, never from the model.

Each subagent gets only its own tools:

- listing-reader   record_claims for a battery listing, and one record tool per check
                   pack (projector, magnifying glass, monocular). The tool it calls
                   decides the category. Each converts units in Python and stores
                   the claims object for that category.
- physics-checker  list_checks, lookup_form_factor, the six battery check tools and
                   the pack check tools. The checks take no arguments: they run the
                   check functions on the recorded claims, so no model can alter a
                   value between extraction and arithmetic.
- report-writer    assemble_report, which builds the report in Python.

Tools are built per run around a RunState, which holds what that run recorded. The
three subagents share one RunState; that is how claims pass from one to the next
without any model copying them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from langchain_core.tools import BaseTool, StructuredTool, ToolException

from pydantic import BaseModel

from agent.extraction import ListingExtraction
from agent.pack_extraction import EXTRACTIONS
from agent.prompts import LISTING_READER, PHYSICS_CHECKER, REPORT_WRITER
from claimcheck import constants
from claimcheck.checks import ALL_CHECKS
from claimcheck.models import AnyReport, CheckResult, Claims, PackEvidenceReport
from claimcheck.verdict import evaluate
from packs.registry import PACKS

RECORD_CLAIMS = "record_claims"
LOOKUP_FORM_FACTOR = "lookup_form_factor"
ASSEMBLE_REPORT = "assemble_report"
LIST_CHECKS = "list_checks"
# The six battery checks.
CHECK_TOOL_NAMES = tuple(check.__name__ for check in ALL_CHECKS)
# The record tool and the check tools of each pack, keyed by pack id.
PACK_RECORD_TOOLS = {pack: extraction.tool for pack, extraction in EXTRACTIONS.items()}
PACK_CHECK_TOOLS = {pack.id: tuple(check.__name__ for check in pack.checks) for pack in PACKS.values()}
PACK_RECORD_TOOL_NAMES = tuple(PACK_RECORD_TOOLS.values())
PACK_CHECK_TOOL_NAMES = tuple(name for names in PACK_CHECK_TOOLS.values() for name in names)
TOOL_NAMES = (
    RECORD_CLAIMS,
    *PACK_RECORD_TOOL_NAMES,
    LIST_CHECKS,
    LOOKUP_FORM_FACTOR,
    *CHECK_TOOL_NAMES,
    *PACK_CHECK_TOOL_NAMES,
    ASSEMBLE_REPORT,
)

# Which subagent owns which tools. No tool belongs to two subagents.
TOOLS_BY_AGENT = {
    LISTING_READER: (RECORD_CLAIMS, *PACK_RECORD_TOOL_NAMES),
    PHYSICS_CHECKER: (LIST_CHECKS, LOOKUP_FORM_FACTOR, *CHECK_TOOL_NAMES, *PACK_CHECK_TOOL_NAMES),
    REPORT_WRITER: (ASSEMBLE_REPORT,),
}

BATTERY = "battery"

_CHECK_DESCRIPTIONS = {
    "check_label_consistency": "Check 1. Tests whether the stated Wh equals stated V x Ah.",
    "check_form_factor_bound": "Check 2. Tests the stated capacity against the energy a standard size code can hold.",
    "check_dimension_bound": "Check 3. Tests energy per litre from the stated product dimensions against the ceiling for the chemistry.",
    "check_weight_bound": "Check 4. Tests energy per kilogram from the stated product weight against the ceiling for the chemistry.",
    "check_label_contradiction": "Check 5. Compares the stated chemistry with codes and wording printed on the product.",
    "check_chemistry_mismatch": "Check 6. Looks for a claim that is unusual for the stated chemistry.",
}
_CHECK_SUFFIX = " Takes no arguments: it runs on the claims saved by record_claims and returns the full working."
_PACK_CHECK_SUFFIX = " Takes no arguments: it runs on the claims the listing reader saved and returns the full working."


@dataclass
class RunState:
    """What one run has recorded so far."""

    claims: Claims | None = None  # a battery listing
    pack: str | None = None  # the pack id, for a listing in a pack's category
    pack_claims: BaseModel | None = None  # that pack's claims
    checks: dict[str, CheckResult] = field(default_factory=dict)
    report: AnyReport | None = None

    @property
    def has_claims(self) -> bool:
        return self.claims is not None or self.pack_claims is not None


def _wrong_category(state: RunState) -> ToolException:
    label = PACKS[state.pack].label if state.pack else BATTERY
    return ToolException(
        f"The recorded listing is a {label} listing, so this check does not apply. "
        f"Call {LIST_CHECKS} to see which checks to run."
    )


def _require_claims(state: RunState) -> Claims:
    if state.claims is None:
        if state.pack_claims is not None:
            raise _wrong_category(state)
        raise ToolException("No claims are recorded yet. The listing reader records them first.")
    return state.claims


def _require_pack_claims(state: RunState, pack: str) -> BaseModel:
    if state.pack != pack or state.pack_claims is None:
        if state.has_claims:
            raise _wrong_category(state)
        raise ToolException("No claims are recorded yet. The listing reader records them first.")
    return state.pack_claims


def pack_report(state: RunState) -> PackEvidenceReport:
    """The pack's report in the contract's shape. Computed in Python by the pack."""
    report = PACKS[state.pack].evaluate(state.pack_claims)
    return PackEvidenceReport.model_validate(report.model_dump(mode="json"))


def evaluate_state(state: RunState) -> AnyReport:
    """The report for whatever the run recorded: a battery listing or a pack's category."""
    if state.pack_claims is not None:
        return pack_report(state)
    return evaluate(state.claims)


def build_tools(state: RunState) -> list[BaseTool]:
    def record_claims(claims: ListingExtraction) -> str:
        converted = claims.to_claims()
        state.claims = converted
        state.pack, state.pack_claims = None, None
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

    def make_pack_record(extraction) -> BaseTool:
        def record(claims: BaseModel) -> str:
            converted = claims.to_claims()
            state.claims = None
            state.pack, state.pack_claims = extraction.pack, converted
            state.checks.clear()
            state.report = None
            return json.dumps(
                {"recorded": True, "category": PACKS[extraction.pack].label, "claims": converted.model_dump(mode="json", exclude_none=True)}
            )

        record.__annotations__["claims"] = extraction.model
        return StructuredTool.from_function(
            record, name=extraction.tool, description=extraction.description, handle_tool_error=True
        )

    def make_pack_check(pack: str, check) -> BaseTool:
        def run() -> str:
            result = check(_require_pack_claims(state, pack))
            state.checks[result.check_id] = result
            return result.model_dump_json()

        return StructuredTool.from_function(
            run,
            name=check.__name__,
            description=f"{PACKS[pack].label.capitalize()} listings only. {check.__doc__}{_PACK_CHECK_SUFFIX}",
            handle_tool_error=True,
        )

    def list_checks() -> str:
        if not state.has_claims:
            raise ToolException("No claims are recorded yet. The listing reader records them first.")
        if state.pack is not None:
            return json.dumps({"category": PACKS[state.pack].label, "checks": list(PACK_CHECK_TOOLS[state.pack])})
        return json.dumps({"category": BATTERY, "checks": list(CHECK_TOOL_NAMES)})

    def assemble_report() -> str:
        if not state.has_claims:
            raise ToolException("No claims are recorded yet. The listing reader records them first.")
        report = evaluate_state(state)
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
                "Save what a battery listing (loose cells, battery pack or power bank) states. Use it also "
                "when the product is in none of the other categories. Call this once. Give each value "
                "in the unit shown; conversion happens inside the tool. Leave out every field the listing does "
                "not state. Never include a seller, store or brand name. Calling it again replaces the saved "
                "claims. Returns the claims as stored, in standard units."
            ),
            handle_tool_error=True,
        ),
        *(make_pack_record(extraction) for extraction in EXTRACTIONS.values()),
        StructuredTool.from_function(
            list_checks,
            name=LIST_CHECKS,
            description=(
                "Says which category the recorded listing is in and names the check tools to run for it. "
                "Takes no arguments. Call it first."
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
        *(make_pack_check(pack.id, check) for pack in PACKS.values() for check in pack.checks),
        StructuredTool.from_function(
            assemble_report,
            name=ASSEMBLE_REPORT,
            description=(
                "Build the evidence report from the saved claims: verdict, routing and every check for the category. "
                "Takes no arguments. Call it once."
            ),
            handle_tool_error=True,
        ),
    ]


def build_toolsets(state: RunState) -> dict[str, list[BaseTool]]:
    """The tools of one run, grouped by the subagent that may call them."""
    by_name = {tool.name: tool for tool in build_tools(state)}
    return {agent: [by_name[name] for name in names] for agent, names in TOOLS_BY_AGENT.items()}

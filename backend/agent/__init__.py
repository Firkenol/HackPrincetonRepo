"""The ClaimCheck agent: a deepagents orchestrator with three subagents (listing
reader, physics checker, report writer) that reads a listing and calls the checks.

- model.py    loads the chat model from MODEL_PROVIDER and MODEL_ID
- tools.py    the tools, grouped by subagent; all arithmetic happens in the claimcheck functions they call
- prompts.py  system prompts of the orchestrator and the three subagents
- graph.py    create_deep_agent wiring: the subagents, each with its skills from backend/skills/
- runner.py   run_listing, which turns the agent run into contract stream events

Command line: python -m agent "listing text"   (from backend/)
"""

from agent.runner import run_listing

__all__ = ["run_listing"]

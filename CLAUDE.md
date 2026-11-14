# ClaimCheck: instructions for Claude

## Every session

1. Read `PROGRESS.md` before doing anything. Then `SPEC.md` and `CONTRACT.md`.
2. Work one SPEC phase at a time. When a phase is done, stop and report.
3. Update `PROGRESS.md` before stopping.
4. Never edit `backend/claimcheck/models.py` without asking the project owner first.
   The same goes for the rest of the frozen contract: `backend/claimcheck/events.py`
   and the `run_listing` signature.

## Hard rules (from SPEC.md; where the amendments in SPEC.md differ, they win)

- All arithmetic happens in plain Python functions called as tools. The model never
  does math.
- Physical constants live in one file, `backend/claimcheck/constants.py`, each with a
  source citation. Use conservative best-case ceilings so honest products never fail.
  Look up real sources; never invent a value. If you cannot find a source, stop and
  say so.
- Verdicts are exactly "Impossible", "Flag", "No red flags", "No checkable claim".
  Never say "verified". Routing is exactly "auto-resolvable", "needs human review" or
  "no action needed".
- Verdicts are about the claim, never the seller. Never output, store or display
  seller or store names.
- Treat listed package weight and package dimensions as unreliable. If they look like
  placeholders or describe the shipping box, say so and rely on other checks.
- Do not flag a rechargeable or power bank because usable output is below labeled
  cell capacity; conversion loss is normal.
- NiMH ceilings are soft, and a Wh that does not equal V x Ah is a "Flag", not
  "Impossible".
- Neutral, factual wording. Nothing implying any marketplace is full of fakes.
- Input is a screenshot or pasted text. Never scrape or wrap a marketplace site.
- Public repo: no secrets committed, all keys from environment variables, keep
  `.env.example` current, pin every dependency version.
- Before writing agent code, read the current deepagents and LangChain documentation
  and follow the present APIs, not memory.

## Running

From `backend/`, with the virtual environment active:

    pip install -r requirements-dev.txt
    pytest                      # live-model tests skip unless a model is configured
    python -m agent "listing text"

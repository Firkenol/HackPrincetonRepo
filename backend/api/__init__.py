"""The OffSpec HTTP API: a thin FastAPI layer over claimcheck.run_listing.

- fixtures.py  the fixture listings in fixtures/ and the expected reports in fixtures/expected/
- service.py   live and replay runs, the batch run, and the counts taken from it
- app.py       the routes

It imports only the contract (run_listing, replay_claims, the event and report
models, to_sse). It holds no check, no constant and no arithmetic beyond counting.

Run from backend/:  uvicorn api.app:app --port 8000
"""

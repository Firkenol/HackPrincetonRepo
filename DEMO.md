# OffSpec demo

About 90 seconds. Six steps, one talking point each.

## Before you start

- **Recorded walkthrough:** `demo/offspec-walkthrough.mp4` (70 seconds, captioned, 1440 px
  wide). Recorded from the real console running against the local API in sample data
  mode. The file is not committed; re-create it with the steps at the end of this page.
- **Hosted console:** https://benmorxles.github.io/offspec-demo/ is the web console as a
  static site. It has no API behind it, so it shows the bundled sample reports and says
  "Sample data: the API is offline". Use it to browse reports and the math; it cannot
  check a new listing.
- **Live on a laptop:** start the API and the web console as in `README.md`, then open
  http://localhost:3000.

## What is live and what is staged

| Part | Status |
|---|---|
| Checks, arithmetic, verdicts, routing, evidence reports | Real. Computed by the check code and shown as produced. |
| Trace, agents, tool calls | Real events from the API. In sample data mode they replay at once; with a model configured they stream as the agents work. |
| Reading a listing with a model | Only with `MODEL_PROVIDER` and `MODEL_ID` set. Without them the console is labelled "Sample data" and only the fixture listings can be checked. |
| Screenshots in `fixtures/` | Captured in advance, with seller names, store links and the delivery address covered. |

## The six steps

1. **An impossible claim.** Paste `fixtures/fixture_01.txt` and press Check listing.
   Verdict `Impossible`, routing `auto-resolvable`.
   *Talking point:* the claim needs more energy than a cell of that size can hold. Open
   "Form-factor bound" to show each line of arithmetic and the cited ceiling.
2. **An honest listing passes.** Open "Lithium-ion battery, 6,200 mAh, 7.4 V, 45.88 Wh"
   in the audit feed. Verdict `No red flags`, routing `no action needed`.
   *Talking point:* ceilings are best-case figures from cited sources, so a product that is
   what it says it is sits well below them. "No red flags" is not a confirmation.
3. **A contradiction between the title and the product.** Open "AA/AAA alkaline battery,
   heavy duty". Verdict `Flag`, routing `needs human review`.
   *Talking point:* the title says alkaline, the cells are marked R6 and R03, which are the
   IEC codes for zinc-carbon. A calculation cannot settle that, so a person looks.
4. **Nothing to test.** Open "AA/AAA zinc-carbon battery, heavy duty". Verdict
   `No checkable claim`.
   *Talking point:* the tool stays quiet when a listing states nothing numeric.
5. **Batch.** Switch to the Batch tab.
   *Talking point:* 29 listings in one run: 2 settled by the calculation, 10 routed to a
   person, 17 needing nothing. Reviewer time goes to the ambiguous ones.
6. **A fresh listing.** Paste or upload a new listing through the same intake.
   *Talking point:* same path, same report. This step needs a configured model; without one
   the console says the listing was not checked rather than showing a sample.

Things to say plainly if asked: verdicts are about the claim, never the seller, and no
seller or store name is stored or shown; input is pasted text or a screenshot, nothing is
scraped; the model never does arithmetic.

## Re-recording the walkthrough

`demo/record.mjs` drives headless Chrome through the steps above and captures frames. It
expects the console on port 3010 and its API on port 8010, so it does not disturb a
development server on 3000 and 8000.

```
# 1. API for the recording
cd backend && CORS_ORIGINS=http://127.0.0.1:3010 uvicorn api.app:app --port 8010

# 2. Console as static files, pointed at that API (build in a copy of web/ if a dev server is running)
cd web && STATIC_EXPORT=1 NEXT_PUBLIC_API_URL=http://127.0.0.1:8010 npm run build
cd out && python3 -m http.server 3010 --bind 127.0.0.1

# 3. Record, then encode (needs ffmpeg)
node demo/record.mjs "$PWD" /tmp/offspec-rec
cd /tmp/offspec-rec && ffmpeg -f concat -safe 0 -i frames.txt -vf fps=30 -c:v libx264 -pix_fmt yuv420p walkthrough.mp4
```

## Updating the hosted console

```
cd web && STATIC_EXPORT=1 BASE_PATH=/offspec-demo NEXT_PUBLIC_API_URL=https://api.offline.invalid npm run build
```

Push the contents of `web/out` (plus an empty `.nojekyll` file) to the `main` branch of
`benmorxles/offspec-demo`. To give the hosted console a real API, deploy the API as in
`README.md`, set `NEXT_PUBLIC_API_URL` to its URL in that build, and add the Pages URL to
the API's `CORS_ORIGINS`.

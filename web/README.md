# OffSpec web console

The Next.js front end. Setup and run instructions are in the README at the repo root.

```
npm install
npm run dev            # http://localhost:3000, expects the API on http://localhost:8000
npm test
npm run sync-samples   # refresh src/samples/samples.json from ../fixtures
```

Set `NEXT_PUBLIC_API_URL` in `web/.env.local` if the API is somewhere else.

- `src/lib/` types from CONTRACT.md, the API client and event-stream parser, product descriptions
- `src/components/` the console: metrics bar, audit feed, verdict card, "Show the math", trace, batch view
- `src/samples/` sample reports bundled for when the API cannot be reached

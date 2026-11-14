// POST /api/check, as in CONTRACT.md: multipart form with exactly one of `image` or
// `text`, answered with a text/event-stream of contract events.
//
// CLAIMCHECK_API_URL set   -> forward the request to the real API and pipe its stream back.
// CLAIMCHECK_API_URL unset -> replay fixtures/expected/ (mock).

import { errorEvents, eventsFor, loadFixture, resolveFixtureId, toSse } from "@/lib/mock/replay";
import type { StreamEvent } from "@/lib/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const SSE_HEADERS = {
  "Content-Type": "text/event-stream; charset=utf-8",
  "Cache-Control": "no-cache, no-transform",
  "X-Accel-Buffering": "no",
};

function streamOf(events: StreamEvent[], delayMs: number, signal: AbortSignal): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    async start(controller) {
      for (const event of events) {
        if (signal.aborted) break;
        controller.enqueue(encoder.encode(toSse(event)));
        if (delayMs > 0) await new Promise((r) => setTimeout(r, delayMs));
      }
      controller.close();
    },
  });
  return new Response(body, { headers: SSE_HEADERS });
}

export async function POST(request: Request): Promise<Response> {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return Response.json({ detail: "Expected multipart form data." }, { status: 400 });
  }
  const image = form.get("image");
  const text = form.get("text");
  const hasImage = image instanceof File && image.size > 0;
  const hasText = typeof text === "string" && text.trim().length > 0;
  if (hasImage === hasText) {
    return Response.json({ detail: "Send exactly one of image or text." }, { status: 400 });
  }

  const apiUrl = process.env.CLAIMCHECK_API_URL?.replace(/\/+$/, "");
  if (apiUrl) {
    const forward = new FormData();
    if (hasImage) forward.set("image", image, image.name);
    else forward.set("text", text as string);
    try {
      const upstream = await fetch(`${apiUrl}/api/check`, { method: "POST", body: forward, signal: request.signal });
      if (!upstream.ok || !upstream.body) {
        return Response.json({ detail: `The API answered with status ${upstream.status}.` }, { status: 502 });
      }
      return new Response(upstream.body, { headers: SSE_HEADERS });
    } catch {
      return Response.json({ detail: "The API could not be reached." }, { status: 502 });
    }
  }

  const delayMs = Math.max(0, Number(process.env.CLAIMCHECK_MOCK_DELAY_MS ?? 90) || 0);
  const id = resolveFixtureId(hasImage ? { filename: image.name } : { text: text as string });
  if (id === null) {
    const hint = hasImage
      ? "name the file fixture_01 to fixture_09"
      : "use one of the sample listings";
    return streamOf(
      errorEvents(`Mock mode replays only the nine recorded fixtures. To replay one, ${hint}. Set CLAIMCHECK_API_URL to check other listings.`),
      delayMs,
      request.signal,
    );
  }
  try {
    const report = await loadFixture(id);
    return streamOf(eventsFor(report, hasImage ? "image" : "text"), delayMs, request.signal);
  } catch {
    return streamOf(errorEvents(`The recorded report for fixture ${id} could not be read.`), delayMs, request.signal);
  }
}

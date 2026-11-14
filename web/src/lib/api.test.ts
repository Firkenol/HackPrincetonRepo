import { describe, expect, it, vi } from "vitest";
import { ApiUnreachable, createSseParser, fetchStats, verifyListing, type Frame } from "./api";

const META = `event: meta\ndata: {"mode":"replay","sample_data":true,"sample_id":null}\n\n`;
const STEP = `event: agent_step\ndata: {"type":"agent_step","run_id":"r","seq":0,"agent":"orchestrator","message":"Reading the listing text."}\n\n`;
const ERROR = `event: error\ndata: {"type":"error","run_id":"r","seq":1,"agent":"orchestrator","message":"No."}\n\n`;

describe("createSseParser", () => {
  it("returns the meta frame and the contract events in order", () => {
    const frames = createSseParser()(META + STEP + ERROR);
    expect(frames.map((f) => f.kind)).toEqual(["meta", "event", "event"]);
    expect(frames[0]).toEqual({ kind: "meta", meta: { mode: "replay", sample_data: true, sample_id: null } });
    expect(frames[2].kind === "event" && frames[2].event.type).toBe("error");
  });

  it("joins a frame that arrives in pieces, and accepts CRLF", () => {
    const parse = createSseParser();
    const text = (META + STEP).replace(/\n/g, "\r\n");
    const frames: Frame[] = [];
    for (let i = 0; i < text.length; i += 7) frames.push(...parse(text.slice(i, i + 7)));
    expect(frames.map((f) => f.kind)).toEqual(["meta", "event"]);
  });

  it("skips a frame that is not JSON", () => {
    expect(createSseParser()("event: x\ndata: not json\n\n" + STEP)).toHaveLength(1);
  });
});

function streamOf(...chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

describe("verifyListing", () => {
  it("posts the text as form data and passes each frame on", async () => {
    const fetchMock = vi.fn(async () => streamOf(META, STEP.slice(0, 30), STEP.slice(30) + ERROR));
    vi.stubGlobal("fetch", fetchMock);

    const frames: Frame[] = [];
    await verifyListing({ text: "18650 12000mAh" }, (f) => frames.push(f));

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toMatch(/\/api\/verify-listing$/);
    expect(init.method).toBe("POST");
    expect((init.body as FormData).get("text")).toBe("18650 12000mAh");
    expect(frames.map((f) => f.kind)).toEqual(["meta", "event", "event"]);
  });

  it("sends an image as a file and a sample by id", async () => {
    const fetchMock = vi.fn(async () => streamOf(META));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File([new Uint8Array([1, 2, 3])], "shot.png", { type: "image/png" });

    await verifyListing({ image: file }, () => {});
    await verifyListing({ sample: "fixture_03" }, () => {});

    const bodies = fetchMock.mock.calls.map((call) => (call as unknown as [string, RequestInit])[1].body as FormData);
    expect(bodies[0].get("image")).toBeInstanceOf(File);
    expect(bodies[1].get("sample")).toBe("fixture_03");
  });

  it("reports the API's own message when the request is refused", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: "Send exactly one of image, text or sample." }), { status: 400 })));
    await expect(verifyListing({ text: "x" }, () => {})).rejects.toThrow("Send exactly one of image, text or sample.");
  });
});

describe("an unreachable API", () => {
  it("is told apart from an API that answers", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    }));
    await expect(fetchStats()).rejects.toBeInstanceOf(ApiUnreachable);
    await expect(verifyListing({ text: "x" }, () => {})).rejects.toBeInstanceOf(ApiUnreachable);

    vi.stubGlobal("fetch", vi.fn(async () => new Response("bad gateway", { status: 502 })));
    await expect(fetchStats()).rejects.toBeInstanceOf(ApiUnreachable);
  });
});

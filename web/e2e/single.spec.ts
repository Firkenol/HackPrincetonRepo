import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { VERDICTS, ROUTINGS } from "../lib/types";
import { FIXTURE_IDS, SHOTS, expectedReport } from "./helpers";

for (const id of FIXTURE_IDS) {
  test(`fixture ${id} renders from the mock stream`, async ({ page }) => {
    const want = expectedReport(id);
    await page.goto("/");
    await expect(page.getByTestId("mode")).toContainText("Mock");
    await page.getByTestId(`sample-${id}`).click();

    const card = page.getByTestId("verdict-card");
    await expect(card).toHaveAttribute("data-state", "done");

    // Verdict and routing: the exact contract strings from the fixture.
    expect(VERDICTS).toContain(want.verdict);
    expect(ROUTINGS).toContain(want.routing);
    await expect(page.getByTestId("verdict")).toHaveText(want.verdict);
    await expect(page.getByTestId("routing")).toHaveText(want.routing);
    await expect(card).toContainText(want.verdict_reason);
    await expect(card).toContainText(want.routing_reason);

    // Every check is shown with its status; the arithmetic and constants are all there.
    for (const check of want.checks) {
      const block = page.getByTestId(`check-${check.check_id}`);
      await expect(block).toHaveAttribute("data-status", check.status);
      if (check.status === "not_assessed") {
        // Listed with its reason in the neutral section, never as a failure.
        await expect(page.getByTestId("not-assessed").getByTestId(`check-${check.check_id}`)).toContainText(check.not_assessed_reason!);
      } else {
        await expect(block).toContainText(check.summary);
        await expect(block.getByTestId("step")).toHaveCount(check.steps.length);
        for (const step of check.steps) await expect(block).toContainText(step.text.slice(step.label.length + 2));
        for (const c of check.constants) {
          await expect(block.getByTestId("constants")).toContainText(c.source_title);
          await expect(block.getByTestId("constants").locator(`a[href="${c.source_url}"]`).first()).toBeVisible();
        }
      }
    }
    const notAssessed = want.checks.filter((c) => c.status === "not_assessed").length;
    await expect(page.getByTestId("not-assessed")).toContainText(`${notAssessed} of 6 checks`);
    await expect(page.getByTestId("not-assessed")).toContainText("This is not a failure");

    // Trace: one row per agent step, tool call and the final report.
    await expect(page.getByTestId("trace").locator("li")).toHaveCount(12); // 4 agent steps, 7 tool calls, 1 final report
    await expect(page.getByTestId("trace")).toContainText("check_form_factor_bound");

    // Wording rules.
    const text = (await page.locator("body").innerText()).toLowerCase();
    expect(text).not.toContain("verified");
    expect(text).not.toMatch(/seller|sold by|store name/);

    // The download is the report itself.
    const [download] = await Promise.all([page.waitForEvent("download"), page.getByTestId("download-json").click()]);
    expect(download.suggestedFilename()).toMatch(/^claimcheck-.*\.json$/);
    expect(JSON.parse(readFileSync(await download.path(), "utf8"))).toEqual(want);

    if (SHOTS) await page.screenshot({ path: `${SHOTS}/single-${id}.png`, fullPage: true });
  });
}

test("the numbers are on screen within a second of the report", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("sample-1").click();
  await expect(page.getByTestId("verdict")).toHaveText("Impossible");
  const comparison = page.getByTestId("check-form_factor_bound").getByTestId("step").last();
  await expect(comparison).toContainText("44.4 Wh > 23.19 Wh");
  await expect(comparison).toHaveCSS("opacity", "1", { timeout: 1000 });
});

test("a screenshot named after a fixture replays that fixture", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("dropzone-input").setInputFiles({ name: "fixture_03.png", mimeType: "image/png", buffer: Buffer.from("not a real image") });
  await expect(page.getByTestId("verdict")).toHaveText("Flag");
  await expect(page.getByTestId("routing")).toHaveText("needs human review");
  await expect(page.locator("img")).toHaveCount(0); // the screenshot is never displayed
});

test("pasted text runs, and an unrecorded listing shows the stream's error event", async ({ page }) => {
  await page.goto("/");
  await page.getByTestId("listing-text").fill("Some listing the mock has no recording for.");
  await page.getByTestId("run-text").click();
  await expect(page.getByTestId("run-error")).toContainText("Mock mode replays only the nine recorded fixtures");
  await expect(page.getByTestId("verdict")).toHaveCount(0);
});

test("the endpoint speaks the contract's SSE format", async ({ request }) => {
  const response = await request.post("/api/check", { multipart: { text: "fixture 2" } });
  expect(response.headers()["content-type"]).toContain("text/event-stream");
  const frames = (await response.text()).trim().split("\n\n");
  const events = frames.map((frame) => {
    const [eventLine, dataLine] = frame.split("\n");
    const data = JSON.parse(dataLine!.replace(/^data: /, ""));
    expect(eventLine).toBe(`event: ${data.type}`);
    return data;
  });
  expect(events.map((e) => e.seq)).toEqual(events.map((_, i) => i));
  expect(new Set(events.map((e) => e.run_id)).size).toBe(1);
  expect(events.at(-1).type).toBe("final_report");
  expect(events.at(-1).report).toEqual(expectedReport(2));
  expect(events.filter((e) => e.type === "tool_call").length).toBe(events.filter((e) => e.type === "tool_result").length);

  const both = await request.post("/api/check", { multipart: { text: "x", image: { name: "a.png", mimeType: "image/png", buffer: Buffer.from("x") } } });
  expect(both.status()).toBe(400);
});

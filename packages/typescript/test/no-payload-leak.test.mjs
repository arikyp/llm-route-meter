import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { LocalMeterWriter, meteredCall } from "../src/index.js";

test("meteredCall does not persist prompt or response sentinels", async () => {
  const tmp = path.join(os.tmpdir(), `llm-route-meter-${Date.now()}.jsonl`);
  const writer = new LocalMeterWriter(tmp);
  const promptSentinel = "PROMPT_SECRET_SENTINEL";
  const responseSentinel = "RESPONSE_SECRET_SENTINEL";
  const response = await meteredCall({
    routeId: "ticket_summary",
    model: "managed-small",
    writer,
    batchable: true,
    qualitySignal: "schema_valid",
    call: async () => ({
      usage: { prompt_tokens: 100, prompt_tokens_details: { cached_tokens: 50 }, completion_tokens: 25 },
      choices: [{ message: { content: responseSentinel } }],
    }),
    messages: [{ role: "user", content: promptSentinel }],
  });
  assert.equal(response.choices[0].message.content, responseSentinel);
  const output = fs.readFileSync(tmp, "utf8");
  assert.equal(output.includes(promptSentinel), false);
  assert.equal(output.includes(responseSentinel), false);
  assert.match(output, /metadata_only/);
});

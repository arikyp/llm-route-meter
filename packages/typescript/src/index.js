import fs from "node:fs";
import crypto from "node:crypto";

const FORBIDDEN_FIELD_NAMES = new Set([
  "prompt", "prompts", "message", "messages", "response", "responses", "content", "contents", "text", "transcript", "transcripts", "document", "documents", "file", "files", "api_key", "apikey", "authorization", "auth_header", "headers", "body", "payload",
]);

export function fingerprintText(value, salt = "") {
  return "fp_" + crypto.createHash("sha256").update(salt + value).digest("hex").slice(0, 16);
}

export function findForbiddenKeys(value, path = "") {
  const found = [];
  if (Array.isArray(value)) {
    value.forEach((item, index) => found.push(...findForbiddenKeys(item, `${path}[${index}]`)));
  } else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      const childPath = path ? `${path}.${key}` : key;
      if (FORBIDDEN_FIELD_NAMES.has(key.toLowerCase())) found.push(childPath);
      found.push(...findForbiddenKeys(child, childPath));
    }
  }
  return found;
}

export function assertMetadataOnly(event) {
  if (event.payload_policy !== "metadata_only") throw new Error("meter events must set payload_policy=metadata_only");
  const forbidden = findForbiddenKeys(event);
  if (forbidden.length) throw new Error(`forbidden payload fields in meter event: ${forbidden.join(", ")}`);
}

export class LocalMeterWriter {
  constructor(path) {
    this.path = path;
  }
  writeEvent(event) {
    assertMetadataOnly(event);
    fs.appendFileSync(this.path, JSON.stringify(event) + "\n", "utf8");
  }
}

function usageValue(response, ...names) {
  let current = response?.usage;
  for (const name of names) current = current?.[name];
  return Number(current ?? 0);
}

export async function meteredCall({ routeId, model, writer, provider = "openai", environment = "production", batchable = false, qualitySignal = "unknown", templateFingerprint, toolSchemaFingerprint, call }) {
  const observedAt = new Date().toISOString();
  const started = performance.now();
  let status = "success";
  let errorType;
  let response;
  try {
    response = await call();
    return response;
  } catch (error) {
    status = error?.name === "TimeoutError" ? "timeout" : "error";
    errorType = error?.name ?? "Error";
    throw error;
  } finally {
    const latencyMs = performance.now() - started;
    const event = {
      schema_version: "meter_event_v1",
      observed_at: observedAt,
      route_id: routeId,
      provider,
      model,
      request_id_hash: fingerprintText(`${observedAt}:${routeId}:${model}:${latencyMs}`),
      environment,
      input_tokens: usageValue(response, "prompt_tokens") || usageValue(response, "input_tokens"),
      cached_input_tokens: usageValue(response, "prompt_tokens_details", "cached_tokens") || usageValue(response, "input_tokens_details", "cached_tokens"),
      output_tokens: usageValue(response, "completion_tokens") || usageValue(response, "output_tokens"),
      estimated_cost_usd: 0,
      latency_ms: Math.round(latencyMs * 1000) / 1000,
      status: status,
      error_type: errorType,
      retry_count: 0,
      fallback_used: false,
      streaming: false,
      batchable,
      quality_signal: qualitySignal,
      template_fingerprint: templateFingerprint,
      tool_schema_fingerprint: toolSchemaFingerprint,
      payload_policy: "metadata_only",
    };
    writer.writeEvent(Object.fromEntries(Object.entries(event).filter(([, value]) => value !== undefined)));
  }
}

// Freya Bank's statement services, as a mock on Cloudflare Workers. Stateless: every answer comes from the bank's own test data
// (test-customers.json, copied next to this file at deploy time), looked up as the pack's test-customers.md says. Nothing is made up.
//
//   POST <any prefix>/<service>     e.g. /voice/v1/cards.list      body {"data": {...}, "call": {...}}
//   GET  /health
import pack from "./test-customers.json";

const CORS = { "Access-Control-Allow-Origin": "*" };
const json = (body, status = 200) => Response.json(body, { status, headers: CORS });
const text = (v) => (v === undefined || v === null ? "" : String(v).trim());
// the panel's "Test API Request" button sends variables unfilled, e.g. "{{customerNumber}}"
const isTemplate = (v) => typeof v === "string" && (v.startsWith("{{") || v.startsWith("%7B%7B"));

// where each service's answer is filed, and what it answers when there is none (service contract, sections 4 and 6)
const SERVICES = {
  "cards.list": { by: "customer", missing: [404, "FB_IVR_CHANNEL_102", "WARNING", "Müşteriye ait geçerli kart bilgisi bulunamadı."] },
  "cards.balance": { by: "card", missing: [404, "FB_IVR_CHANNEL_120", "WARNING", "Kart bakiye servisi hatası: kart bulunamadı"] },
  "statement.week.get": { by: "card", missing: [404, "FB_IVR_CHANNEL_121", "WARNING", "Kart bulunamadı"] },
  "statement.week.decide": { by: "card", week: true },
  "statement.week.change": { by: "card", week: true },
  "contact.email.get": { by: "customer" },
  "statement.pdf.send": { by: "customer", missing: [404, "FB_IVR_CHANNEL_107", "WARNING", "Pdf dokümanı bulunamadı"] },
};

const byCustomer = {};
const byCard = {};
for (const c of pack.customers) {
  byCustomer[text(c.customerNo)] = c.services;
  for (const [service, spec] of Object.entries(SERVICES)) {
    if (spec.by !== "card") continue;
    for (const [card, entry] of Object.entries(c.services[service] || {})) (byCard[card] = byCard[card] || {})[service] = entry;
  }
}

function guid() {
  return [...crypto.getRandomValues(new Uint8Array(16))].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function error(status, code, type, message) {
  const id = guid();
  const rootCause = status === 404 ? "com.freyabank.ivrgateway.ivrchannel.rest.exception.NotFoundException" : "InvalidArgumentsException";
  return json({ result: { guid: id, returnCode: code, messageText: message, code, message, type, details: { guid: id, rootCause, errorOrigin: "ivr-gateway-test:ivr-channel-v0" } } }, status);
}
const invalid = (message) => error(400, "INVALID_ARGUMENTS_ERROR", "ERROR", message);

function find(service, spec, data) {
  if (spec.by === "customer") return (byCustomer[text(data.customerNo)] || {})[service];
  const entry = (byCard[text(data.cardNumber)] || {})[service];
  return spec.week ? (entry || {})[text(data.newStatementWeek)] : entry;
}

async function serve(service, request) {
  const spec = SERVICES[service];
  let body;
  try { body = await request.json(); } catch { body = null; }
  const data = (body && typeof body.data === "object" && body.data) || {};
  const key = spec.by === "customer" ? "customerNo" : "cardNumber";
  if (isTemplate(data[key])) {                         // an unfilled test request: a valid record, so the panel's test button shows the shape
    const first = pack.customers[0].services[service];
    const sample = spec.by === "customer" ? first : Object.values(first)[0];
    const entry = spec.week ? Object.values(sample)[0] : sample;
    return json(entry.response, entry.http);
  }
  if (!text(data[key])) return invalid(spec.by === "customer" ? "customer number cannot be empty" : "card number cannot be empty");
  if (spec.week && !text(data.newStatementWeek)) return invalid("newStatementWeek cannot be empty");
  const entry = find(service, spec, data);
  if (!entry || entry.http === undefined) {
    return spec.missing ? error(...spec.missing) : invalid("no record for the given arguments");
  }
  if (entry.delaySeconds) await new Promise((done) => setTimeout(done, Number(entry.delaySeconds) * 1000));
  return json(entry.response, entry.http);
}

export default {
  async fetch(request) {
    const url = new URL(request.url);
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: { ...CORS, "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "*" } });
    }
    if (request.method === "GET" && url.pathname === "/health") return json({ status: "ok", customers: pack.customers.length });
    const service = url.pathname.split("/").filter(Boolean).pop() || "";
    if (request.method === "POST" && SERVICES[service]) {
      try { return await serve(service, request); } catch (e) { return error(500, "FBE00099", "ERROR", "Teknik hata: ABORTED: "); }
    }
    return json({ error: "not found", services: Object.keys(SERVICES).map((s) => "POST /voice/v1/" + s) }, 404);
  },
};

// A mock of the bank's services on Cloudflare Workers. Generic part: routing, the per-customer ledger (a Durable Object, so reads see
// every write), and the three endpoints the builder's test runner uses. The bank's rules live in handlers.js and customers.json:
// fill those from the service contract and the test customers.
//
//   GET  /_health            -> {"ok": true}
//   GET  /_ledger/<id>       -> {"calls": [{"tool", "args", "result"}], "state": {...}}   what the agent did to this customer
//   POST /_reset/<id>        -> clears the ledger of that customer
//   POST <a tool path>       -> handlers[path]; the call, its result and the state patch are recorded under body.customer_id
import customers from "./customers.json";
import { handlers } from "./handlers.js";

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "access-control-allow-origin": "*" } });

export class Ledger {
  constructor(state) { this.state = state; }
  async fetch(request) {
    const path = new URL(request.url).pathname;
    let data = (await this.state.storage.get("data")) || { calls: [], state: {} };
    if (path === "/reset") { await this.state.storage.delete("data"); return json({ ok: true }); }
    if (path === "/record") {
      const { call, state } = await request.json();
      data.calls.push(call);
      Object.assign(data.state, state || {});
      await this.state.storage.put("data", data);
    }
    return json(data);
  }
}

const stub = (env, id) => env.LEDGER.get(env.LEDGER.idFromName(String(id)));
const ask = (env, id, path, body) => stub(env, id).fetch("https://ledger" + path, { method: body ? "POST" : "GET", body: body ? JSON.stringify(body) : undefined }).then((r) => r.json());

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const parts = url.pathname.split("/").filter(Boolean);
    if (request.method === "OPTIONS") return json({});
    if (url.pathname === "/_health") return json({ ok: true });
    if (parts[0] === "_ledger" && parts[1]) return json(await ask(env, parts[1], "/get"));
    if (parts[0] === "_reset" && parts[1]) return json(await ask(env, parts[1], "/reset", {}));
    const handler = handlers[url.pathname];
    if (!handler) return json({ ok: false, error: "unknown route " + url.pathname }, 404);
    const body = request.method === "POST" ? await request.json().catch(() => ({})) : Object.fromEntries(url.searchParams);
    // the customer's id: the field the contract uses for it (add its name here), or a header
    const id = ["customerNumber", "customer_number", "customer_id", "customerId"].map((k) => body[k]).find((v) => v) || request.headers.get("x-customer-id");
    if (!id) return json({ ok: false, error: "customer id is required" }, 400);
    const ledger = await ask(env, id, "/get");
    // handler({body, customer, ledger}) -> {status?, result, state?}: result goes back to the agent, state is merged into the ledger's state
    const out = await handler({ body, customer: customers[id] || null, ledger, env });
    await ask(env, id, "/record", { call: { tool: out.tool || url.pathname.split("/").pop(), args: body, result: out.result }, state: out.state });
    return json(out.result, out.status || 200);
  },
};

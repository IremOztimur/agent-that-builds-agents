# The bank's mock (Cloudflare Workers)

The final case asks for a mock of the bank's services, written from the service contract and the test customers, deployed before the builder runs.
This is a generic starting point: routing, a per-customer ledger that is consistent (a Durable Object), and the endpoints the builder's test runner reads.

    cd mock
    npx wrangler login                       # once
    # fill in handlers.js (one handler per contract route) and customers.json (the test customers, keyed by the id the calls carry)
    npx wrangler deploy                      # prints https://bank-mock.<subdomain>.workers.dev  -> the mock url
    curl https://bank-mock.<subdomain>.workers.dev/_health

Run the builder with that URL: `python3 builder/build.py <case folder> <mock url> 2>&1 | tee traces/final.log`.

What the builder's test runner needs from the mock (already in `worker.js`):
- `GET /_ledger/<id>` returns `{"calls": [{"tool", "args", "result"}], "state": {...}}`: every call the agent made for that customer, and the facts the handlers kept.
- `POST /_reset/<id>` clears one customer between rounds.
- The id is the call's customer number (`customerNumber`, `customer_number`, `customer_id` or `customerId` in the body, or an `x-customer-id` header). If the contract names it differently, add the name to the list in `worker.js`.

Keep the mock up until the results are out: the hidden customers' tool calls reach it.

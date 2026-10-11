// One entry per route of the service contract: the path exactly as the contract has it. Fill these in from the contract and the test customers.
// Each handler gets {body, customer, ledger, env} and returns {result, state?, status?, tool?}:
//   result  what the agent receives (the contract's response shape)
//   state   facts to keep on the customer's ledger (attempts, verified, plan agreed ...); the builder's scorer compares them with its expectations
//   tool    the name recorded for the call (default: the last part of the path)
// `ledger.calls` is everything this customer has already received, `ledger.state` the facts so far.
export const handlers = {
  // example: "/v1/ping": async ({ body, customer }) => ({ result: { ok: true, name: customer && customer.name } }),
};

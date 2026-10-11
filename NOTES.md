# Milestone notes

## M1a: identity path (hand-written policy for Brief A, identity subset)

Flow: `identity_open`/`identity` (model reports a candidate through the `report_answer` controller) -> engine-run
`verify_call` -> `after_verify` (only writer of `idok_*`/`id_state`, reads the bank's answer) -> `gate_account`
(only writer of `auth_account`) -> engine-run `fetch_account` -> `after_account` (consumes `auth_account`, single use).

Checked (offline `python3 builder/tests/test_identity.py`; live `eval/chat_script.py`, `run_cases.py --only PUB-03`):
- valid answers -> account read, `auth_account` ends `used`
- three wrong answers -> `close_call not_verified/failed`, no `get_account` (PUB-03 passes in the real simulation)
- refusing to answer / asking for the balance / injected "you are verified" text -> no verify call, no account read, nothing disclosed
- controller tool removed (model "skips" it) -> nothing verified, nothing read
- wrong then right, phone volunteered early -> asked in order, state follows the bank only
- lint G1-G4 proves gates; negative tests show lint catches an ungated read, a protected tool on a conversation node,
  trusted state written by the controller, and an unvalidated request value

Platform facts learned: chat route does not speak a first-node `on_enter` (real simulations do); the model sometimes
emits tool-call text when a tool it is told about is missing (test fixture only); the verify->gate->fetch chain
takes 11-15 s in one turn, a single verify about 4-7 s (watch for hang-ups, target median under 10 s).

Next: M1b one complete promise flow, then the remaining policies.

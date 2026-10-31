# provider_failover

Does a model-call arm still answer when its primary provider fails? Offline: fake providers, no model, no network, no key, $0.

- **Cases** (`cases.json`, 30): the primary fails with a billing or credit error ("credit balance is too low", an insufficient
  balance, a payment-required status), a quota or rate limit, a timeout, or an outage (502, 503, 504, 529, 500), or does not fail.
  The secondary is healthy, or also down. The wordings are the vendors' own error texts. Two cases are not failures to route around
  (a bad request, a bad key): they must be raised, not hidden by asking another provider.
- **Pass**: the call is answered by the healthy provider, or by the primary when it is healthy, or it fails with a clear error when
  none is healthy.
- **Arms**: `multi_provider` (the router, given the secondary's model as its fallback) against `single_provider` (the primary alone,
  what a consumer wired to one vendor gets).
- **Run the free stage**: `PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run provider_failover --impl multi_provider`
  (add `--record` to log it).
- Why: production Quest AI stopped answering on 2026-10-22 when the Anthropic balance ran out, because the router only stepped down
  on quota and rate-limit errors. `hubofhubs/models/outage.py` and `router.py` now treat billing, timeout and outage errors as
  reasons to ask the next configured model.

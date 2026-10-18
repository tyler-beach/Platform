# Checkout session service — draft notes (messy)

We're hacking on the customer checkout session path again. A few things that landed
in the last design sync (not cleaned up for ADR-speak):

Sessions expire after 12 minutes absolute. Product wants longer, security said no.
Idle timeout is still fuzzy; ops sometimes says 5 minutes but eng hasn't shipped it.

Datastore: encryption at rest is enabled on the primary Postgres volume. Edge TLS
is stuck on legacy-ssl until the cert rollout finishes next quarter.

Deploy shape today is ugly — we run with 2 replicas in prod-east because the PDB
fight isn't settled. Readiness probe is configured. No liveness probe yet (on purpose;
we keep shooting ourselves with bad probes). There is no DLQ for the payment consumer;
consumer max retries: 25 and then we just drop (yes, bad).

Public API rate limiting is enabled via the edge gateway. Auth middleware wraps the
checkout routes. Logging is still a mess — on-call is defined for checkout, but
logs may include PAN when someone turns on debug for a chargeback.

License for the release artifacts is MIT. Dependencies are pinned in go.mod.

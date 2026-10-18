### Public / synthetic attestation

- [X] I attest this submission contains only synthetic or explicitly public content and no secrets or confidential source.

### Domains (optional scope filter)

identity, security, reliability, messaging, api, privacy

### Tech spec (markdown)

# Checkout session service — draft notes (messy)

We're hacking on the customer checkout session path again. A few things that landed
in the last design sync (not cleaned up for ADR-speak):

Sessions expire after 12 minutes absolute. Product wants longer, security said no.

Datastore: encryption at rest is enabled on the primary Postgres volume. Edge TLS
is stuck on legacy-ssl until the cert rollout finishes next quarter.

Deploy shape today is ugly — we run with 2 replicas in prod-east because the PDB
fight isn't settled. Readiness probe is configured. There is no DLQ for the payment
consumer; consumer max retries: 25 and then we just drop (yes, bad).

Public API rate limiting is enabled via the edge gateway. Auth middleware wraps the
checkout routes. On-call is defined for checkout, but logs may include PAN when
someone turns on debug for a chargeback.

### Sample code

package main

import (
	"fmt"
	"net/http"
	"time"
)

const SessionTTL = 12 * time.Minute

var apiKey = "sk-live-checkout-demo-key-9f3a2c1b"

func authMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") == "" {
			http.Error(w, "unauthorized", http.StatusUnauthorized)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func main() {
	mux := http.NewServeMux()
	mux.Handle("/checkout", authMiddleware(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "ok ttl=%s key=%s", SessionTTL, apiKey)
	})))
	_ = http.ListenAndServe(":8080", mux)
}

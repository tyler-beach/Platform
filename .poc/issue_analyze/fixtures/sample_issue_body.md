### Public / synthetic attestation

- [X] I attest this submission contains only synthetic or explicitly public content and no secrets or confidential source.

### Domains (optional scope filter)

identity, security, reliability

### Full package JSON (preferred)

```pathfinder-package
{
  "schema_version": "pathfinder-evidence-package-v1",
  "package_id": "issue-fixture-session-service",
  "scope": {
    "domains": ["identity", "security", "reliability"]
  },
  "tech_spec": {
    "artifact_id": "tech_spec",
    "path": "issue/tech-spec.md",
    "revision": "sha256:placeholder",
    "sha256": "placeholder",
    "content": "# Synthetic session service\n\nSessions expire after 12 minutes.\nEncryption at rest enabled.\nReplicas: 2.\n"
  },
  "observations": [
    {
      "evidence_id": "EV-TTL",
      "predicate": "session.ttl_seconds",
      "subject": "session",
      "value": 720,
      "artifact_id": "tech_spec",
      "revision": "sha256:placeholder",
      "path": "issue/tech-spec.md",
      "source_sha256": "placeholder",
      "locator": {"kind": "tech_spec_claim", "value": "session.ttl_seconds"}
    },
    {
      "evidence_id": "EV-ENC",
      "predicate": "security.encryption_at_rest.enabled",
      "subject": "datastore",
      "value": true,
      "artifact_id": "tech_spec",
      "revision": "sha256:placeholder",
      "path": "issue/tech-spec.md",
      "source_sha256": "placeholder",
      "locator": {"kind": "tech_spec_claim", "value": "security.encryption_at_rest.enabled"}
    },
    {
      "evidence_id": "EV-REP",
      "predicate": "kubernetes.deployment.replicas",
      "subject": "workload",
      "value": 2,
      "artifact_id": "tech_spec",
      "revision": "sha256:placeholder",
      "path": "issue/tech-spec.md",
      "source_sha256": "placeholder",
      "locator": {"kind": "tech_spec_claim", "value": "kubernetes.deployment.replicas"}
    }
  ]
}
```

# Synthetic placeholder for ADR-005; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-005" {
  source = "live-system-not-connected"
}

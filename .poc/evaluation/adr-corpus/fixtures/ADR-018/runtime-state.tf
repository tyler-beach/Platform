# Synthetic placeholder for ADR-018; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-018" {
  source = "live-system-not-connected"
}

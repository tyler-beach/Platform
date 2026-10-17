# Synthetic placeholder for ADR-038; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-038" {
  source = "live-system-not-connected"
}

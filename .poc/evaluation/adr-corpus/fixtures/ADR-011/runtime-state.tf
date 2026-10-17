# Synthetic placeholder for ADR-011; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-011" {
  source = "live-system-not-connected"
}

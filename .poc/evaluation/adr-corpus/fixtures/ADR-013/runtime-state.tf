# Synthetic placeholder for ADR-013; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-013" {
  source = "live-system-not-connected"
}

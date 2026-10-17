# Synthetic placeholder for ADR-041; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-041" {
  source = "live-system-not-connected"
}

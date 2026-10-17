# Synthetic placeholder for ADR-045; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-045" {
  source = "live-system-not-connected"
}

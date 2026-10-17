# Synthetic placeholder for ADR-025; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-025" {
  source = "live-system-not-connected"
}

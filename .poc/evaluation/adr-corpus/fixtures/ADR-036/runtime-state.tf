# Synthetic placeholder for ADR-036; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-036" {
  source = "live-system-not-connected"
}

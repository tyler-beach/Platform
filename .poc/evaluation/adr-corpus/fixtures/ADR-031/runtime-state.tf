# Synthetic placeholder for ADR-031; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-031" {
  source = "live-system-not-connected"
}

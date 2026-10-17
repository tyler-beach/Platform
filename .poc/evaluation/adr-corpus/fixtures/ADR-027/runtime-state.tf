# Synthetic placeholder for ADR-027; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-027" {
  source = "live-system-not-connected"
}

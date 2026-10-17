# Synthetic placeholder for ADR-046; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-046" {
  source = "live-system-not-connected"
}

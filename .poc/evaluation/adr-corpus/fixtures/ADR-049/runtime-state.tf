# Synthetic placeholder for ADR-049; no live state is captured.
resource "unavailable_runtime_snapshot" "adr-049" {
  source = "live-system-not-connected"
}

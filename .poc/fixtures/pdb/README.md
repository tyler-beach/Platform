# PDB collector fixtures

The collector tests create temporary Kubernetes YAML bundles so each case can isolate workload labels, namespaces, PDB selectors, malformed input, and missing evidence. These are synthetic manifests, not evidence from a live cluster.

The collector only supports a negative observation when it can parse the complete supplied YAML inventory and find the named workload. The inventory boundary must be supplied by the caller; manifests omitted from that directory and live cluster state are outside the conclusion. A production collector must pin repository revision, define its scan roots, and report excluded/ignored files explicitly.

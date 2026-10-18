package predicates

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
)

const RegistryVersion = "predicate-registry-v2"

const CollectorStructuredPackage = "structured_package"

type Meta struct {
	ValueType       string   `json:"value_type"`
	Collector       string   `json:"collector"`
	AlsoCollectors  []string `json:"also_collectors"`
	Description     string   `json:"description"`
	CompatibleKinds []string `json:"compatible_kinds"`
	Domains         []string `json:"domains"`
}

type Registry struct {
	Predicates map[string]Meta
}

var builtin = map[string]Meta{
	"session.ttl_seconds": {
		ValueType: "number", Collector: "config_json",
		Description: "Configured or observed session lifetime in seconds",
		CompatibleKinds: []string{"numeric_max"},
	},
	"kubernetes.pod_disruption_budget.present": {
		ValueType: "boolean", Collector: "kubernetes_manifest",
		Description: "Whether a PDB in the supplied inventory selects the workload",
		CompatibleKinds: []string{"resource_present", "boolean_required"},
	},
	"security.encryption_at_rest.enabled": {
		ValueType: "boolean", Collector: "config_json",
		Description: "Whether encryption at rest is enabled in pinned config",
		CompatibleKinds: []string{"boolean_required"},
	},
	"security.tls_policy.id": {
		ValueType: "string", Collector: "config_json",
		Description: "Configured TLS policy identifier",
		CompatibleKinds: []string{"set_membership"},
	},
}

// Load merges builtins with predicates.json from catalogDir.
func Load(catalogDir string) (*Registry, error) {
	merged := map[string]Meta{}
	for k, v := range builtin {
		cp := v
		cp.CompatibleKinds = append([]string{}, v.CompatibleKinds...)
		merged[k] = cp
	}
	path := filepath.Join(catalogDir, "predicates.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return &Registry{Predicates: merged}, nil
		}
		return nil, err
	}
	var payload struct {
		Predicates map[string]Meta `json:"predicates"`
	}
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, err
	}
	for name, meta := range payload.Predicates {
		current := merged[name]
		kinds := uniqueStrings(append(current.CompatibleKinds, meta.CompatibleKinds...))
		domains := uniqueStrings(append(current.Domains, meta.Domains...))
		collector := meta.Collector
		if collector == "" {
			collector = current.Collector
		}
		if _, isBuiltin := builtin[name]; isBuiltin && meta.Collector == CollectorStructuredPackage && current.Collector != "" {
			collector = current.Collector
		}
		also := uniqueStrings(append(current.AlsoCollectors, meta.AlsoCollectors...))
		if collector == "config_json" || collector == "kubernetes_manifest" {
			also = uniqueStrings(append(also, CollectorStructuredPackage))
		}
		if len(domains) == 0 {
			domains = meta.Domains
		}
		merged[name] = Meta{
			ValueType:       firstNonEmpty(meta.ValueType, current.ValueType),
			Collector:       collector,
			AlsoCollectors:  also,
			Description:     firstNonEmpty(meta.Description, current.Description),
			CompatibleKinds: kinds,
			Domains:         domains,
		}
	}
	return &Registry{Predicates: merged}, nil
}

func (r *Registry) Get(predicate string) (Meta, error) {
	meta, ok := r.Predicates[predicate]
	if !ok {
		return Meta{}, fmt.Errorf("unknown predicate %q", predicate)
	}
	return meta, nil
}

func (r *Registry) CollectorsFor(predicate string) ([]string, error) {
	meta, err := r.Get(predicate)
	if err != nil {
		return nil, err
	}
	out := []string{meta.Collector}
	out = append(out, meta.AlsoCollectors...)
	return uniqueStrings(out), nil
}

func (r *Registry) AssertsCompatible(kind, predicate string) error {
	meta, err := r.Get(predicate)
	if err != nil {
		return err
	}
	for _, k := range meta.CompatibleKinds {
		if k == kind {
			return nil
		}
	}
	return fmt.Errorf("kind %q incompatible with predicate %q", kind, predicate)
}

func firstNonEmpty(a, b string) string {
	if a != "" {
		return a
	}
	return b
}

func uniqueStrings(in []string) []string {
	seen := map[string]struct{}{}
	var out []string
	for _, s := range in {
		if s == "" {
			continue
		}
		if _, ok := seen[s]; ok {
			continue
		}
		seen[s] = struct{}{}
		out = append(out, s)
	}
	sort.Strings(out)
	return out
}

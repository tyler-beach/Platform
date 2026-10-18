package catalog

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const (
	ModeSynthetic = "synthetic"
	ModeReal      = "real"
)

// Identity names the catalog pack used for an evaluation.
type Identity struct {
	Mode           string `json:"mode"`
	CatalogID      string `json:"catalog_id"`
	Version        string `json:"version"`
	ManifestSHA256 string `json:"manifest_sha256"`
	Path           string `json:"path"`
	Size           int    `json:"requirement_count,omitempty"`
}

// ResolveMode returns synthetic|real from flag/env (empty → real prototype pack).
func ResolveMode(flagOrEnv string) (string, error) {
	mode := strings.ToLower(strings.TrimSpace(flagOrEnv))
	if mode == "" {
		mode = strings.ToLower(strings.TrimSpace(os.Getenv("PATHFINDER_CATALOG")))
	}
	if mode == "" {
		return ModeReal, nil
	}
	switch mode {
	case ModeSynthetic, ModeReal:
		return mode, nil
	default:
		return "", fmt.Errorf("unsupported catalog mode %q (want synthetic|real)", mode)
	}
}

// ResolveDir returns the catalog directory for a mode under repoRoot.
func ResolveDir(repoRoot, mode string) (string, error) {
	resolved, err := ResolveMode(mode)
	if err != nil {
		return "", err
	}
	switch resolved {
	case ModeReal:
		return filepath.Join(repoRoot, "data", "adr_catalog"), nil
	default:
		return DefaultDir(repoRoot), nil
	}
}

// LoadIdentity reads catalog_manifest.json when present, else fingerprints requirements.jsonl.
func LoadIdentity(catalogDir, mode string) (Identity, error) {
	resolved := strings.ToLower(strings.TrimSpace(mode))
	if resolved == "" {
		slash := filepath.ToSlash(catalogDir)
		switch {
		case strings.Contains(slash, ".poc/requirement_catalog"):
			resolved = ModeSynthetic
		case strings.Contains(slash, "data/adr_catalog"):
			resolved = ModeReal
		default:
			var err error
			resolved, err = ResolveMode("")
			if err != nil {
				return Identity{}, err
			}
		}
	} else {
		var err error
		resolved, err = ResolveMode(resolved)
		if err != nil {
			return Identity{}, err
		}
	}
	id := Identity{Mode: resolved, Path: catalogDir}
	manifestPath := filepath.Join(catalogDir, "catalog_manifest.json")
	if raw, err := os.ReadFile(manifestPath); err == nil {
		var m struct {
			CatalogID        string `json:"catalog_id"`
			Version          string `json:"version"`
			ManifestSHA256   string `json:"manifest_sha256"`
			RequirementCount int    `json:"requirement_count"`
			CatalogMode      string `json:"catalog_mode"`
		}
		if err := json.Unmarshal(raw, &m); err != nil {
			return Identity{}, fmt.Errorf("catalog_manifest.json: %w", err)
		}
		id.CatalogID = m.CatalogID
		id.Version = m.Version
		id.ManifestSHA256 = m.ManifestSHA256
		id.Size = m.RequirementCount
		if m.CatalogMode != "" {
			id.Mode = m.CatalogMode
		}
		return id, nil
	}
	reqPath := filepath.Join(catalogDir, "requirements.jsonl")
	raw, err := os.ReadFile(reqPath)
	if err != nil {
		return Identity{}, err
	}
	sum := sha256.Sum256(raw)
	id.CatalogID = "synthetic-requirement-catalog"
	if resolved == ModeReal {
		id.CatalogID = "real-adr-catalog"
	}
	id.Version = "unmanifested"
	id.ManifestSHA256 = hex.EncodeToString(sum[:])
	return id, nil
}

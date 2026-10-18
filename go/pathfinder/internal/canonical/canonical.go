package canonical

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
)

// JSON returns a deterministic JSON encoding with sorted object keys,
// matching Python json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False).
func JSON(value any) (string, error) {
	normalized, err := normalize(value)
	if err != nil {
		return "", err
	}
	b, err := json.Marshal(normalized)
	if err != nil {
		return "", err
	}
	return string(b), nil
}

// Fingerprint returns the lowercase SHA-256 hex digest of Canonical JSON.
func Fingerprint(value any) (string, error) {
	s, err := JSON(value)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256([]byte(s))
	return hex.EncodeToString(sum[:]), nil
}

func normalize(value any) (any, error) {
	switch v := value.(type) {
	case nil:
		return nil, nil
	case bool, string:
		return v, nil
	case json.Number:
		return v, nil
	case int:
		return float64(v), nil
	case int8:
		return float64(v), nil
	case int16:
		return float64(v), nil
	case int32:
		return float64(v), nil
	case int64:
		return float64(v), nil
	case uint:
		return float64(v), nil
	case uint8:
		return float64(v), nil
	case uint16:
		return float64(v), nil
	case uint32:
		return float64(v), nil
	case uint64:
		return float64(v), nil
	case float32:
		return float64(v), nil
	case float64:
		return v, nil
	case []any:
		out := make([]any, len(v))
		for i, item := range v {
			n, err := normalize(item)
			if err != nil {
				return nil, err
			}
			out[i] = n
		}
		return out, nil
	case map[string]any:
		// encoding/json.Marshal sorts map keys.
		out := make(map[string]any, len(v))
		for k, item := range v {
			n, err := normalize(item)
			if err != nil {
				return nil, err
			}
			out[k] = n
		}
		return out, nil
	default:
		// Re-encode structs via JSON round-trip for stable maps.
		b, err := json.Marshal(v)
		if err != nil {
			return nil, fmt.Errorf("canonical: unsupported type %T: %w", value, err)
		}
		var decoded any
		if err := json.Unmarshal(b, &decoded); err != nil {
			return nil, err
		}
		return normalize(decoded)
	}
}

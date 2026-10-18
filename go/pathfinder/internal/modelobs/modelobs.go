// Package modelobs reserves an optional model-backed observation path.
// It is disabled by default and MUST NOT invent observations without an
// explicit enable flag and credentials (fail closed).
package modelobs

import (
	"fmt"
	"os"
	"strings"
)

const EnableEnv = "PATHFINDER_ENABLE_MODEL_EXTRACT"

// Enabled reports whether model-backed extraction was explicitly requested.
func Enabled() bool {
	v := strings.ToLower(strings.TrimSpace(os.Getenv(EnableEnv)))
	return v == "1" || v == "true" || v == "yes"
}

// Augment is a fail-closed stub. When disabled it returns the input unchanged.
// When enabled without a configured provider it returns an error rather than
// fabricating observations.
func Augment(observations []any) ([]any, error) {
	if !Enabled() {
		return observations, nil
	}
	if strings.TrimSpace(os.Getenv("ANTHROPIC_API_KEY")) == "" {
		return nil, fmt.Errorf("model extract enabled (%s) but ANTHROPIC_API_KEY is not set", EnableEnv)
	}
	return nil, fmt.Errorf("model-backed observation extraction is not implemented in this prototype build; disable %s or supply observations explicitly", EnableEnv)
}

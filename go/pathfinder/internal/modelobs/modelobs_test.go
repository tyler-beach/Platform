package modelobs_test

import (
	"testing"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/modelobs"
)

func TestAugmentNoopWhenDisabled(t *testing.T) {
	t.Setenv(modelobs.EnableEnv, "")
	in := []any{map[string]any{"predicate": "session.ttl_seconds"}}
	out, err := modelobs.Augment(in)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 1 {
		t.Fatalf("len=%d", len(out))
	}
}

func TestAugmentFailsClosedWhenEnabledWithoutKey(t *testing.T) {
	t.Setenv(modelobs.EnableEnv, "1")
	t.Setenv("ANTHROPIC_API_KEY", "")
	_, err := modelobs.Augment(nil)
	if err == nil {
		t.Fatal("expected error")
	}
}

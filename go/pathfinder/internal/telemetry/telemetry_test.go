package telemetry

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"sync/atomic"
	"testing"
	"time"

	"go.opentelemetry.io/otel"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	"go.opentelemetry.io/otel/sdk/trace/tracetest"
)

func TestNormalizeStageBoundsCardinality(t *testing.T) {
	if got := NormalizeStage("evaluation"); got != "evaluation" {
		t.Fatalf("known stage = %q", got)
	}
	if got := NormalizeStage("issue-1234-user-controlled"); got != "other" {
		t.Fatalf("unknown stage = %q", got)
	}
}

func TestNormalizeOutcomeBoundsCardinality(t *testing.T) {
	if got := NormalizeOutcome("ok"); got != "ok" {
		t.Fatalf("known outcome = %q", got)
	}
	if got := NormalizeOutcome("error: issue body contains secrets"); got != "error" {
		t.Fatalf("unknown outcome = %q", got)
	}
	if got := NormalizeOutcome("skipped"); got != "skipped" {
		t.Fatalf("skipped outcome = %q", got)
	}
}

func TestStageSnapshotContainsRealBoundedMeasurementsWithoutEndpoint(t *testing.T) {
	t.Setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
	runtime := Initialize(context.Background(), "test-service")
	ctx, finish := runtime.Stage(context.Background(), "evaluation")
	_ = ctx
	finish(nil)
	ctx, finish = runtime.Stage(context.Background(), "evaluation")
	_ = ctx
	finish(errors.New("private input must not enter telemetry"))
	ctx, finish = runtime.Stage(context.Background(), "untrusted-stage-name")
	_ = ctx
	finish(ErrSkipped)
	snapshot := runtime.StageSnapshot()
	if len(snapshot) != len(stages) {
		t.Fatalf("snapshot stage cardinality = %d", len(snapshot))
	}
	got := snapshot["evaluation"]
	if got.Runs != 2 || got.Errors != 1 || got.Skipped != 0 || got.DurationTotalNS <= 0 {
		t.Fatalf("evaluation telemetry = %+v", got)
	}
	other := snapshot["other"]
	if other.Runs != 1 || other.Skipped != 1 {
		t.Fatalf("other telemetry = %+v", other)
	}
	if err := runtime.Shutdown(context.Background()); err != nil {
		t.Fatal(err)
	}
}

func TestNoEndpointUsesNoopAndStageSpansCarryNoAttributes(t *testing.T) {
	t.Setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
	t.Setenv("OTEL_EXPORTER_OTLP_HEADERS", "authorization=do-not-inherit")
	exporter := tracetest.NewInMemoryExporter()
	provider := sdktrace.NewTracerProvider(sdktrace.WithSyncer(exporter))
	otel.SetTracerProvider(provider)
	runtime := Initialize(context.Background(), "test-service")
	if got := os.Getenv("OTEL_EXPORTER_OTLP_HEADERS"); got != "" {
		t.Fatalf("OTLP secret header remains in child-process environment: %q", got)
	}
	ctx, finish := runtime.Stage(context.Background(), "issue-secret-123")
	runtime.RecordStage(ctx, "evaluation", "ok", time.Millisecond)
	runtime.RecordJob(ctx, "ok")
	finish(ErrSkipped)
	if err := runtime.Shutdown(context.Background()); err != nil {
		t.Fatalf("Shutdown() error = %v", err)
	}
	spans := exporter.GetSpans()
	if len(spans) != 1 || spans[0].Name != "pathfinder.stage.other" {
		t.Fatalf("unexpected spans: %+v", spans)
	}
	if len(spans[0].Attributes) != 0 {
		t.Fatalf("stage span contains attributes: %+v", spans[0].Attributes)
	}
	if spans[0].Status.Code.String() != "Unset" {
		t.Fatalf("skipped span should not be marked as an error: %+v", spans[0].Status)
	}
}

func TestExporterTimeoutDoesNotBlockShutdown(t *testing.T) {
	oldDeadline := exportDeadline
	exportDeadline = 100 * time.Millisecond
	t.Cleanup(func() { exportDeadline = oldDeadline })
	var requests atomic.Int32
	release := make(chan struct{})
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests.Add(1)
		<-release
	}))
	defer func() {
		close(release)
		server.Close()
	}()
	t.Setenv("OTEL_EXPORTER_OTLP_ENDPOINT", server.URL)
	t.Setenv("OTEL_EXPORTER_OTLP_HEADERS", "")
	runtime := Initialize(context.Background(), "test-timeout")
	ctx, span := runtime.Start(context.Background(), "pathfinder.analysis")
	runtime.RecordJob(ctx, "ok")
	span.End()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 500*time.Millisecond)
	defer cancel()
	started := time.Now()
	_ = runtime.Shutdown(shutdownCtx)
	if elapsed := time.Since(started); elapsed > 750*time.Millisecond {
		t.Fatalf("export shutdown exceeded bound: %s", elapsed)
	}
	if requests.Load() == 0 {
		t.Fatal("expected OTLP exporter to attempt at least one request")
	}
}

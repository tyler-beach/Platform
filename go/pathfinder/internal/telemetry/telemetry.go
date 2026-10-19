// Package telemetry configures optional, privacy-preserving OpenTelemetry export.
package telemetry

import (
	"context"
	"errors"
	"fmt"
	"os"
	"sort"
	"strings"
	"sync"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/exporters/otlp/otlpmetric/otlpmetrichttp"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/metric"
	sdkmetric "go.opentelemetry.io/otel/sdk/metric"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
	"go.opentelemetry.io/otel/trace"
)

var exportDeadline = 3 * time.Second

var ErrSkipped = errors.New("telemetry stage skipped")

var stages = map[string]struct{}{
	"intake": {}, "catalog_load": {}, "package_build": {}, "evaluation": {},
	"report_write": {}, "publication": {}, "ledger": {}, "summary": {}, "other": {},
}

var outcomes = map[string]struct{}{"ok": {}, "error": {}, "skipped": {}}

// Runtime owns providers and bounded-cardinality instruments for one CLI process.
type Runtime struct {
	shutdown func(context.Context) error
	tracer   trace.Tracer
	meter    metric.Meter
	// Instruments are private; caller records only normalized stage/outcome labels.
	stageRuns metric.Int64Counter
	stageSecs metric.Float64Histogram
	jobRuns   metric.Int64Counter
	stageMu   sync.Mutex
	stageData map[string]StageMetric
}

// StageMetric is a privacy-bounded aggregate of the same measurements recorded
// by the OTel instruments. It intentionally contains no run or source identity.
type StageMetric struct {
	Runs            int64 `json:"runs"`
	Errors          int64 `json:"errors"`
	Skipped         int64 `json:"skipped"`
	DurationTotalNS int64 `json:"duration_total_ns"`
	DurationMaxNS   int64 `json:"duration_max_ns"`
}

// Initialize enables OTLP/HTTP only when OTEL_EXPORTER_OTLP_ENDPOINT is configured.
// Invalid exporter configuration disables export and never fails the analysis job.
func Initialize(ctx context.Context, serviceName string) *Runtime {
	// Exporters read standard OTLP headers during construction. Remove the secret
	// before the CLI can spawn helper processes that would inherit its environment.
	defer func() { _ = os.Unsetenv("OTEL_EXPORTER_OTLP_HEADERS") }()
	r := &Runtime{shutdown: func(context.Context) error { return nil }, tracer: otel.Tracer(serviceName), meter: otel.Meter(serviceName), stageData: make(map[string]StageMetric, len(stages))}
	endpoint := strings.TrimSpace(os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"))
	if endpoint == "" {
		return r
	}
	otel.SetErrorHandler(otel.ErrorHandlerFunc(func(error) { safeWarning() }))
	traceExporter, err := otlptracehttp.New(ctx, otlptracehttp.WithTimeout(exportDeadline))
	if err != nil {
		safeWarning()
		return r
	}
	metricExporter, err := otlpmetrichttp.New(ctx, otlpmetrichttp.WithTimeout(exportDeadline))
	if err != nil {
		cleanupCtx, cancel := context.WithTimeout(context.Background(), exportDeadline)
		_ = traceExporter.Shutdown(cleanupCtx)
		cancel()
		safeWarning()
		return r
	}
	res := resource.NewWithAttributes(semconv.SchemaURL, semconv.ServiceName(serviceName))
	tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(traceExporter, sdktrace.WithBatchTimeout(500*time.Millisecond)), sdktrace.WithResource(res))
	mp := sdkmetric.NewMeterProvider(sdkmetric.WithReader(sdkmetric.NewPeriodicReader(metricExporter, sdkmetric.WithInterval(5*time.Second))), sdkmetric.WithResource(res))
	r.tracer = tp.Tracer(serviceName)
	r.meter = mp.Meter(serviceName)
	r.stageRuns, _ = r.meter.Int64Counter("pathfinder.stage.runs")
	r.stageSecs, _ = r.meter.Float64Histogram("pathfinder.stage.duration", metric.WithUnit("s"))
	r.jobRuns, _ = r.meter.Int64Counter("pathfinder.analysis.jobs")
	r.shutdown = func(ctx context.Context) error {
		errs := make(chan error, 2)
		go func() { errs <- mp.Shutdown(ctx) }()
		go func() { errs <- tp.Shutdown(ctx) }()
		var first error
		for i := 0; i < 2; i++ {
			if err := <-errs; err != nil && first == nil {
				first = err
			}
		}
		return first
	}
	r.tracer = tp.Tracer(serviceName)
	return r
}

// Start creates a span with the given fixed operation name. Callers must not add user content.
func (r *Runtime) Start(ctx context.Context, name string) (context.Context, trace.Span) {
	ctx, span := r.tracer.Start(ctx, name)
	return ctx, span
}

func NormalizeStage(name string) string {
	if _, ok := stages[name]; ok {
		return name
	}
	return "other"
}

func ValidStage(name string) bool { _, ok := stages[name]; return ok }

func StageNames() []string {
	names := make([]string, 0, len(stages))
	for name := range stages {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func NormalizeOutcome(outcome string) string {
	if _, ok := outcomes[outcome]; ok {
		return outcome
	}
	return "error"
}

func (r *Runtime) RecordStage(ctx context.Context, name, outcome string, elapsed time.Duration) {
	name, outcome = NormalizeStage(name), NormalizeOutcome(outcome)
	if elapsed < 0 {
		elapsed = 0
	}
	elapsedNS := int64(elapsed)
	if elapsedNS > maxStageMetricValue {
		elapsedNS = maxStageMetricValue
	}
	r.stageMu.Lock()
	current := r.stageData[name]
	if current.Runs < maxStageMetricValue {
		current.Runs++
	}
	if outcome == "error" && current.Errors < maxStageMetricValue {
		current.Errors++
	}
	if outcome == "skipped" && current.Skipped < maxStageMetricValue {
		current.Skipped++
	}
	if elapsedNS > maxStageMetricValue-current.DurationTotalNS {
		current.DurationTotalNS = maxStageMetricValue
	} else {
		current.DurationTotalNS += elapsedNS
	}
	if elapsedNS > current.DurationMaxNS {
		current.DurationMaxNS = elapsedNS
	}
	r.stageData[name] = current
	r.stageMu.Unlock()
	if r.stageRuns == nil {
		return
	}
	attrs := []attribute.KeyValue{attribute.String("stage", NormalizeStage(name)), attribute.String("outcome", NormalizeOutcome(outcome))}
	r.stageRuns.Add(ctx, 1, metric.WithAttributes(attrs...))
	r.stageSecs.Record(ctx, elapsed.Seconds(), metric.WithAttributes(attrs...))
}

const maxStageMetricValue int64 = 1<<53 - 1

// StageSnapshot returns a fresh, fixed-key map suitable for the redacted job ledger.
func (r *Runtime) StageSnapshot() map[string]StageMetric {
	r.stageMu.Lock()
	defer r.stageMu.Unlock()
	snapshot := make(map[string]StageMetric, len(stages))
	for stage := range stages {
		snapshot[stage] = r.stageData[stage]
	}
	return snapshot
}

// Stage starts a bounded-name span and returns a completion function that records
// only an allowlisted outcome and elapsed time, never an error message.
func (r *Runtime) Stage(ctx context.Context, name string) (context.Context, func(error)) {
	name = NormalizeStage(name)
	ctx, span := r.Start(ctx, "pathfinder.stage."+name)
	started := time.Now()
	return ctx, func(err error) {
		outcome := "ok"
		if errors.Is(err, ErrSkipped) {
			outcome = "skipped"
		} else if err != nil {
			outcome = "error"
			span.SetStatus(codes.Error, "stage failed")
		}
		r.RecordStage(ctx, name, outcome, time.Since(started))
		span.End()
	}
}

func (r *Runtime) RecordJob(ctx context.Context, outcome string) {
	if r.jobRuns != nil {
		r.jobRuns.Add(ctx, 1, metric.WithAttributes(attribute.String("outcome", NormalizeOutcome(outcome))))
	}
}

func (r *Runtime) Shutdown(ctx context.Context) error {
	if r.shutdown == nil {
		return nil
	}
	return r.shutdown(ctx)
}

func safeWarning() {
	fmt.Fprintln(os.Stderr, "warning: OpenTelemetry telemetry may be unavailable; details redacted")
}

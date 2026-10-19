package dashboard_test

import (
	"strings"
	"testing"
	"time"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/dashboard"
)

func TestBuildSummaryAggregatesOnlyBoundedOutcomeData(t *testing.T) {
	now := time.Date(2026, 10, 19, 12, 0, 0, 0, time.UTC)
	ledger := strings.Join([]string{
		`{"schema_version":"pathfinder-job-record-v2","job_id":"private-id","issue_number":7,"repository":"org/repo","run_id":"123","ok":true,"aggregate_status":"mixed","outcome_counts":{"supported_deviation":2,"no_deviation_found":1,"inconclusive":1,"not_applicable":0},"recorded_at":"2026-10-19T10:00:00Z"}`,
		`{"schema_version":"pathfinder-job-record-v1","job_id":"legacy","issue_number":8,"ok":false,"recorded_at":"2026-10-19T11:00:00Z"}`,
		`not json at all`,
		`{"schema_version":"pathfinder-job-record-v2","ok":true,"recorded_at":"2026-07-01T00:00:00Z"}`,
	}, "\n")

	summary, err := dashboard.BuildSummary(strings.NewReader(ledger), now, 90)
	if err != nil {
		t.Fatal(err)
	}
	if summary.SchemaVersion != dashboard.SchemaVersion {
		t.Fatalf("schema=%q", summary.SchemaVersion)
	}
	if summary.Totals.Jobs != 2 || summary.Totals.Succeeded != 1 || summary.Totals.Failed != 1 {
		t.Fatalf("totals=%+v", summary.Totals)
	}
	if summary.Totals.Outcomes.SupportedDeviation != 2 || summary.Totals.Outcomes.NoDeviationFound != 1 || summary.Totals.Outcomes.Inconclusive != 1 {
		t.Fatalf("outcomes=%+v", summary.Totals.Outcomes)
	}
	if summary.Totals.AggregateStatuses["mixed"] != 1 {
		t.Fatalf("aggregate statuses=%v", summary.Totals.AggregateStatuses)
	}
	if summary.Totals.AggregateStatuses["other"] != 0 {
		t.Fatalf("aggregate status keys must include bounded zero categories: %v", summary.Totals.AggregateStatuses)
	}
	if summary.RejectedRecords != 1 {
		t.Fatalf("rejected=%d, want 1", summary.RejectedRecords)
	}
	if summary.ModelMetering != "not_metered" {
		t.Fatalf("model metering=%q", summary.ModelMetering)
	}
	encoded, err := dashboard.MarshalSummary(summary)
	if err != nil {
		t.Fatal(err)
	}
	for _, forbidden := range []string{"private-id", "org/repo", "\"issue_number\"", "\"run_id\"", "not json at all"} {
		if strings.Contains(string(encoded), forbidden) {
			t.Errorf("summary leaked %q: %s", forbidden, encoded)
		}
	}
}

func TestBuildSummaryRejectsUnboundedWindowAndMalformedCounts(t *testing.T) {
	if _, err := dashboard.BuildSummary(strings.NewReader(""), time.Now(), 10000); err == nil {
		t.Fatal("expected excessive window rejection")
	}
	ledger := `{"schema_version":"pathfinder-job-record-v2","ok":true,"recorded_at":"2026-10-19T10:00:00Z","outcome_counts":{"supported_deviation":-1}}` + "\n"
	summary, err := dashboard.BuildSummary(strings.NewReader(ledger), time.Date(2026, 10, 19, 12, 0, 0, 0, time.UTC), 90)
	if err != nil {
		t.Fatal(err)
	}
	if summary.Totals.Jobs != 0 || summary.RejectedRecords != 1 {
		t.Fatalf("malformed record should not count: %+v", summary)
	}
	future := `{"schema_version":"pathfinder-job-record-v2","ok":true,"recorded_at":"2026-10-20T00:00:00Z"}` + "\n"
	summary, err = dashboard.BuildSummary(strings.NewReader(future), time.Date(2026, 10, 19, 12, 0, 0, 0, time.UTC), 90)
	if err != nil || summary.RejectedRecords != 1 || summary.Totals.Jobs != 0 {
		t.Fatalf("future record should be excluded safely: summary=%+v err=%v", summary, err)
	}
	tooLarge := `{"schema_version":"pathfinder-job-record-v2","ok":true,"recorded_at":"2026-10-19T10:00:00Z","outcome_counts":{"supported_deviation":9007199254740992}}` + "\n"
	summary, err = dashboard.BuildSummary(strings.NewReader(tooLarge), time.Date(2026, 10, 19, 12, 0, 0, 0, time.UTC), 90)
	if err != nil || summary.RejectedRecords != 1 || summary.Totals.Jobs != 0 {
		t.Fatalf("unsafe count should be excluded: summary=%+v err=%v", summary, err)
	}
	nearLimit := `{"schema_version":"pathfinder-job-record-v2","ok":true,"recorded_at":"2026-10-19T10:00:00Z","outcome_counts":{"supported_deviation":9007199254740000}}`
	ledger = nearLimit + "\n" + nearLimit + "\n"
	if _, err := dashboard.BuildSummary(strings.NewReader(ledger), time.Date(2026, 10, 19, 12, 0, 0, 0, time.UTC), 90); err == nil {
		t.Fatal("expected aggregate overflow rejection")
	}
}

func TestBuildSummaryAggregatesBoundedStageTelemetryAndExcludesIdentifiers(t *testing.T) {
	now := time.Date(2026, 10, 19, 12, 0, 0, 0, time.UTC)
	ledger := `{"schema_version":"pathfinder-job-record-v3","job_id":"private-job","issue_number":91,"run_id":"private-run","ok":false,"recorded_at":"2026-10-19T10:00:00Z","stage_telemetry":{"evaluation":{"runs":2,"errors":1,"skipped":0,"duration_total_ns":4000000,"duration_max_ns":3000000},"intake":{"runs":1,"errors":0,"skipped":0,"duration_total_ns":1000000,"duration_max_ns":1000000}}}`
	summary, err := dashboard.BuildSummary(strings.NewReader(ledger), now, 90)
	if err != nil {
		t.Fatal(err)
	}
	got := summary.Totals.OperationalMetrics["evaluation"]
	if got.Runs != 2 || got.Errors != 1 || got.DurationTotalNS != 4000000 || got.DurationMaxNS != 3000000 {
		t.Fatalf("unexpected aggregate telemetry: %+v", got)
	}
	if summary.Daily[0].OperationalMetrics["intake"].Runs != 1 {
		t.Fatalf("daily stage metrics=%+v", summary.Daily[0].OperationalMetrics)
	}
	encoded, err := dashboard.MarshalSummary(summary)
	if err != nil {
		t.Fatal(err)
	}
	for _, forbidden := range []string{"private-job", "private-run", "issue_number"} {
		if strings.Contains(string(encoded), forbidden) {
			t.Errorf("summary leaked %q", forbidden)
		}
	}
	bad := `{"schema_version":"pathfinder-job-record-v3","ok":true,"recorded_at":"2026-10-19T10:00:00Z","stage_telemetry":{"issue-91":{"runs":1}}}`
	summary, err = dashboard.BuildSummary(strings.NewReader(bad), now, 90)
	if err != nil || summary.RejectedRecords != 1 || summary.Totals.Jobs != 0 {
		t.Fatalf("invalid telemetry record not rejected: %+v %v", summary, err)
	}
}

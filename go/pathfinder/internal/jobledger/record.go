package jobledger

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/telemetry"
	"os"
	"time"
)

const SchemaVersion = "pathfinder-job-record-v3"

// Record is a lean index line for the pathfinder-jobs branch ledger.
type Record struct {
	SchemaVersion   string                           `json:"schema_version"`
	JobID           string                           `json:"job_id"`
	IssueNumber     int                              `json:"issue_number"`
	Repository      string                           `json:"repository,omitempty"`
	RunID           string                           `json:"run_id,omitempty"`
	RunAttempt      string                           `json:"run_attempt,omitempty"`
	EngineVersion   string                           `json:"engine_version,omitempty"`
	AggregateStatus string                           `json:"aggregate_status,omitempty"`
	OutcomeCounts   map[string]int                   `json:"outcome_counts,omitempty"`
	StageTelemetry  map[string]telemetry.StageMetric `json:"stage_telemetry,omitempty"`
	PackageID       string                           `json:"package_id,omitempty"`
	PackageSHA256   string                           `json:"package_sha256,omitempty"`
	ReportSHA256    string                           `json:"report_sha256,omitempty"`
	OK              bool                             `json:"ok"`
	Error           string                           `json:"error,omitempty"`
	RecordedAt      string                           `json:"recorded_at"`
}

// Build constructs a lean record from evaluate outputs (no source bodies).
func Build(issueNumber int, repo, runID, runAttempt, engineVersion string, packageObj, report map[string]any, evalErr error) (Record, error) {
	return BuildWithTelemetry(issueNumber, repo, runID, runAttempt, engineVersion, packageObj, report, evalErr, nil)
}

func BuildWithTelemetry(issueNumber int, repo, runID, runAttempt, engineVersion string, packageObj, report map[string]any, evalErr error, stageTelemetry map[string]telemetry.StageMetric) (Record, error) {
	now := time.Now().UTC().Format(time.RFC3339)
	rec := Record{
		SchemaVersion: SchemaVersion,
		IssueNumber:   issueNumber,
		Repository:    repo,
		RunID:         runID,
		RunAttempt:    runAttempt,
		EngineVersion: engineVersion,
		RecordedAt:    now,
		OK:            evalErr == nil,
	}
	if len(stageTelemetry) > 0 {
		validated := make(map[string]telemetry.StageMetric, len(stageTelemetry))
		for stage, metric := range stageTelemetry {
			if !telemetry.ValidStage(stage) || metric.Runs < 0 || metric.Errors < 0 || metric.Skipped < 0 || metric.DurationTotalNS < 0 || metric.DurationMaxNS < 0 || metric.Errors > metric.Runs || metric.Skipped > metric.Runs-metric.Errors || metric.DurationMaxNS > metric.DurationTotalNS || (metric.Runs == 0 && (metric.Errors != 0 || metric.Skipped != 0 || metric.DurationTotalNS != 0 || metric.DurationMaxNS != 0)) || metric.Runs > (1<<53-1) || metric.Errors > (1<<53-1) || metric.Skipped > (1<<53-1) || metric.DurationTotalNS > (1<<53-1) || metric.DurationMaxNS > (1<<53-1) {
				return Record{}, fmt.Errorf("invalid stage telemetry for %q", stage)
			}
			validated[stage] = metric
		}
		rec.StageTelemetry = validated
	}
	if evalErr != nil {
		rec.Error = evalErr.Error()
	}
	if packageObj != nil {
		if id, ok := packageObj["package_id"].(string); ok {
			rec.PackageID = id
		}
		sum, err := sha256JSON(packageObj)
		if err != nil {
			return Record{}, err
		}
		rec.PackageSHA256 = sum
	}
	if report != nil {
		if s, ok := report["aggregate_status"].(string); ok {
			rec.AggregateStatus = s
		}
		if s, ok := report["report_sha256"].(string); ok {
			rec.ReportSHA256 = s
		}
		if rawCounts, ok := report["counts"]; ok {
			counts, err := parseOutcomeCounts(rawCounts)
			if err != nil {
				return Record{}, err
			}
			rec.OutcomeCounts = counts
		}
		if s, ok := report["engine_version"].(string); ok && rec.EngineVersion == "" {
			rec.EngineVersion = s
		}
	}
	rec.JobID = fmt.Sprintf("issue-%d-run-%s-%s", issueNumber, nonempty(runID, "local"), nonempty(runAttempt, "0"))
	return rec, nil
}

var allowedOutcomes = map[string]struct{}{
	"supported_deviation": {},
	"no_deviation_found":  {},
	"inconclusive":        {},
	"not_applicable":      {},
}

func parseOutcomeCounts(raw any) (map[string]int, error) {
	b, err := json.Marshal(raw)
	if err != nil {
		return nil, fmt.Errorf("encode report outcome counts: %w", err)
	}
	var counts map[string]int
	if err := json.Unmarshal(b, &counts); err != nil {
		return nil, fmt.Errorf("decode report outcome counts: %w", err)
	}
	for name, count := range counts {
		if _, ok := allowedOutcomes[name]; !ok {
			return nil, fmt.Errorf("unknown report outcome %q", name)
		}
		if count < 0 {
			return nil, fmt.Errorf("negative report outcome count for %q", name)
		}
	}
	return counts, nil
}

// WriteFile writes a single JSON object (not JSONL) for the workflow ledger step to append.
func WriteFile(path string, rec Record) error {
	b, err := json.Marshal(rec)
	if err != nil {
		return err
	}
	b = append(b, '\n')
	return os.WriteFile(path, b, 0o644)
}

func sha256JSON(v any) (string, error) {
	b, err := json.Marshal(v)
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(b)
	return hex.EncodeToString(sum[:]), nil
}

func nonempty(v, fallback string) string {
	if v == "" {
		return fallback
	}
	return v
}

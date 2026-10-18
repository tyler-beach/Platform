package jobledger

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"time"
)

const SchemaVersion = "pathfinder-job-record-v1"

// Record is a lean index line for the pathfinder-jobs branch ledger.
type Record struct {
	SchemaVersion    string `json:"schema_version"`
	JobID            string `json:"job_id"`
	IssueNumber      int    `json:"issue_number"`
	Repository       string `json:"repository,omitempty"`
	RunID            string `json:"run_id,omitempty"`
	RunAttempt       string `json:"run_attempt,omitempty"`
	EngineVersion    string `json:"engine_version,omitempty"`
	AggregateStatus  string `json:"aggregate_status,omitempty"`
	PackageID        string `json:"package_id,omitempty"`
	PackageSHA256    string `json:"package_sha256,omitempty"`
	ReportSHA256     string `json:"report_sha256,omitempty"`
	OK               bool   `json:"ok"`
	Error            string `json:"error,omitempty"`
	RecordedAt       string `json:"recorded_at"`
}

// Build constructs a lean record from evaluate outputs (no source bodies).
func Build(issueNumber int, repo, runID, runAttempt, engineVersion string, packageObj, report map[string]any, evalErr error) (Record, error) {
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
		if s, ok := report["engine_version"].(string); ok && rec.EngineVersion == "" {
			rec.EngineVersion = s
		}
	}
	rec.JobID = fmt.Sprintf("issue-%d-run-%s-%s", issueNumber, nonempty(runID, "local"), nonempty(runAttempt, "0"))
	return rec, nil
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

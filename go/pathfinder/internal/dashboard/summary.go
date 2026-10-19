package dashboard

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/telemetry"
	"io"
	"sort"
	"time"
)

const (
	SchemaVersion = "pathfinder-usage-dashboard-v2"
	ModelMetering = "not_metered"
	MaxWindowDays = 90
	maxLineBytes  = 1 << 20
	maxSafeCount  = int64(1<<53 - 1)
)

var supportedSchemas = map[string]bool{
	"pathfinder-job-record-v1": true,
	"pathfinder-job-record-v2": true,
	"pathfinder-job-record-v3": true,
}

type OutcomeCounts struct {
	SupportedDeviation int `json:"supported_deviation"`
	NoDeviationFound   int `json:"no_deviation_found"`
	Inconclusive       int `json:"inconclusive"`
	NotApplicable      int `json:"not_applicable"`
}

type Counts struct {
	Jobs               int                              `json:"jobs"`
	Succeeded          int                              `json:"succeeded"`
	Failed             int                              `json:"failed"`
	AggregateStatuses  map[string]int                   `json:"aggregate_statuses"`
	Outcomes           OutcomeCounts                    `json:"outcomes"`
	OperationalMetrics map[string]telemetry.StageMetric `json:"operational_metrics"`
}

type Day struct {
	Date               string                           `json:"date"`
	Jobs               int                              `json:"jobs"`
	Succeeded          int                              `json:"succeeded"`
	Failed             int                              `json:"failed"`
	AggregateStatuses  map[string]int                   `json:"aggregate_statuses"`
	Outcomes           OutcomeCounts                    `json:"outcomes"`
	OperationalMetrics map[string]telemetry.StageMetric `json:"operational_metrics"`
}

type Summary struct {
	SchemaVersion        string `json:"schema_version"`
	GeneratedAt          string `json:"generated_at"`
	WindowDays           int    `json:"window_days"`
	RecordsSeen          int    `json:"records_seen"`
	RejectedRecords      int    `json:"rejected_records"`
	Totals               Counts `json:"totals"`
	Daily                []Day  `json:"daily"`
	ModelMetering        string `json:"model_metering"`
	OperationalTelemetry string `json:"operational_telemetry"`
}

type ledgerRecord struct {
	SchemaVersion   string                           `json:"schema_version"`
	RecordedAt      string                           `json:"recorded_at"`
	OK              bool                             `json:"ok"`
	AggregateStatus string                           `json:"aggregate_status"`
	OutcomeCounts   map[string]int                   `json:"outcome_counts,omitempty"`
	StageTelemetry  map[string]telemetry.StageMetric `json:"stage_telemetry,omitempty"`
}

var allowedAggregateStatuses = map[string]bool{
	"all_aligned": true, "deviations_found": true, "mixed": true,
	"insufficient_coverage": true, "not_applicable_only": true,
}

var aggregateStatusKeys = []string{"all_aligned", "deviations_found", "mixed", "insufficient_coverage", "not_applicable_only", "other"}

func emptyAggregateStatuses() map[string]int {
	counts := make(map[string]int, len(aggregateStatusKeys))
	for _, key := range aggregateStatusKeys {
		counts[key] = 0
	}
	return counts
}

func emptyStageMetrics() map[string]telemetry.StageMetric {
	metrics := make(map[string]telemetry.StageMetric, len(telemetry.StageNames()))
	for _, stage := range telemetry.StageNames() {
		metrics[stage] = telemetry.StageMetric{}
	}
	return metrics
}

func BuildSummary(input io.Reader, now time.Time, windowDays int) (Summary, error) {
	if windowDays < 1 || windowDays > MaxWindowDays {
		return Summary{}, fmt.Errorf("window days must be between 1 and %d", MaxWindowDays)
	}
	if input == nil {
		return Summary{}, errors.New("ledger input is required")
	}
	now = now.UTC()
	start := time.Date(now.Year(), now.Month(), now.Day(), 0, 0, 0, 0, time.UTC).AddDate(0, 0, -(windowDays - 1))
	buckets := make(map[string]*Day, windowDays)
	summary := Summary{
		SchemaVersion:        SchemaVersion,
		GeneratedAt:          now.Format(time.RFC3339),
		WindowDays:           windowDays,
		ModelMetering:        ModelMetering,
		OperationalTelemetry: "not_available",
		Totals:               Counts{AggregateStatuses: emptyAggregateStatuses(), OperationalMetrics: emptyStageMetrics()},
		Daily:                make([]Day, 0, windowDays),
	}

	scanner := bufio.NewScanner(input)
	scanner.Buffer(make([]byte, 64*1024), maxLineBytes)
	for scanner.Scan() {
		line := bytes.TrimSpace(scanner.Bytes())
		if len(line) == 0 {
			continue
		}
		summary.RecordsSeen++
		var record ledgerRecord
		if err := json.Unmarshal(line, &record); err != nil || !supportedSchemas[record.SchemaVersion] {
			summary.RejectedRecords++
			continue
		}
		recordedAt, err := time.Parse(time.RFC3339, record.RecordedAt)
		if err != nil || recordedAt.After(now) || !validCounts(record.OutcomeCounts) || !validStageMetrics(record.StageTelemetry) {
			summary.RejectedRecords++
			continue
		}
		recordedAt = recordedAt.UTC()
		if recordedAt.Before(start) {
			continue
		}
		if len(record.StageTelemetry) > 0 {
			summary.OperationalTelemetry = "available"
		}
		key := recordedAt.Format("2006-01-02")
		bucket := buckets[key]
		if bucket == nil {
			bucket = &Day{Date: key, AggregateStatuses: emptyAggregateStatuses(), OperationalMetrics: emptyStageMetrics()}
			buckets[key] = bucket
		}
		if err := applyRecord(&summary.Totals, bucket, record); err != nil {
			return Summary{}, err
		}
	}
	if err := scanner.Err(); err != nil {
		return Summary{}, fmt.Errorf("read job ledger: %w", err)
	}
	for _, bucket := range buckets {
		summary.Daily = append(summary.Daily, *bucket)
	}
	sort.Slice(summary.Daily, func(i, j int) bool { return summary.Daily[i].Date < summary.Daily[j].Date })
	return summary, nil
}

func applyRecord(totals *Counts, day *Day, record ledgerRecord) error {
	totals.Jobs++
	day.Jobs++
	if record.OK {
		totals.Succeeded++
		day.Succeeded++
		status := record.AggregateStatus
		if !allowedAggregateStatuses[status] {
			status = "other"
		}
		if totals.AggregateStatuses == nil {
			totals.AggregateStatuses = emptyAggregateStatuses()
		}
		if day.AggregateStatuses == nil {
			day.AggregateStatuses = emptyAggregateStatuses()
		}
		totals.AggregateStatuses[status]++
		day.AggregateStatuses[status]++
		var err error
		totals.Outcomes, err = addOutcomeCounts(totals.Outcomes, record.OutcomeCounts)
		if err != nil {
			return err
		}
		day.Outcomes, err = addOutcomeCounts(day.Outcomes, record.OutcomeCounts)
		if err != nil {
			return err
		}
	} else {
		totals.Failed++
		day.Failed++
	}
	var err error
	totals.OperationalMetrics, err = addStageMetrics(totals.OperationalMetrics, record.StageTelemetry)
	if err != nil {
		return err
	}
	day.OperationalMetrics, err = addStageMetrics(day.OperationalMetrics, record.StageTelemetry)
	if err != nil {
		return err
	}
	return nil
}

func validStageMetrics(metrics map[string]telemetry.StageMetric) bool {
	for stage, metric := range metrics {
		if !telemetry.ValidStage(stage) || metric.Runs < 0 || metric.Errors < 0 || metric.Skipped < 0 || metric.DurationTotalNS < 0 || metric.DurationMaxNS < 0 || metric.Errors > metric.Runs || metric.Skipped > metric.Runs-metric.Errors || metric.DurationMaxNS > metric.DurationTotalNS || (metric.Runs == 0 && (metric.Errors != 0 || metric.Skipped != 0 || metric.DurationTotalNS != 0 || metric.DurationMaxNS != 0)) || metric.Runs > maxSafeCount || metric.Errors > maxSafeCount || metric.Skipped > maxSafeCount || metric.DurationTotalNS > maxSafeCount || metric.DurationMaxNS > maxSafeCount {
			return false
		}
	}
	return true
}

func addStageMetrics(total, addition map[string]telemetry.StageMetric) (map[string]telemetry.StageMetric, error) {
	if total == nil {
		total = emptyStageMetrics()
	}
	for stage, value := range addition {
		current := total[stage]
		for _, pair := range [][2]int64{{current.Runs, value.Runs}, {current.Errors, value.Errors}, {current.Skipped, value.Skipped}, {current.DurationTotalNS, value.DurationTotalNS}} {
			if pair[1] > maxSafeCount-pair[0] {
				return nil, fmt.Errorf("dashboard telemetry total exceeds safe integer range")
			}
		}
		current.Runs += value.Runs
		current.Errors += value.Errors
		current.Skipped += value.Skipped
		current.DurationTotalNS += value.DurationTotalNS
		if value.DurationMaxNS > current.DurationMaxNS {
			current.DurationMaxNS = value.DurationMaxNS
		}
		total[stage] = current
	}
	return total, nil
}

func validCounts(counts map[string]int) bool {
	for key, value := range counts {
		if value < 0 || int64(value) > maxSafeCount {
			return false
		}
		switch key {
		case "supported_deviation", "no_deviation_found", "inconclusive", "not_applicable":
		default:
			return false
		}
	}
	return true
}

func addOutcomeCounts(total OutcomeCounts, counts map[string]int) (OutcomeCounts, error) {
	values := []struct {
		target *int
		key    string
	}{
		{&total.SupportedDeviation, "supported_deviation"},
		{&total.NoDeviationFound, "no_deviation_found"},
		{&total.Inconclusive, "inconclusive"},
		{&total.NotApplicable, "not_applicable"},
	}
	for _, item := range values {
		addition := counts[item.key]
		if int64(addition) > maxSafeCount-int64(*item.target) {
			return OutcomeCounts{}, fmt.Errorf("dashboard outcome total exceeds safe integer range")
		}
		*item.target += addition
	}
	return total, nil
}

func MarshalSummary(summary Summary) ([]byte, error) {
	if summary.SchemaVersion != SchemaVersion || summary.ModelMetering != ModelMetering || (summary.OperationalTelemetry != "available" && summary.OperationalTelemetry != "not_available") || summary.WindowDays < 1 || summary.WindowDays > MaxWindowDays {
		return nil, errors.New("invalid dashboard summary metadata")
	}
	encoded, err := json.MarshalIndent(summary, "", "  ")
	if err != nil {
		return nil, fmt.Errorf("encode dashboard summary: %w", err)
	}
	return append(encoded, '\n'), nil
}

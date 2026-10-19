package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/dashboard"
)

func main() {
	inputPath := flag.String("input", "", "path to pathfinder-jobs JSONL ledger")
	outputPath := flag.String("output", "", "path for the aggregate dashboard JSON")
	windowDays := flag.Int("window-days", 90, "maximum reporting window in days")
	flag.Parse()
	if *inputPath == "" || *outputPath == "" {
		fmt.Fprintln(os.Stderr, "--input and --output are required")
		os.Exit(2)
	}
	input, err := os.Open(*inputPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, "open dashboard ledger:", err)
		os.Exit(2)
	}
	defer input.Close()
	summary, err := dashboard.BuildSummary(input, time.Now().UTC(), *windowDays)
	if err != nil {
		fmt.Fprintln(os.Stderr, "build dashboard summary:", err)
		os.Exit(2)
	}
	encoded, err := dashboard.MarshalSummary(summary)
	if err != nil {
		fmt.Fprintln(os.Stderr, "marshal dashboard summary:", err)
		os.Exit(2)
	}
	if err := os.MkdirAll(filepath.Dir(*outputPath), 0o755); err != nil {
		fmt.Fprintln(os.Stderr, "create dashboard output directory:", err)
		os.Exit(2)
	}
	if err := os.WriteFile(*outputPath, encoded, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, "write dashboard summary:", err)
		os.Exit(2)
	}
}

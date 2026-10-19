package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"time"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/catalog"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/collect/pkgcollect"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/evaluate"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/telemetry"
)

func main() {
	ctx := context.Background()
	tel := telemetry.Initialize(ctx, "pathfinder-evaluate-package")
	ctx, root := tel.Start(ctx, "pathfinder.analysis")
	code := run(ctx, tel)
	if code == 0 {
		tel.RecordJob(ctx, "ok")
	} else {
		tel.RecordJob(ctx, "error")
	}
	root.End()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if err := tel.Shutdown(shutdownCtx); err != nil {
		fmt.Fprintln(os.Stderr, "warning: OpenTelemetry flush failed (details redacted)")
	}
	os.Exit(code)
}

func run(ctx context.Context, tel *telemetry.Runtime) int {
	outPath := flag.String("out", "", "write report JSON to path")
	catalogDirFlag := flag.String("catalog-dir", "", "requirement catalog directory")
	catalogModeFlag := flag.String("catalog-mode", "", "catalog mode: synthetic|real (or PATHFINDER_CATALOG)")
	flag.Parse()
	if flag.NArg() != 1 {
		fmt.Fprintln(os.Stderr, "usage: pathfinder-evaluate-package [--out path] [--catalog-dir dir] [--catalog-mode synthetic|real] <package.json>")
		return 2
	}
	pkgPath := flag.Arg(0)
	_, finish := tel.Stage(ctx, "catalog_load")
	mode, err := catalog.ResolveMode(*catalogModeFlag)
	if err != nil {
		finish(err)
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	catalogDir := *catalogDirFlag
	if catalogDir == "" {
		var resolveErr error
		catalogDir, resolveErr = catalog.ResolveDir(findRepoRoot(), mode)
		if resolveErr != nil {
			finish(resolveErr)
			fmt.Fprintln(os.Stderr, resolveErr)
			return 2
		}
	}
	finish(nil)
	_, finish = tel.Stage(ctx, "package_build")
	pkg, err := pkgcollect.LoadPackage(pkgPath)
	if err != nil {
		finish(err)
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	finish(nil)
	_, finish = tel.Stage(ctx, "evaluation")
	report, err := evaluate.EvaluatePackageWithMode(pkg, catalogDir, "accepted", mode)
	if err != nil {
		finish(err)
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	finish(nil)
	_, finish = tel.Stage(ctx, "report_write")
	encoded, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		finish(err)
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	encoded = append(encoded, '\n')
	if *outPath != "" {
		if err := os.MkdirAll(filepath.Dir(*outPath), 0o755); err != nil {
			finish(err)
			fmt.Fprintln(os.Stderr, err)
			return 2
		}
		if err := os.WriteFile(*outPath, encoded, 0o644); err != nil {
			finish(err)
			fmt.Fprintln(os.Stderr, err)
			return 2
		}
		finish(nil)
		return 0
	}
	os.Stdout.Write(encoded)
	finish(nil)
	return 0
}

func findRepoRoot() string {
	wd, _ := os.Getwd()
	dir := wd
	for {
		if _, err := os.Stat(filepath.Join(dir, ".poc", "requirement_catalog", "requirements.jsonl")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return wd
		}
		dir = parent
	}
}

package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/catalog"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/collect/pkgcollect"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/evaluate"
)

func main() {
	outPath := flag.String("out", "", "write report JSON to path")
	catalogDirFlag := flag.String("catalog-dir", "", "requirement catalog directory")
	flag.Parse()
	if flag.NArg() != 1 {
		fmt.Fprintln(os.Stderr, "usage: pathfinder-evaluate-package [--out path] [--catalog-dir dir] <package.json>")
		os.Exit(2)
	}
	pkgPath := flag.Arg(0)
	catalogDir := *catalogDirFlag
	if catalogDir == "" {
		catalogDir = catalog.DefaultDir(findRepoRoot())
	}
	pkg, err := pkgcollect.LoadPackage(pkgPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	// Optional --domains via remaining? keep simple; domains stay in package.
	report, err := evaluate.EvaluatePackage(pkg, catalogDir, "accepted")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	encoded, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	encoded = append(encoded, '\n')
	if *outPath != "" {
		if err := os.MkdirAll(filepath.Dir(*outPath), 0o755); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(2)
		}
		if err := os.WriteFile(*outPath, encoded, 0o644); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(2)
		}
		return
	}
	os.Stdout.Write(encoded)
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

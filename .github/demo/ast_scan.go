package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"strings"
)

type Observation struct {
	ObservationID string `json:"observation_id"`
	Line          int    `json:"line"`
	Call          string `json:"call"`
	Classification string `json:"classification"`
	Reason        string `json:"reason"`
}

type Result struct {
	Scanner       string        `json:"scanner"`
	SourcePath    string        `json:"source_path"`
	SourceSHA256  string        `json:"source_sha256"`
	ParseStatus   string        `json:"parse_status"`
	Observations  []Observation `json:"observations"`
	ScopeNote     string        `json:"scope_note"`
}

func main() {
	source := flag.String("source", "", "Go source file to parse")
	out := flag.String("out", "", "JSON output path")
	flag.Parse()
	if *source == "" || *out == "" {
		fmt.Fprintln(os.Stderr, "usage: ast_scan --source handler.go --out ast-analysis.json")
		os.Exit(2)
	}
	content, err := os.ReadFile(*source)
	must(err)
	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, *source, content, parser.AllErrors|parser.ParseComments)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Go AST parse failed: %v\n", err)
		os.Exit(1)
	}
	sum := sha256.Sum256(content)
	result := Result{
		Scanner: "go/parser + go/ast (demo scanner; no type-check or package build)",
		SourcePath: *source,
		SourceSHA256: hex.EncodeToString(sum[:]),
		ParseStatus: "parsed",
		Observations: []Observation{},
		ScopeNote: "This pass extracts selected call sites from the synthetic handler. It does not resolve dynamic dispatch or prove transitive runtime behavior.",
	}
	index := 0
	ast.Inspect(file, func(n ast.Node) bool {
		call, ok := n.(*ast.CallExpr)
		if !ok {
			return true
		}
		var b strings.Builder
		if err := format.Node(&b, fset, call.Fun); err != nil {
			return true
		}
		callText := b.String()
		classification, reason := classify(callText)
		if classification == "" {
			return true
		}
		index++
		result.Observations = append(result.Observations, Observation{
			ObservationID: fmt.Sprintf("AST-%03d", index),
			Line: fset.Position(call.Pos()).Line,
			Call: callText,
			Classification: classification,
			Reason: reason,
		})
		return true
	})
	body, err := json.MarshalIndent(result, "", "  ")
	must(err)
	must(os.WriteFile(*out, append(body, '\n'), 0644))
	fmt.Printf("Go AST parse: %s (%d selected call sites)\n", result.ParseStatus, len(result.Observations))
	for _, observation := range result.Observations {
		fmt.Printf("  line %d: %s -> %s\n", observation.Line, observation.Call, observation.Classification)
	}
}

func classify(call string) (string, string) {
	lower := strings.ToLower(call)
	switch {
	case strings.HasSuffix(lower, ".assess") || strings.HasSuffix(lower, ".createmessage") || strings.HasSuffix(lower, ".generate"):
		return "synchronous_provider_call", "A provider-style method is invoked directly at this call site; the demo treats this as inline execution."
	case strings.HasSuffix(lower, ".enqueue") || strings.HasSuffix(lower, ".startexecution") || strings.HasSuffix(lower, ".submitjob"):
		return "async_enqueue", "The handler hands work to an asynchronous queue/workflow boundary."
	case strings.HasSuffix(lower, ".run"):
		return "delegated_call", "The call delegates to another abstraction; this file alone does not establish whether provider work is synchronous."
	default:
		return "", ""
	}
}

func must(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

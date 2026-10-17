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
	ObservationID       string `json:"observation_id"`
	Function            string `json:"enclosing_function"`
	Line                int    `json:"line"`
	Column              int    `json:"column"`
	EndLine             int    `json:"end_line"`
	EndColumn           int    `json:"end_column"`
	Call                string `json:"call"`
	Expression          string `json:"expression"`
	Receiver            string `json:"receiver_expression"`
	Method              string `json:"method_name"`
	Classification      string `json:"classification"`
	ClassificationBasis string `json:"classification_basis"`
	Reason              string `json:"reason"`
}

type Result struct {
	Scanner      string        `json:"scanner"`
	SourcePath   string        `json:"source_path"`
	SourceSHA256 string        `json:"source_sha256"`
	ParseStatus  string        `json:"parse_status"`
	Observations []Observation `json:"observations"`
	ScopeNote    string        `json:"scope_note"`
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
		Scanner: "Go standard library: go/parser + go/ast + go/token + go/format",
		SourcePath: *source,
		SourceSHA256: hex.EncodeToString(sum[:]),
		ParseStatus: "parsed",
		Observations: []Observation{},
		ScopeNote: "This is real Go syntax-tree analysis. Classifications are explicit syntactic heuristics over call targets; there is no type-check, interprocedural call graph, dynamic dispatch resolution, or runtime proof.",
	}
	index := 0
	for _, decl := range file.Decls {
		fn, ok := decl.(*ast.FuncDecl)
		if !ok || fn.Body == nil {
			continue
		}
		ast.Inspect(fn.Body, func(n ast.Node) bool {
			call, ok := n.(*ast.CallExpr)
			if !ok {
				return true
			}
			var targetBuilder, expressionBuilder strings.Builder
			if err := format.Node(&targetBuilder, fset, call.Fun); err != nil {
				return true
			}
			if err := format.Node(&expressionBuilder, fset, call); err != nil {
				return true
			}
			target := targetBuilder.String()
			selector, ok := call.Fun.(*ast.SelectorExpr)
			if !ok {
				return true
			}
			var receiverBuilder strings.Builder
			if err := format.Node(&receiverBuilder, fset, selector.X); err != nil {
				return true
			}
			receiver, method := receiverBuilder.String(), selector.Sel.Name
			classification, reason := classify(receiver, method)
			if classification == "" {
				return true
			}
			start, end := fset.Position(call.Pos()), fset.Position(call.End())
			index++
			result.Observations = append(result.Observations, Observation{
				ObservationID: fmt.Sprintf("AST-%03d", index),
				Function: fn.Name.Name,
				Line: start.Line,
				Column: start.Column,
				EndLine: end.Line,
				EndColumn: end.Column,
				Call: target,
				Expression: expressionBuilder.String(),
				Receiver: receiver,
				Method: method,
				Classification: classification,
				ClassificationBasis: "syntactic_heuristic",
				Reason: reason,
			})
			return true
		})
	}
	body, err := json.MarshalIndent(result, "", "  ")
	must(err)
	must(os.WriteFile(*out, append(body, '\n'), 0644))
	fmt.Printf("Go AST parse: %s; %d classified call sites\n", result.ParseStatus, len(result.Observations))
	for _, observation := range result.Observations {
		fmt.Printf("  %s:%d:%d-%d:%d %s -> %s [syntactic heuristic]\n",
			observation.Function, observation.Line, observation.Column,
			observation.EndLine, observation.EndColumn, observation.Expression,
			observation.Classification)
	}
}

func classify(receiver, method string) (string, string) {
	lowerReceiver, lowerMethod := strings.ToLower(receiver), strings.ToLower(method)
	switch {
	case strings.Contains(lowerReceiver, "anthropic") &&
		(lowerMethod == "assess" || lowerMethod == "createmessage" || lowerMethod == "generate"):
		return "synchronous_provider_call", "AST shows a direct call to a provider-shaped receiver from this function. This is a syntactic rule, not a resolved SDK/type check."
	case lowerMethod == "enqueue" || lowerMethod == "startexecution" || lowerMethod == "submitjob":
		return "async_enqueue", "AST shows a call whose method name suggests enqueue or workflow submission. The callee implementation is not resolved."
	case lowerMethod == "run":
		return "delegated_call", "AST shows delegation to a Run method; this file does not show whether the callee uses synchronous or asynchronous execution."
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

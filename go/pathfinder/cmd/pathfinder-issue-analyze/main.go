package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/tyler-beach/Platform/go/pathfinder/internal/adapt/pr"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/catalog"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/engine"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/evaluate"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/issueintake"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/jobledger"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/predicates"
	"github.com/tyler-beach/Platform/go/pathfinder/internal/telemetry"
)

func main() {
	ctx := context.Background()
	tel := telemetry.Initialize(ctx, "pathfinder-issue-analyze")
	ctx, span := tel.Start(ctx, "pathfinder.analysis")
	code := run(ctx, tel)
	if code == 0 {
		tel.RecordJob(ctx, "ok")
	} else {
		tel.RecordJob(ctx, "error")
	}
	span.End()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	if err := tel.Shutdown(shutdownCtx); err != nil {
		fmt.Fprintln(os.Stderr, "warning: OpenTelemetry flush failed (details redacted)")
	}
	os.Exit(code)
}

func run(ctx context.Context, tel *telemetry.Runtime) int {
	issueNumber := flag.Int("issue-number", -1, "GitHub issue number (0 allowed for local body-file runs)")
	repo := flag.String("repo", os.Getenv("GITHUB_REPOSITORY"), "owner/repo")
	runURL := flag.String("run-url", os.Getenv("RUN_URL"), "workflow run URL")
	workDir := flag.String("work-dir", "", "directory for package/report/comment")
	comment := flag.Bool("comment", false, "post or update issue comment via gh")
	bodyFile := flag.String("body-file", "", "local issue body instead of gh api")
	catalogDirFlag := flag.String("catalog-dir", "", "requirement catalog directory")
	catalogModeFlag := flag.String("catalog-mode", "", "catalog mode: synthetic|real (or PATHFINDER_CATALOG)")
	flag.Parse()

	if *issueNumber < 0 {
		fmt.Fprintln(os.Stderr, "--issue-number is required")
		return 2
	}
	work := *workDir
	if work == "" {
		var err error
		work, err = os.MkdirTemp("", "pathfinder-issue-")
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			return 2
		}
	}
	if err := os.MkdirAll(work, 0o755); err != nil {
		fmt.Fprintln(os.Stderr, err)
		return 2
	}
	run := *runURL
	if run == "" {
		run = "(local run)"
	}

	repoRoot := findRepoRoot()
	exitCode := 0
	var body, title string
	var err error
	_, finishStage := tel.Stage(ctx, "intake")
	if *bodyFile != "" {
		raw, readErr := os.ReadFile(*bodyFile)
		if readErr != nil {
			err = readErr
		} else {
			body = string(raw)
			title = "[Pathfinder analyze] local"
		}
	} else {
		if *repo == "" {
			err = &issueintake.Error{Msg: "GITHUB_REPOSITORY / --repo is required"}
		} else {
			body, title, err = fetchIssue(*repo, *issueNumber)
		}
	}
	finishStage(err)

	if err == nil {
		lowerTitle := strings.ToLower(title)
		lowerBody := strings.ToLower(body)
		if !strings.Contains(lowerTitle, "[pathfinder analyze]") &&
			!strings.Contains(lowerBody, "pathfinder-analyze") &&
			!strings.Contains(lowerBody, "public / synthetic attestation") {
			err = &issueintake.Error{Msg: "issue is not a Pathfinder analyze submission"}
		}
	}

	modeFlag := *catalogModeFlag
	if modeFlag == "" && body != "" {
		modeFlag = issueintake.CatalogModeFromIssueBody(body)
	}
	_, finishStage = tel.Stage(ctx, "catalog_load")
	mode, modeErr := catalog.ResolveMode(modeFlag)
	if modeErr != nil {
		fmt.Fprintln(os.Stderr, modeErr)
		finishStage(modeErr)
		return 2
	}
	catalogDir := *catalogDirFlag
	if catalogDir == "" {
		var resolveErr error
		catalogDir, resolveErr = catalog.ResolveDir(repoRoot, mode)
		if resolveErr != nil {
			fmt.Fprintln(os.Stderr, resolveErr)
			finishStage(resolveErr)
			return 2
		}
	}

	reg, regErr := predicates.Load(catalogDir)
	var rows []map[string]any
	catalogErr := regErr
	if catalogErr == nil {
		rows, catalogErr = catalog.LoadRequirements(catalogDir, reg)
	}
	if err == nil {
		err = catalogErr
	}
	finishStage(catalogErr)
	subjects := catalog.SubjectMap(rows)

	var packageObj map[string]any
	var report map[string]any
	_, finishStage = tel.Stage(ctx, "package_build")
	packageAttempted := err == nil
	if packageAttempted {
		opts := issueintake.Options{Repo: *repo}
		if *repo != "" {
			opts.PRClient = pr.NewGHClient()
		}
		packageObj, err = issueintake.PackageFromIssue(body, *issueNumber, catalogDir, subjects, reg, opts)
	}
	if err == nil {
		pkgPath := filepath.Join(work, "package.json")
		if werr := writeJSON(pkgPath, packageObj); werr != nil {
			err = werr
		}
	}
	packageStageErr := telemetry.ErrSkipped
	if packageAttempted {
		packageStageErr = err
	}
	finishStage(packageStageErr)
	_, finishStage = tel.Stage(ctx, "evaluation")
	evaluationAttempted := err == nil
	if evaluationAttempted {
		report, err = evaluate.EvaluatePackageWithMode(packageObj, catalogDir, "accepted", mode)
	}
	evaluationStageErr := telemetry.ErrSkipped
	if evaluationAttempted {
		evaluationStageErr = err
	}
	finishStage(evaluationStageErr)
	_, finishStage = tel.Stage(ctx, "report_write")
	reportWriteAttempted := err == nil
	if reportWriteAttempted {
		if werr := writeJSON(filepath.Join(work, "report.json"), report); werr != nil {
			err = werr
		}
	}
	reportWriteErr := telemetry.ErrSkipped
	if reportWriteAttempted {
		reportWriteErr = err
	}
	finishStage(reportWriteErr)
	var commentMD string
	_, finishStage = tel.Stage(ctx, "publication")
	publicationAttempted := err == nil
	if publicationAttempted {
		commentMD, err = issueintake.RenderResultComment(report, packageObj, run)
	}
	publicationErr := telemetry.ErrSkipped
	if publicationAttempted {
		publicationErr = err
	}
	finishStage(publicationErr)
	writeJobRecord := func(evalErr error) {
		_, finishStage := tel.Stage(ctx, "ledger")
		buildRecord := func() (jobledger.Record, error) {
			return jobledger.BuildWithTelemetry(
				*issueNumber,
				*repo,
				os.Getenv("GITHUB_RUN_ID"),
				os.Getenv("GITHUB_RUN_ATTEMPT"),
				engine.EngineVersion,
				packageObj,
				report,
				evalErr,
				tel.StageSnapshot(),
			)
		}
		rec, rerr := buildRecord()
		if rerr != nil {
			fmt.Fprintln(os.Stderr, "job record:", rerr)
			finishStage(rerr)
			return
		}
		tmpPath := filepath.Join(work, "job.json.telemetry.tmp")
		if werr := jobledger.WriteFile(tmpPath, rec); werr != nil {
			fmt.Fprintln(os.Stderr, "job record write:", werr)
			finishStage(werr)
			_ = os.Remove(tmpPath)
			return
		}
		finishStage(nil)
		rec, rerr = buildRecord()
		_ = os.Remove(tmpPath)
		if rerr != nil {
			fmt.Fprintln(os.Stderr, "job record:", rerr)
			return
		}
		if werr := jobledger.WriteFile(filepath.Join(work, "job.json"), rec); werr != nil {
			fmt.Fprintln(os.Stderr, "job record write:", werr)
		}
	}

	if err != nil {
		exitCode = 2
		msg := err.Error()
		commentMD = issueintake.RenderErrorComment(msg, run)
		_ = os.WriteFile(filepath.Join(work, "comment.md"), []byte(commentMD), 0o644)
		enc, _ := json.Marshal(map[string]any{"ok": false, "error": msg})
		fmt.Fprintln(os.Stderr, string(enc))
		if *comment {
			if *repo == "" {
				fmt.Fprintln(os.Stderr, "repo required to comment")
				writeJobRecord(err)
				return 2
			}
			_, finishStage = tel.Stage(ctx, "publication")
			cerr := publishComment(*repo, *issueNumber, filepath.Join(work, "comment.md"))
			if cerr != nil {
				fmt.Fprintln(os.Stderr, cerr)
			}
			finishStage(cerr)
		}
		writeJobRecord(err)
		return exitCode
	}

	_ = os.WriteFile(filepath.Join(work, "comment.md"), []byte(commentMD), 0o644)
	out, _ := json.Marshal(map[string]any{
		"ok":               true,
		"aggregate_status": report["aggregate_status"],
		"counts":           report["counts"],
		"package_path":     filepath.Join(work, "package.json"),
		"report_path":      filepath.Join(work, "report.json"),
	})
	fmt.Println(string(out))
	publicationFailed := false
	if *comment {
		if *repo == "" {
			fmt.Fprintln(os.Stderr, "repo required to comment")
			_, finishStage = tel.Stage(ctx, "publication")
			finishStage(errors.New("comment publication requires a repository"))
			writeJobRecord(nil)
			return 2
		}
		_, finishStage = tel.Stage(ctx, "publication")
		if cerr := publishComment(*repo, *issueNumber, filepath.Join(work, "comment.md")); cerr != nil {
			fmt.Fprintln(os.Stderr, cerr)
			publicationFailed = true
			finishStage(cerr)
		} else {
			finishStage(nil)
		}
	}
	writeJobRecord(nil)
	if publicationFailed {
		return 2
	}
	return 0
}

func writeJSON(path string, value any) error {
	b, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return err
	}
	b = append(b, '\n')
	return os.WriteFile(path, b, 0o644)
}

func fetchIssue(repo string, number int) (body, title string, err error) {
	cmd := exec.Command("gh", "api", fmt.Sprintf("repos/%s/issues/%d", repo, number))
	out, err := cmd.Output()
	if err != nil {
		return "", "", err
	}
	var issue map[string]any
	if err := json.Unmarshal(out, &issue); err != nil {
		return "", "", err
	}
	body, _ = issue["body"].(string)
	title, _ = issue["title"].(string)
	return body, title, nil
}

func publishComment(repo string, number int, bodyFile string) error {
	raw, err := os.ReadFile(bodyFile)
	if err != nil {
		return err
	}
	// Best-effort update existing Pathfinder comment by marker.
	list := exec.Command("gh", "api", fmt.Sprintf("repos/%s/issues/%d/comments", repo, number), "--paginate")
	out, err := list.Output()
	if err == nil {
		var comments []map[string]any
		if json.Unmarshal(out, &comments) == nil {
			for _, c := range comments {
				body, _ := c["body"].(string)
				if strings.Contains(body, issueintake.CommentMarker) {
					id := fmt.Sprint(c["id"])
					payload, _ := json.Marshal(map[string]string{"body": string(raw)})
					cmd := exec.Command("gh", "api", "--method", "PATCH",
						fmt.Sprintf("repos/%s/issues/comments/%s", repo, id),
						"--input", "-",
					)
					cmd.Stdin = strings.NewReader(string(payload))
					return cmd.Run()
				}
			}
		}
	}
	cmd := exec.Command("gh", "issue", "comment", fmt.Sprint(number), "--repo", repo, "--body-file", bodyFile)
	return cmd.Run()
}

func findRepoRoot() string {
	wd, err := os.Getwd()
	if err != nil {
		return "."
	}
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

#!/usr/bin/env python3
"""Evidence-first evaluator for cross-domain ADR requirement scenarios.

The corpus contains provisional synthetic reference labels. Independent reviewer
adjudication is explicitly tracked separately and is not claimed by this module.
"""
from __future__ import annotations
import hashlib, json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / ".poc" / "evaluation" / "requirements" / "cases.jsonl"
LABELS = {"deviation", "no_deviation", "ambiguous"}

def load_cases():
    cases=[json.loads(x) for x in CORPUS.read_text(encoding="utf-8").splitlines() if x.strip()]
    ids=[c["case_id"] for c in cases]
    if len(ids)!=len(set(ids)): raise ValueError("duplicate case_id")
    counts=Counter(c["requirement_type"] for c in cases)
    if not counts or any(v!=20 for v in counts.values()):
        raise ValueError(f"Each requirement type must have exactly 20 cases: {dict(counts)}")
    for c in cases:
        if c["gold_label"] not in LABELS: raise ValueError(f"invalid label: {c['case_id']}")
        if c["split"] not in {"development","locked_holdout"}: raise ValueError("invalid split")
        if c.get("independent_adjudication_status") != "pending":
            raise ValueError("synthetic corpus must not imply completed independent adjudication")
    return cases

def fingerprint():
    return hashlib.sha256(CORPUS.read_bytes()).hexdigest()

def classify(case):
    f=case["facts"]; t=case["requirement_type"]
    if t=="session_ttl":
        if not f.get("evidence_complete") or not f.get("active_config"):
            return "ambiguous"
        ttl=f.get("ttl_seconds"); limit=f.get("max_ttl_seconds")
        if ttl is None or limit is None: return "ambiguous"
        if ttl > limit and f.get("exception_valid") is True: return "no_deviation"
        if ttl > limit and f.get("exception_valid") is None: return "ambiguous"
        return "deviation" if ttl > limit else "no_deviation"
    if t=="pod_disruption_budget":
        if not f.get("evidence_complete"): return "ambiguous"
        if f.get("workload_active") is False: return "no_deviation"
        if f.get("pdb_present") is False: return "deviation"
        if f.get("pdb_present") is None or f.get("pdb_selector_matches") is None: return "ambiguous"
        if f.get("pdb_selector_matches") is False: return "deviation"
        actual=f.get("actual_min_available"); required=f.get("required_min_available")
        if actual is None or required is None: return "ambiguous"
        return "deviation" if actual < required else "no_deviation"
    if t=="sensitive_data_logging":
        if not f.get("evidence_complete"): return "ambiguous"
        sensitive=f.get("sensitive_data_observed"); redaction=f.get("redaction_verified")
        if sensitive is None or redaction is None: return "ambiguous"
        if sensitive is True: return "deviation"
        if sensitive is False and redaction is True: return "no_deviation"
        return "ambiguous"
    if t=="async_provider":
        if not f.get("evidence_complete") or not f.get("dispatch_resolved"): return "ambiguous"
        direct=f.get("direct_sync_call"); boundary=f.get("async_boundary")
        if direct is None or boundary is None: return "ambiguous"
        if direct is True and boundary is True: return "ambiguous"
        return "deviation" if direct is True and boundary is False else "no_deviation"
    if t=="approved_exception":
        if not f.get("evidence_complete"): return "ambiguous"
        if f.get("exception_used") is False: return "no_deviation"
        if any(f.get(k) is None for k in ("approved","unexpired","scope_matches")): return "ambiguous"
        valid=f["approved"] is True and f["unexpired"] is True and f["scope_matches"] is True
        return "no_deviation" if valid else "deviation"
    if t=="runtime_evidence":
        if f.get("applicable") is False: return "no_deviation"
        if f.get("applicable") is None: return "ambiguous"
        if not f.get("evidence_present") or not f.get("fresh") or not f.get("source_pinned"): return "ambiguous"
        contradictory=f.get("contradicts_requirement")
        if contradictory is None: return "ambiguous"
        return "deviation" if contradictory else "no_deviation"
    raise ValueError(f"unknown requirement_type: {t}")

def metrics(rows):
    n=len(rows); correct=sum(r["predicted_label"]==r["gold_label"] for r in rows)
    labels=("deviation","no_deviation","ambiguous")
    matrix={g:{p:0 for p in labels} for g in labels}
    for r in rows: matrix[r["gold_label"]][r["predicted_label"]]+=1
    return {"count":n,"correct":correct,"exact_accuracy":correct/n if n else None,"confusion_matrix":matrix}

def evaluate():
    cases=load_cases(); results=[]
    for c in cases:
        predicted=classify(c)
        results.append({"case_id":c["case_id"],"requirement_type":c["requirement_type"],"split":c["split"],"gold_label":c["gold_label"],"predicted_label":predicted,"correct":predicted==c["gold_label"],"independent_adjudication_status":c["independent_adjudication_status"]})
    by_type={}
    for t in sorted({r["requirement_type"] for r in results}):
        by_type[t]={split:metrics([r for r in results if r["requirement_type"]==t and r["split"]==split]) for split in ("development","locked_holdout")}
        by_type[t]["all"]=metrics([r for r in results if r["requirement_type"]==t])
    return {"dataset_sha256":fingerprint(),"total_cases":len(results),"cases_per_type":20,"requirement_types":len(by_type),"independently_adjudicated_cases":sum(r["independent_adjudication_status"]=="complete" for r in results),"by_requirement_type":by_type,"overall":{split:metrics([r for r in results if r["split"]==split]) for split in ("development","locked_holdout")},"results":results,"interpretation":"Metrics are against provisional synthetic scenario labels, not independent human adjudication or production accuracy."}

def main():
    report=evaluate()
    out=ROOT/".poc"/"evaluation"/"requirements"/"latest-report.json"
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="results"},indent=2))
    print(f"Detailed report: {out.relative_to(ROOT)}")
if __name__=="__main__": main()

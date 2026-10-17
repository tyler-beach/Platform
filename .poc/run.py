#!/usr/bin/env python3
"""Executable, audited ADR-deviation PoC. Only the model decision is mocked."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from store import CsvStore
import model
import confidence

SUFFIXES={".go",".py",".pyi",".js",".jsx",".mjs",".cjs",".ts",".tsx",".java"}
SKIP={".git","node_modules","vendor","target","build",".venv","venv","__pycache__"}
OUTCOMES={"supported_deviation","potential_deviation","no_deviation_found","inconclusive"}
def now(): return datetime.now(timezone.utc).isoformat()
def sha(data: bytes): return hashlib.sha256(data).hexdigest()
def write_json(p: Path,v: Any):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
def run_cmd(cmd,cwd=None):
    r=subprocess.run(cmd,cwd=str(cwd) if cwd else None,text=True,capture_output=True)
    if r.stdout: print(r.stdout,end="")
    if r.stderr: print(r.stderr[-4000:],file=sys.stderr)
    if r.returncode: raise RuntimeError("Command failed: "+ " ".join(cmd)+"\n"+r.stderr[-6000:])
def under(p: Path,base: Path):
    try:p.resolve().relative_to(base.resolve());return True
    except ValueError:return False
def files_under(root):
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUFFIXES and not any(x in SKIP for x in p.parts))
def basename(q):
    s=q.split("::")[-1].rsplit(".",1)[-1]
    return re.split(r"[:(]",s,1)[0].strip()
def semantic(language,source,out):
    out.parent.mkdir(parents=True,exist_ok=True)
    if language=="go":
        go_mod=Path(".poc/analyzers/go").resolve()
        if not (go_mod/"go.sum").is_file(): run_cmd(["go","mod","tidy"],go_mod)
        run_cmd(["go","run",".","--root",str(source),"--out",str(out)],go_mod)
    elif language in {"typescript","javascript"}: run_cmd(["node",str(Path(".poc/analyzers/typescript/callgraph.cjs").resolve()),"--root",str(source),"--out",str(out),"--language",language])
    elif language=="python": run_cmd([sys.executable,str(Path(".poc/analyzers/python_callgraph.py").resolve()),"--root",str(source),"--out",str(out)])
    elif language=="java":
        classes=out.parent/"java-classes";classes.mkdir(parents=True,exist_ok=True)
        run_cmd(["javac","-d",str(classes),str(Path(".poc/analyzers/java/CallGraph.java").resolve())])
        cmd=["java","-cp",str(classes),"CallGraph","--root",str(source),"--out",str(out)]
        project_cp=os.environ.get("JAVA_POC_CLASSPATH","")
        if project_cp: cmd.extend(["--classpath",project_cp])
        run_cmd(cmd)
    else: raise ValueError("unsupported language "+language)
    return json.loads(out.read_text(encoding="utf-8"))
def bind_graph(g,root_name,run_id):
    funcs=g.get("functions",[]);edges=g.get("edges",[])
    old_to_new={f.get("symbol_id",""):run_id+":"+f.get("symbol_id","") for f in funcs}
    for f in funcs: f["symbol_id"]=old_to_new[f.get("symbol_id","")]
    for i,e in enumerate(edges,1):
        e["edge_id"]=run_id+":"+str(e.get("edge_id") or ("edge-%05d"%i))
        for col in ("caller_symbol_id","callee_symbol_id"):
            old=e.get(col,"")
            if old: e[col]=old_to_new.get(old,run_id+":"+old)
    roots=sorted(f["symbol_id"] for f in funcs if basename(f.get("qualified_name",""))==root_name)
    byid={f["symbol_id"]:f for f in funcs}
    resolved={"resolved","resolved_static","resolved_approximate"}
    adj={}
    for e in edges:
        if e.get("resolution_status") in resolved and e.get("callee_symbol_id") in byid:
            adj.setdefault(e.get("caller_symbol_id"),[]).append(e)
    reached=set(roots);paths={x:[] for x in roots};queue=list(roots)
    while queue:
        cur=queue.pop(0)
        for e in adj.get(cur,[]):
            nxt=e["callee_symbol_id"]
            if nxt not in reached:
                reached.add(nxt);paths[nxt]=paths.get(cur,[])+[e["edge_id"]];queue.append(nxt)
    for f in funcs:
        f["reachable_from_entry"]=f["symbol_id"] in reached
        f["entry_path_edge_ids"]=paths.get(f["symbol_id"],[])
    for e in edges:
        e["reachable_from_entry"]=e.get("caller_symbol_id") in reached
        e["is_transitive"]=e.get("caller_symbol_id") in reached and e.get("caller_symbol_id") not in roots
        caller=byid.get(e.get("caller_symbol_id",""),{});callee=byid.get(e.get("callee_symbol_id",""),{})
        e.setdefault("caller_qualified_name",caller.get("qualified_name",e.get("caller_symbol_id","")))
        e.setdefault("callee_qualified_name",callee.get("qualified_name",e.get("callee_qualified_name",e.get("callee_symbol_id",""))))
        e.setdefault("resolution_basis",g.get("resolver","language_resolver"));e.setdefault("dispatch_kind","unknown")
    g.update({"entry_function":root_name,"entry_symbol_ids":roots,"reachable_symbol_ids":sorted(reached),"reachable_functions":[f for f in funcs if f["symbol_id"] in reached],"reachable_edges":[e for e in edges if e["reachable_from_entry"]],"entry_resolution":"resolved" if roots else "unresolved"})
    return g

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--language",required=True,choices=["go","python","javascript","typescript","java"])
    p.add_argument("--source",required=True);p.add_argument("--root-function",default="Submit")
    p.add_argument("--comparison",required=True,choices=["code-diff","technical-spec","spec-vs-implementation"])
    p.add_argument("--provider",choices=["mock","anthropic"],default=os.getenv("MODEL_PROVIDER","mock"))
    p.add_argument("--run-id",default="local-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    p.add_argument("--db-dir",default=".poc-db");p.add_argument("--out-dir",default="run-data")
    p.add_argument("--spec-path",default=".poc/fixtures/go/technical-spec.md");p.add_argument("--adr-path",default=".poc/fixtures/go/ADR-001.md");p.add_argument("--diff-path",default="")
    p.add_argument("--max-input-tokens",type=int,default=12000);p.add_argument("--max-output-tokens",type=int,default=1000)
    p.add_argument("--repository",default=os.getenv("GITHUB_REPOSITORY","local"));p.add_argument("--workflow-url",default=os.getenv("GITHUB_WORKFLOW_URL",""))
    a=p.parse_args();workspace=Path.cwd().resolve();source=Path(a.source).resolve()
    if not source.is_dir() or not under(source,workspace): raise SystemExit("--source must be an existing directory within the checked-out workspace")
    spec=Path(a.spec_path).resolve() if a.spec_path else None;adr=Path(a.adr_path).resolve()
    if not under(adr,workspace) or not adr.is_file(): raise SystemExit("--adr-path must be an existing file in the workspace")
    if a.comparison in {"technical-spec","spec-vs-implementation"} and (not spec or not under(spec,workspace) or not spec.is_file()): raise SystemExit("--spec-path must identify an existing workspace file")
    diff=Path(a.diff_path).resolve() if a.diff_path else ((source/"change.diff").resolve() if (source/"change.diff").is_file() else None)
    if diff and (not under(diff,workspace) or not diff.is_file()): raise SystemExit("--diff-path must identify an existing file in the workspace")
    run_id=re.sub(r"[^A-Za-z0-9_.-]","-",a.run_id)[:100];started=now()
    out=Path(a.out_dir).resolve()/run_id;out.mkdir(parents=True,exist_ok=True)
    store=CsvStore(a.db_dir);events=[]
    provider_model=(os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-5-5") if a.provider=="anthropic" else "deterministic-rules-v1"
    def event(stage,kind,status,details=None):
        events.append(stage+":"+kind+":"+status)
        store.append("run_events",{"event_id":run_id+":event-%04d"%len(events),"run_id":run_id,"timestamp":now(),"stage":stage,"event_type":kind,"status":status,"details_json":details or {}})
    try:
        event("admission","start","running",{"source":str(source.relative_to(workspace)),"comparison":a.comparison,"language":a.language})
        code=files_under(source)
        if not code and a.comparison!="technical-spec": raise RuntimeError("no supported code files under source root")
        input_paths=(code if a.comparison!="technical-spec" else [])+[adr]
        if a.comparison in {"technical-spec","spec-vs-implementation"}: input_paths.append(spec)
        if diff and a.comparison in {"code-diff","spec-vs-implementation"}: input_paths.append(diff)
        unique=[];seen=set()
        for x in input_paths:
            if x and x.resolve() not in seen:unique.append(x.resolve());seen.add(x.resolve())
        digest=hashlib.sha256();artifact_map={};artifact_rows=[]
        for i,path in enumerate(unique,1):
            data=path.read_bytes();display=path.relative_to(workspace).as_posix()
            role="implementation" if path in code else "adr" if path==adr else "technical_spec" if path==spec else "diff"
            aid=f"{run_id}:artifact-{i:04d}";artifact_map[display]=aid
            artifact_rows.append({"artifact_id":aid,"run_id":run_id,"role":role,"path":display,"sha256":sha(data),"byte_length":len(data),"version":"sha256:"+sha(data)})
            digest.update(display.encode());digest.update(b"\0");digest.update(data);digest.update(b"\0")
        input_hash=digest.hexdigest()
        for row in artifact_rows:store.append("artifacts",row)
        event("admission","complete","success",{"artifacts":len(artifact_rows),"input_hash":input_hash})
        syntax_path=out/"tree-sitter.json";event("syntax","start","running")
        run_cmd([sys.executable,str(Path(".poc/syntax_index.py").resolve()),"--root",str(source),"--out",str(syntax_path)])
        syntax=json.loads(syntax_path.read_text(encoding="utf-8"))
        event("syntax","complete","success",{"files":len(syntax["files"]),"errors":sum(len(f["errors"]) for f in syntax["files"])})
        if a.comparison=="technical-spec": graph={"language":a.language,"resolver":"document-only","functions":[],"edges":[],"diagnostics":[]}
        else:
            event("semantic_analysis","start","running",{"resolver":a.language})
            graph=bind_graph(semantic(a.language,source,out/"callgraph.json"),a.root_function,run_id)
            write_json(out/"callgraph.json",graph)
            event("semantic_analysis","complete","success",{"resolver":graph.get("resolver"),"functions":len(graph.get("functions",[])),"edges":len(graph.get("edges",[])),"reachable_functions":len(graph.get("reachable_functions",[])),"root_resolved":graph.get("entry_resolution")=="resolved"})
        for f in graph.get("functions",[]):
            store.append("symbols",{"symbol_id":f.get("symbol_id"),"run_id":run_id,"language":a.language,"qualified_name":f.get("qualified_name"),"symbol_kind":f.get("symbol_kind"),"signature":f.get("signature"),"declared_type":f.get("declared_type"),"path":f.get("path"),"start_line":f.get("start_line"),"end_line":f.get("end_line"),"resolver":f.get("resolver",graph.get("resolver")),"resolution_status":f.get("resolution_status","resolved")})
        for e in graph.get("edges",[]):
            store.append("call_edges",{"edge_id":e.get("edge_id"),"run_id":run_id,"caller_symbol_id":e.get("caller_symbol_id"),"callee_symbol_id":e.get("callee_symbol_id"),"call_expression":e.get("call_expression"),"path":e.get("path"),"line":e.get("line"),"resolution_status":e.get("resolution_status"),"resolution_basis":e.get("resolution_basis"),"dispatch_kind":e.get("dispatch_kind"),"is_transitive":e.get("is_transitive",False)})
        docs=[("adr",adr)]
        if a.comparison in {"technical-spec","spec-vs-implementation"}:docs.append(("technical_spec",spec))
        evidence=[];requirements=[];n=0;norm=re.compile(r"\b(must|must not|shall|shall not|required|prohibited|should not|never)\b",re.I)
        for role,path in docs:
            text=path.read_text(encoding="utf-8",errors="replace");display=path.relative_to(workspace).as_posix()
            for line_no,line in enumerate(text.splitlines(),1):
                if norm.search(line):
                    n+=1;ev={"evidence_id":f"{run_id}:evidence-{n:05d}","run_id":run_id,"evidence_type":"normative_requirement","artifact_id":artifact_map.get(display,""),"symbol_id":"","edge_id":"","claim":"Normative requirement extracted from "+role,"excerpt":line.strip(),"path":display,"start_line":line_no,"end_line":line_no,"sha256":sha(line.strip().encode("utf-8"))}
                    evidence.append(ev);requirements.append({"evidence_id":ev["evidence_id"],"source":role,"line":line_no,"text":line.strip()})
        for e in graph.get("edges",[]):
            if not e.get("reachable_from_entry"):continue
            rel=e.get("path","");ln=int(e.get("line") or 0);src=(source/rel).resolve() if rel else None;excerpt=""
            if src and src.is_file():
                lines=src.read_text(encoding="utf-8",errors="replace").splitlines()
                if 1<=ln<=len(lines):excerpt=lines[ln-1].strip()
            n+=1
            try:display=(source/rel).resolve().relative_to(workspace).as_posix()
            except ValueError:display=rel
            status=e.get("resolution_status","unresolved")
            ev={"evidence_id":f"{run_id}:evidence-{n:05d}","run_id":run_id,"evidence_type":"resolved_call_edge" if status.startswith("resolved") else "unresolved_call_edge","artifact_id":artifact_map.get(display,""),"symbol_id":e.get("caller_symbol_id",""),"edge_id":e.get("edge_id",""),"claim":f"Call edge {status} ({e.get('resolution_basis')}) from {e.get('caller_qualified_name')} to {e.get('callee_qualified_name')}","excerpt":excerpt or e.get("call_expression",""),"path":display,"start_line":ln,"end_line":ln,"sha256":sha(excerpt.encode()) if excerpt else ""}
            evidence.append(ev)
        diff_text=""
        if diff and a.comparison in {"code-diff","spec-vs-implementation"}:
            diff_text=diff.read_text(encoding="utf-8",errors="replace")
            display=diff.relative_to(workspace).as_posix()
            for ln,line in enumerate(diff_text.splitlines(),1):
                if line.startswith(("+","-")) and not line.startswith(("+++","---")):
                    n+=1;evidence.append({"evidence_id":f"{run_id}:evidence-{n:05d}","run_id":run_id,"evidence_type":"diff_line","artifact_id":artifact_map.get(display,""),"symbol_id":"","edge_id":"","claim":"Added or removed diff line","excerpt":line[:500],"path":display,"start_line":ln,"end_line":ln,"sha256":sha(line.encode())})
        write_json(out/"evidence.json",evidence)
        for ev in evidence:store.append("evidence",ev)
        event("evidence","complete","success",{"evidence":len(evidence),"requirements":len(requirements)})
        entry=", ".join(f.get("qualified_name","") for f in graph.get("functions",[]) if f.get("symbol_id") in graph.get("entry_symbol_ids",[])) or a.root_function
        evidence_index=[{"evidence_id":e["evidence_id"],"evidence_type":e["evidence_type"],"claim":e["claim"],"excerpt":e["excerpt"],"path":e["path"],"start_line":e["start_line"],"edge_id":e["edge_id"],"artifact_id":e["artifact_id"],"sha256":e["sha256"]} for e in evidence]
        context={"comparison":a.comparison,"root_symbol":entry,"requirements":requirements,"graph_evidence":{"functions":graph.get("reachable_functions",[]),"edges":graph.get("reachable_edges",[]),"diagnostics":graph.get("diagnostics",[]),"syntax_diagnostics":[{"path":f.get("path"),"errors":f.get("errors")} for f in syntax["files"] if f.get("has_syntax_errors")]},"graph":graph,"evidence":evidence_index,"evidence_items":evidence_index,"diff_excerpt":diff_text[:12000]}
        prompt=model.render_prompt(context);reservation=run_id+":budget"
        event("budget","token_count_start","running",{"provider":a.provider})
        try:
            token_preflight=model.count_input_tokens(a.provider,context)
            est=int(token_preflight["input_tokens"])
        except Exception as ex:
            store.append("llm_transactions",{"transaction_id":run_id+":preflight","run_id":run_id,"provider":a.provider,"model":provider_model,"request_id":"","status":"token_count_failed","prompt_sha256":sha(prompt.encode()),"input_chars":len(prompt),"error":str(ex)[:2000],"created_at":now()})
            event("budget","token_count_complete","failed",{"error":str(ex)[:1000]})
            raise
        store.append("llm_transactions",{"transaction_id":run_id+":preflight","run_id":run_id,"provider":a.provider,"model":token_preflight.get("model",provider_model),"request_id":token_preflight.get("request_id",""),"status":"token_counted","prompt_sha256":token_preflight.get("prompt_sha256",sha(prompt.encode())),"input_chars":token_preflight.get("input_chars",len(prompt)),"estimated_input_tokens":est,"actual_input_tokens":est if a.provider=="anthropic" else "","duration_ms":token_preflight.get("duration_ms"),"error":"","created_at":token_preflight.get("created_at",now())})
        event("budget","token_count_complete","success",{"input_tokens":est,"method":token_preflight.get("method")})
        allowed=est<=a.max_input_tokens
        store.append("budget_reservations",{"reservation_id":reservation,"run_id":run_id,"provider":a.provider,"model":provider_model,"max_input_tokens":a.max_input_tokens,"max_output_tokens":a.max_output_tokens,"estimated_input_tokens":est,"reserved_at":now(),"status":"approved" if allowed else "denied"})
        event("budget","decision","approved" if allowed else "denied",{"estimated_input_tokens":est,"max_input_tokens":a.max_input_tokens,"max_output_tokens":a.max_output_tokens})
        if not allowed:raise RuntimeError(f"estimated prompt tokens {est} exceeds limit {a.max_input_tokens}; model call skipped")
        event("model","start","running",{"provider":a.provider,"model":provider_model})
        try:envelope=model.assess(a.provider,context,a.max_output_tokens)
        except Exception as ex:
            store.append("llm_transactions",{"transaction_id":run_id+":llm","run_id":run_id,"provider":a.provider,"model":provider_model,"status":"failed","prompt_sha256":sha(prompt.encode()),"input_chars":len(prompt),"estimated_input_tokens":est,"error":str(ex)[:2000],"created_at":now()})
            event("model","complete","failed",{"error":str(ex)[:800]});raise
        model_candidate=dict(envelope["assessment"]);model_self_confidence=model_candidate.get("confidence");model_proposed_outcome=model_candidate.get("outcome","inconclusive");cand=dict(model_candidate);schema_errors=[]
        if cand.get("outcome") not in OUTCOMES:schema_errors.append("invalid outcome")
        if not isinstance(cand.get("summary"),str) or not cand["summary"].strip():schema_errors.append("invalid summary")
        if not isinstance(cand.get("rationale"),str) or not cand["rationale"].strip():schema_errors.append("invalid rationale")
        valid_ids={e["evidence_id"] for e in evidence}
        if not isinstance(cand.get("evidence_ids"),list):schema_errors.append("evidence_ids must be a list")
        elif any(x not in valid_ids for x in cand["evidence_ids"]):schema_errors.append("candidate cited evidence not emitted by this run")
        if not isinstance(cand.get("limitations"),list):schema_errors.append("limitations must be a list")
        if not isinstance(cand.get("evidence_links"),list):
            schema_errors.append("evidence_links must be an array")
        else:
            evidence_lookup={e["evidence_id"]:e for e in evidence}
            cited_set=set(cand.get("evidence_ids",[])) if isinstance(cand.get("evidence_ids"),list) else set()
            for link in cand.get("evidence_links",[]):
                if not isinstance(link,dict):
                    schema_errors.append("each evidence link must be an object"); continue
                req_ev=evidence_lookup.get(link.get("requirement_evidence_id"))
                obs_ev=evidence_lookup.get(link.get("observation_evidence_id"))
                if req_ev is None or req_ev.get("evidence_type")!="normative_requirement":
                    schema_errors.append("evidence link requirement_evidence_id must reference a normative requirement")
                if obs_ev is None or obs_ev.get("evidence_type") not in {"resolved_call_edge","unresolved_call_edge","diff_line"}:
                    schema_errors.append("evidence link observation_evidence_id must reference a call edge or diff line")
                if link.get("relationship") not in {"contradicts","consistent_with","uncertain"}:
                    schema_errors.append("evidence link relationship is invalid")
                if not isinstance(link.get("explanation"),str) or not link.get("explanation","").strip():
                    schema_errors.append("evidence link explanation must be non-empty")
                if link.get("requirement_evidence_id") not in cited_set or link.get("observation_evidence_id") not in cited_set:
                    schema_errors.append("evidence link endpoints must also appear in evidence_ids")
        try:
            if not 0<=float(cand.get("confidence"))<=1:schema_errors.append("confidence outside [0,1]")
        except (TypeError,ValueError):schema_errors.append("confidence is not numeric")
        validation="valid" if not schema_errors else "invalid"
        store.append("llm_transactions",{"transaction_id":run_id+":llm","run_id":run_id,"provider":envelope["provider"],"model":envelope["model"],"request_id":envelope.get("request_id"),"status":"success" if not schema_errors else "rejected","prompt_sha256":envelope["prompt_sha256"],"input_chars":envelope["input_chars"],"output_chars":envelope["output_chars"],"estimated_input_tokens":est,"actual_input_tokens":envelope.get("input_tokens"),"actual_output_tokens":envelope.get("output_tokens"),"duration_ms":envelope.get("duration_ms"),"error":"; ".join(schema_errors),"created_at":envelope.get("created_at")})
        store.append("budget_reservations",{"reservation_id":reservation,"run_id":run_id,"provider":a.provider,"model":envelope["model"],"max_input_tokens":a.max_input_tokens,"max_output_tokens":a.max_output_tokens,"estimated_input_tokens":est,"reserved_at":now(),"status":"completed" if not schema_errors else "rejected","actual_input_tokens":envelope.get("input_tokens"),"actual_output_tokens":envelope.get("output_tokens")})
        if schema_errors:
            cand={"outcome":"inconclusive","summary":"Model candidate rejected by deterministic validation","rationale":"Candidate did not pass schema/evidence validation: "+"; ".join(schema_errors),"evidence_ids":[],"limitations":["The model candidate was not accepted by the application validator."],"confidence":0.0}
        score_outcome=model_proposed_outcome if not schema_errors and model_proposed_outcome in OUTCOMES else "inconclusive"
        confidence_result=confidence.score_assessment(graph=graph,syntax=syntax,evidence=evidence,artifact_rows=artifact_rows,cited_ids=cand.get("evidence_ids",[]),evidence_links=cand.get("evidence_links",[]),proposed_outcome=score_outcome)
        confidence_result["model_self_reported_confidence"]=model_self_confidence if isinstance(model_self_confidence,(int,float)) else None
        confidence_result["proposed_outcome"]=model_proposed_outcome
        if not schema_errors:
            cand["model_proposed_outcome"]=model_proposed_outcome
            cand["model_self_reported_confidence"]=model_self_confidence
            cand["confidence"]=confidence_result["score"]
            cand["outcome"]=confidence_result["accepted_outcome"]
            for guardrail in confidence_result["guardrails"]:
                if guardrail not in cand["limitations"]: cand["limitations"].append(guardrail)
            if cand["outcome"]!=model_proposed_outcome:
                cand["rationale"] += " Deterministic evidence gates downgraded the model-proposed outcome: "+ "; ".join(confidence_result["guardrails"])
        event("model","complete","success" if not schema_errors else "rejected",{"model":envelope["model"],"proposed_outcome":model_proposed_outcome,"accepted_outcome":cand["outcome"],"evidence_strength_score":confidence_result["score"],"evidence_strength_band":confidence_result["band"],"model_self_reported_confidence":model_self_confidence,"validation":validation,"input_tokens":envelope.get("input_tokens"),"output_tokens":envelope.get("output_tokens")})
        write_json(out/"tree-sitter.json",syntax);write_json(out/"callgraph.json",graph);write_json(out/"evidence.json",evidence)
        write_json(out/"confidence.json",confidence_result)
        write_json(out/"model-response.json",{"metadata":{k:v for k,v in envelope.items() if k!="assessment"},"model_candidate":model_candidate,"accepted_assessment":cand,"confidence":confidence_result,"validation_status":validation,"validation_errors":schema_errors})
        assessment_id=run_id+":confidence"
        component_summary=[{"dimension":x["dimension"],"score":x["score"],"weight":x["weight"],"weighted_contribution":x["weighted_contribution"]} for x in confidence_result["components"]]
        store.append("confidence_assessments",{"assessment_id":assessment_id,"run_id":run_id,"algorithm_version":confidence_result["algorithm_version"],"proposed_outcome":model_proposed_outcome,"accepted_outcome":cand["outcome"],"score_0_to_100":confidence_result["score_0_to_100"],"score_0_to_1":confidence_result["score"],"score_band":confidence_result["band"],"calibrated_probability":False,"model_self_reported_confidence":model_self_confidence,"component_scores_json":component_summary,"caps_json":confidence_result["caps"],"guardrails_json":confidence_result["guardrails"],"principle":confidence_result["principle"],"evidence_ids_json":cand.get("evidence_ids",[]),"created_at":now()})
        for item in confidence_result["components"]:
            store.append("confidence_components",{"component_id":assessment_id+":"+item["dimension"],"assessment_id":assessment_id,"run_id":run_id,"dimension":item["dimension"],"score":item["score"],"weight":item["weight"],"weighted_contribution":item["weighted_contribution"],"explanation":item["explanation"],"evidence_ids_json":item["evidence_ids"],"details_json":item["details"],"algorithm_version":confidence_result["algorithm_version"],"created_at":now()})
        for link_num,link in enumerate(confidence_result["evidence_links"],1):
            store.append("assessment_evidence_links",{"link_id":assessment_id+":link-%03d"%link_num,"run_id":run_id,"finding_id":run_id+":finding","requirement_evidence_id":link.get("requirement_evidence_id"),"observation_evidence_id":link.get("observation_evidence_id"),"relationship":link.get("relationship"),"explanation":link.get("explanation"),"validation_status":"valid","created_at":now()})
        for link_num,invalid in enumerate(confidence_result["invalid_evidence_links"],len(confidence_result["evidence_links"])+1):
            link=invalid.get("link",{})
            store.append("assessment_evidence_links",{"link_id":assessment_id+":link-%03d"%link_num,"run_id":run_id,"finding_id":run_id+":finding","requirement_evidence_id":link.get("requirement_evidence_id"),"observation_evidence_id":link.get("observation_evidence_id"),"relationship":link.get("relationship"),"explanation":link.get("explanation"),"validation_status":"invalid: "+invalid.get("reason","validation failed"),"created_at":now()})
        store.append("findings",{"finding_id":run_id+":finding","run_id":run_id,"outcome":cand["outcome"],"confidence":confidence_result["score"],"summary":cand["summary"],"rationale":cand["rationale"],"evidence_ids_json":cand.get("evidence_ids",[]),"limitations_json":cand.get("limitations",[]),"validation_status":validation,"created_at":now()})
        status="complete" if not schema_errors else "model_response_rejected";store.append("runs",{"run_id":run_id,"started_at":started,"completed_at":now(),"github_run_id":os.getenv("GITHUB_RUN_ID",""),"repository":a.repository,"comparison":a.comparison,"language":a.language,"source_path":source.relative_to(workspace).as_posix(),"root_function":a.root_function,"model_provider":a.provider,"model":envelope["model"],"result":cand["outcome"],"status":status,"input_hash":input_hash,"workflow_url":a.workflow_url})
        report=["# ADR Deviation Analysis PoC","","- Run ID: "+run_id,"- Comparison: "+a.comparison,"- Language: "+a.language,"- Resolver: "+str(graph.get("resolver","document-only")),"- Entry symbol: "+entry,"- Functions: "+str(len(graph.get("functions",[]))),"- Direct call edges: "+str(len(graph.get("edges",[]))),"- Functions reachable from entry: "+str(len(graph.get("reachable_functions",[]))),"- Evidence items: "+str(len(evidence)),"- Model: "+envelope["provider"]+" / "+envelope["model"],"- Candidate validation: "+validation,"","## Finding","","**Model-proposed outcome:** "+str(model_proposed_outcome),"","**Accepted outcome:** "+cand["outcome"],"","**Summary:** "+cand["summary"],"","**Rationale:** "+cand["rationale"],"","","## Evidence-strength score","","**Score:** "+str(confidence_result["score_0_to_100"])+"/100 ("+confidence_result["band"]+"). This is a deterministic evidence-support score, not a calibrated probability.","","**Model self-reported confidence:** "+str(model_self_confidence)+" (recorded for inspection only; it does not contribute to the evidence-strength score).","","**Scoring algorithm:** "+confidence_result["algorithm_version"],"","| Dimension | Score | Weight | Contribution | Why |","|---|---:|---:|---:|---|"]
        for component in confidence_result["components"]:
            report.append("| "+component["dimension"].replace("_"," ")+" | "+str(round(component["score"]*100,1))+" | "+str(round(component["weight"]*100,1))+"% | "+str(round(component["weighted_contribution"]*100,1))+" | "+component["explanation"].replace("|","\\|")+" |")
        if confidence_result["caps"] or confidence_result["guardrails"]:
            report += ["","","### Scoring caps and outcome guardrails",""] + ["- "+x for x in confidence_result["caps"]+confidence_result["guardrails"]]
        report += ["","","### Requirement-to-observation links",""]
        evidence_lookup={e["evidence_id"]:e for e in evidence}
        if confidence_result["evidence_links"]:
            for link in confidence_result["evidence_links"]:
                req_ev=evidence_lookup.get(link.get("requirement_evidence_id"),{})
                obs_ev=evidence_lookup.get(link.get("observation_evidence_id"),{})
                report.append("- **"+link.get("relationship","uncertain")+"** — requirement "+str(link.get("requirement_evidence_id"))+" ("+str(req_ev.get("path",""))+":"+str(req_ev.get("start_line",""))+"): "+str(req_ev.get("excerpt",""))+"; observation "+str(link.get("observation_evidence_id"))+" ("+str(obs_ev.get("path",""))+":"+str(obs_ev.get("start_line",""))+"): "+str(obs_ev.get("excerpt",""))+". Explanation: "+str(link.get("explanation","")))
        else:
            report.append("- No valid requirement-to-observation links were produced.")
        report += ["","","### Evidence cited",""]
        report += ["- "+x for x in cand.get("evidence_ids",[])] or ["- No evidence cited."]
        report += ["","","### Cited evidence details",""]
        for eid in cand.get("evidence_ids",[]):
            ev=evidence_lookup.get(eid)
            if ev:
                report.append("- **"+eid+"** ("+str(ev.get("evidence_type"))+") — "+str(ev.get("path"))+":"+str(ev.get("start_line"))+" — "+str(ev.get("claim"))+"; excerpt: "+str(ev.get("excerpt",""))+"; artifact: "+str(ev.get("artifact_id"))+"; excerpt SHA-256: "+str(ev.get("sha256"))+".")
        report += ["","## Limitations",""]+["- "+x for x in cand["limitations"]]+["","","CSV audit tables: "+str(Path(a.db_dir))+"/","Input SHA-256: "+input_hash,""]
        (out/"report.md").write_text("\n".join(report),encoding="utf-8")
        event("report","complete","success",{"outcome":cand["outcome"],"out_dir":str(out)})
        print("\n".join(report))
    except Exception as ex:
        try:
            event("pipeline","failed","failed",{"error":str(ex)[:1500]})
            store.append("runs",{"run_id":run_id,"started_at":started,"completed_at":now(),"github_run_id":os.getenv("GITHUB_RUN_ID",""),"repository":a.repository,"comparison":a.comparison,"language":a.language,"source_path":str(source),"root_function":a.root_function,"model_provider":a.provider,"model":provider_model,"result":"inconclusive","status":"failed","workflow_url":a.workflow_url})
        except Exception:pass
        write_json(out/"failure.json",{"run_id":run_id,"error":str(ex),"timestamp":now()})
        print("PoC run failed: "+str(ex),file=sys.stderr);raise SystemExit(1)
if __name__=="__main__":main()

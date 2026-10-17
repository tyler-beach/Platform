#!/usr/bin/env python3
"""Shared Tree-sitter syntax/byte-span inventory across supported languages."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from tree_sitter_language_pack import get_parser

EXTENSIONS={".go":"go",".py":"python",".pyi":"python",".js":"javascript",".jsx":"javascript",".mjs":"javascript",".cjs":"javascript",".ts":"typescript",".tsx":"tsx",".java":"java"}
EXCLUDE={".git","node_modules","vendor","target","build",".venv","venv","__pycache__"}
def main():
    p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--out",required=True);a=p.parse_args()
    root=Path(a.root).resolve();files=[];errors=[]
    for path in sorted(x for x in root.rglob("*") if x.is_file() and x.suffix.lower() in EXTENSIONS and not any(part in EXCLUDE for part in x.parts)):
        lang=EXTENSIONS[path.suffix.lower()]
        try:
            data=path.read_bytes();parser=get_parser(lang);tree=parser.parse(data);root_node=tree.root_node
            stack=[root_node];error_nodes=[];nodes=0;calls=0;funcs=0
            while stack:
                n=stack.pop();nodes+=1
                if n.type=="ERROR" or n.is_missing:
                    error_nodes.append({"node_type":n.type,"start_byte":n.start_byte,"end_byte":n.end_byte,"start_line":n.start_point.row+1,"start_column":n.start_point.column+1,"excerpt":data[n.start_byte:min(n.end_byte,n.start_byte+180)].decode("utf-8",errors="replace")})
                if "call" in n.type or n.type in {"method_invocation","call_expression"}: calls+=1
                if "function" in n.type or n.type in {"method_declaration","method_definition","function_definition"}: funcs+=1
                stack.extend(reversed(n.children))
            rel=path.relative_to(root).as_posix()
            files.append({"path":rel,"language":lang,"sha256":hashlib.sha256(data).hexdigest(),"byte_length":len(data),"node_count":nodes,"call_node_count":calls,"function_node_count":funcs,"has_syntax_errors":bool(error_nodes),"errors":error_nodes[:40]})
        except Exception as ex:
            errors.append({"path":str(path),"language":lang,"error":str(ex)})
    result={"root":str(root),"parser":"Tree-sitter language pack","files":files,"diagnostics":errors}
    Path(a.out).parent.mkdir(parents=True,exist_ok=True);Path(a.out).write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(f"Tree-sitter syntax inventory: {len(files)} source files, {sum(len(x['errors']) for x in files)} parse diagnostics, {len(errors)} parser failures")
    if errors: raise SystemExit("One or more source files could not be parsed")
if __name__=="__main__": main()

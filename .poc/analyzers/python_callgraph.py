#!/usr/bin/env python3
"""Python scope/import/type-hint index and intra-project static call graph."""
from __future__ import annotations
import argparse, ast, json, os
from pathlib import Path
from typing import Any

def dump(value: Any, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
def dotted(node: ast.AST | None) -> str:
    if node is None: return ""
    if isinstance(node, ast.Name): return node.id
    if isinstance(node, ast.Attribute): return dotted(node.value) + "." + node.attr
    if isinstance(node, ast.Call): return dotted(node.func)
    return ""
def module_name(rel: str) -> str:
    s = rel.replace("/", ".")
    for suffix in (".py", ".pyi"): 
        if s.endswith(suffix): s = s[:-len(suffix)]
    return s[:-9] if s.endswith(".__init__") else s
class Analyzer:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.modules: dict[str, dict[str, Any]] = {}
        self.functions: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.node_info: dict[int, dict[str, Any]] = {}
        self.func_by_id: dict[str, dict[str, Any]] = {}
        self.module_funcs: dict[tuple[str,str], dict[str,Any]] = {}
        self.class_methods: dict[tuple[str,str], dict[str,Any]] = {}
        self.class_names: set[str] = set()
        self.module_imports: dict[str, dict[str,str]] = {}
        self.from_imports: dict[str, dict[str,str]] = {}
        self.class_bases: dict[tuple[str,str], list[str]] = {}
        self.class_attrs: dict[tuple[str,str,str], str] = {}
        self.parse_errors: list[str] = []
    def files(self):
        return sorted([p for p in self.root.rglob("*.py") if not any(x in {"venv",".venv","site-packages","__pycache__",".git"} for x in p.parts)])
    def scan(self):
        for p in self.files():
            rel=p.relative_to(self.root).as_posix(); mod=module_name(rel)
            try: src=p.read_text(encoding="utf-8"); tree=ast.parse(src,filename=rel)
            except (SyntaxError,UnicodeDecodeError) as e:
                self.parse_errors.append(f"{rel}:{getattr(e,'lineno',0)}: {e}")
                continue
            self.modules[mod]={"path":rel,"source":src,"tree":tree}
            imports={}; froms={}
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):
                    for a in n.names: imports[a.asname or a.name.split(".")[0]]=a.name
                elif isinstance(n,ast.ImportFrom):
                    base=("."*n.level)+(n.module or "")
                    for a in n.names: froms[a.asname or a.name]=base+"."+a.name
            self.module_imports[mod]=imports; self.from_imports[mod]=froms
        for mod, record in self.modules.items():
            tree=record["tree"]; rel=record["path"]
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    parents=[]
                    # Derive class nesting by traversing source structure rather than line-order guesses.
                    cls=self.enclosing_class(tree,node)
                    name=(cls+"."+node.name) if cls else node.name
                    ident=f"py:{rel}:{node.lineno}:{name}"
                    ann=ast.unparse(node.returns) if node.returns else ""
                    symbol={"symbol_id":ident,"qualified_name":mod+"."+name,"symbol_kind":"method" if cls else "function","signature":ast.unparse(node.args),"declared_type":ann,"path":rel,"start_line":node.lineno,"end_line":getattr(node,"end_lineno",node.lineno),"resolver":"python_ast_scope_import_index","resolution_status":"resolved"}
                    self.functions.append(symbol); self.node_info[id(node)]={"symbol":symbol,"node":node,"module":mod,"class":cls}
                    self.func_by_id[ident]=symbol
                    if cls: self.class_methods[(mod,cls+"."+node.name)]=symbol
                    else: self.module_funcs[(mod,node.name)]=symbol
                elif isinstance(node,ast.ClassDef):
                    cls=self.enclosing_class(tree,node)
                    full=(cls+"." if cls else "")+node.name
                    self.class_names.add(mod+"."+full)
                    self.class_bases[(mod,full)]=[dotted(b) for b in node.bases]
        self.index_constructor_attributes()
        for mod, record in self.modules.items():
            for fn in ast.walk(record["tree"]):
                if isinstance(fn,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    meta=self.node_info.get(id(fn))
                    if not meta: continue
                    Calls(self,meta).visit(fn)
        return {"language":"python","resolver":"Python AST + scope/import/type-hint/constructor index","functions":self.functions,"edges":self.edges,"diagnostics":self.parse_errors}
    def enclosing_class(self, tree: ast.AST, target: ast.AST) -> str:
        # Find the narrowest ClassDef which contains the target node by source span.
        choices=[]
        for n in ast.walk(tree):
            if isinstance(n,ast.ClassDef) and n.lineno <= getattr(target,"lineno",0) <= getattr(n,"end_lineno",n.lineno):
                choices.append(n)
        if not choices: return ""
        return min(choices,key=lambda n:getattr(n,"end_lineno",n.lineno)-n.lineno).name
    def index_constructor_attributes(self):
        for mod, rec in self.modules.items():
            for cls in [n for n in ast.walk(rec["tree"]) if isinstance(n,ast.ClassDef)]:
                for n in ast.walk(cls):
                    if isinstance(n,ast.Assign):
                        for target in n.targets:
                            if isinstance(target,ast.Attribute) and isinstance(target.value,ast.Name) and target.value.id=="self":
                                typ=dotted(n.value.func) if isinstance(n.value,ast.Call) else ""
                                if typ: self.class_attrs[(mod,cls.name,target.attr)]=typ.split(".")[-1]
                    elif isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Attribute) and isinstance(n.target.value,ast.Name) and n.target.value.id=="self":
                        if n.annotation: self.class_attrs[(mod,cls.name,n.target.attr)]=dotted(n.annotation).split(".")[-1]
    def resolve_module(self, mod: str, path: str) -> str | None:
        if path in self.modules: return path
        # Resolve dotted imports to a Python module in the checked source tree.
        for candidate in (path,mod.rsplit(".",1)[0]+"."+path if "." in mod else path):
            if candidate in self.modules: return candidate
        return None
    def resolve_name(self, mod: str, name: str, cls: str, local_types: dict[str,str]) -> tuple[dict[str,Any]|None,str,str]:
        if name in self.from_imports.get(mod,{}):
            imp=self.from_imports[mod][name]
            base,_,sym=imp.rpartition(".")
            target_mod=self.resolve_module(mod,base)
            if target_mod:
                found=self.module_funcs.get((target_mod,sym)) or self.class_methods.get((target_mod,sym))
                if found: return found,"resolved","python_import_binding"
        if name in self.module_imports.get(mod,{}):
            target_mod=self.resolve_module(mod,self.module_imports[mod][name])
            if target_mod:
                return None,"unresolved_dynamic","python_module_attribute_requires_call_expression"
        return (self.module_funcs.get((mod,name)), "resolved","python_module_scope") if (mod,name) in self.module_funcs else (None,"unresolved_dynamic","python_name_binding_not_proven")
    def resolve_attr(self, mod: str, expr: ast.AST, cls: str, local_types: dict[str,str]) -> tuple[dict[str,Any]|None,str,str]:
        if isinstance(expr,ast.Attribute):
            owner=dotted(expr.value)
            if isinstance(expr.value,ast.Name) and expr.value.id in {"self","cls"} and cls:
                return (self.class_methods.get((mod,cls+"."+expr.attr)), "resolved","python_class_method_binding") if (mod,cls+"."+expr.attr) in self.class_methods else (None,"unresolved_dynamic","python_method_not_found_in_class_index")
            if isinstance(expr.value,ast.Attribute) and isinstance(expr.value.value,ast.Name) and expr.value.value.id in {"self","cls"} and cls:
                typ=self.class_attrs.get((mod,cls,expr.value.attr),"")
                key=(mod,typ+"."+expr.attr) if typ else None
                return (self.class_methods.get(key), "resolved","python_constructor_attribute_type") if key and key in self.class_methods else (None,"unresolved_dynamic","python_receiver_type_not_proven")
            if isinstance(expr.value,ast.Name):
                var=expr.value.id
                typ=local_types.get(var,"")
                key=(mod,typ+"."+expr.attr) if typ else None
                if key and key in self.class_methods: return self.class_methods[key],"resolved","python_local_constructor_or_annotation"
                imp=self.module_imports.get(mod,{}).get(var)
                if imp:
                    target_mod=self.resolve_module(mod,imp)
                    if target_mod and (target_mod,expr.attr) in self.module_funcs:
                        return self.module_funcs[(target_mod,expr.attr)],"resolved","python_imported_module_symbol"
                fromimp=self.from_imports.get(mod,{}).get(var)
                if fromimp:
                    base,_,sym=fromimp.rpartition(".")
                    target_mod=self.resolve_module(mod,base)
                    if target_mod:
                        target=self.class_methods.get((target_mod,sym+"."+expr.attr)) or self.module_funcs.get((target_mod,sym+"."+expr.attr))
                        if target: return target,"resolved","python_imported_class_symbol"
        return None,"unresolved_dynamic","python_dynamic_attribute_or_duck_typed_call"

class Calls(ast.NodeVisitor):
    def __init__(self, analyzer: Analyzer, meta: dict[str,Any]):
        self.a=analyzer; self.meta=meta; self.symbol=meta["symbol"]; self.mod=meta["module"]; self.cls=meta["class"]; self.local_types={}
        node=meta["node"]
        for arg in node.args.args:
            if arg.annotation: self.local_types[arg.arg]=dotted(arg.annotation).split(".")[-1]
        for n in ast.walk(node):
            if isinstance(n,(ast.Assign,ast.AnnAssign)):
                value=n.value
                typ=""
                if isinstance(value,ast.Call): typ=dotted(value.func).split(".")[-1]
                elif isinstance(n,ast.AnnAssign) and n.annotation: typ=dotted(n.annotation).split(".")[-1]
                targets=n.targets if isinstance(n,ast.Assign) else [n.target]
                for t in targets:
                    if isinstance(t,ast.Name) and typ: self.local_types[t.id]=typ
        self.counter=0
    def visit_Call(self,node:ast.Call):
        target=None; status="unresolved_dynamic"; basis="python_call_not_resolved"; expression=dotted(node.func)
        if isinstance(node.func,ast.Name):
            target,status,basis=self.a.resolve_name(self.mod,node.func.id,self.cls,self.local_types)
            # Class construction maps to __init__ when source defines it.
            if target is None and node.func.id and (self.mod,node.func.id+".__init__") in self.a.class_methods:
                target=self.a.class_methods[(self.mod,node.func.id+".__init__")]; status="resolved"; basis="python_constructor_binding"
        else:
            target,status,basis=self.a.resolve_attr(self.mod,node.func,self.cls,self.local_types)
        self.counter+=1
        line=node.lineno
        callee_id=target["symbol_id"] if target else ("unresolved:"+self.symbol["symbol_id"]+":"+str(line)+":"+expression)
        callee_name=target["qualified_name"] if target else expression
        self.a.edges.append({"edge_id":f"py-edge-{len(self.a.edges)+1:05d}","caller_symbol_id":self.symbol["symbol_id"],"callee_symbol_id":callee_id,"caller_qualified_name":self.symbol["qualified_name"],"callee_qualified_name":callee_name,"call_expression":ast.get_source_segment(self.a.modules[self.mod]["source"],node) or expression,"path":self.symbol["path"],"line":line,"resolution_status":status,"resolution_basis":basis,"dispatch_kind":"python_dynamic" if status=="unresolved_dynamic" else "static"})
        self.generic_visit(node)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True); p.add_argument("--out",required=True)
    a=p.parse_args()
    result=Analyzer(Path(a.root)).scan()
    dump(result,a.out)
    print(f"Python semantic analysis: {len(result['functions'])} symbols, {len(result['edges'])} call sites, {len(result['diagnostics'])} parse diagnostics")
if __name__=="__main__": main()

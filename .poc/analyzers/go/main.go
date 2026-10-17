package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"golang.org/x/tools/go/callgraph/cha"
	"golang.org/x/tools/go/packages"
	"golang.org/x/tools/go/ssa"
	"golang.org/x/tools/go/ssa/ssautil"
)

type Function struct {
	ID string `json:"symbol_id"`
	Name string `json:"qualified_name"`
	Kind string `json:"symbol_kind"`
	Signature string `json:"signature"`
	Path string `json:"path"`
	StartLine int `json:"start_line"`
	EndLine int `json:"end_line"`
	Resolver string `json:"resolver"`
	Status string `json:"resolution_status"`
}
type Edge struct {
	ID string `json:"edge_id"`
	Caller string `json:"caller_symbol_id"`
	Callee string `json:"callee_symbol_id"`
	CallerName string `json:"caller_qualified_name"`
	CalleeName string `json:"callee_qualified_name"`
	Expression string `json:"call_expression"`
	Path string `json:"path"`
	Line int `json:"line"`
	Status string `json:"resolution_status"`
	Basis string `json:"resolution_basis"`
	Dispatch string `json:"dispatch_kind"`
}
type Output struct {
	Language string `json:"language"`
	Resolver string `json:"resolver"`
	Functions []Function `json:"functions"`
	Edges []Edge `json:"edges"`
	Diagnostics []string `json:"diagnostics"`
}
func rel(root, file string) string {
	if file == "" { return "" }
	r, err := filepath.Rel(root, file)
	if err != nil || r == ".." || strings.HasPrefix(r, ".."+string(filepath.Separator)) { return "" }
	return filepath.ToSlash(r)
}
func fnName(fn *ssa.Function) string { if fn == nil { return "<unknown>" }; return fn.String() }
func fnKind(fn *ssa.Function) string { if fn != nil && fn.Signature != nil && fn.Signature.Recv() != nil { return "method" }; return "function" }
func main() {
	root := flag.String("root", ".", "directory containing the Go module/packages")
	outPath := flag.String("out", "callgraph.json", "output JSON path")
	flag.Parse()
	absRoot, err := filepath.Abs(*root); if err != nil { fail(err) }
	cfg := &packages.Config{Mode: packages.LoadAllSyntax, Dir: absRoot}
	pkgs, err := packages.Load(cfg, "./..."); if err != nil { fail(err) }
	if len(pkgs)==0 { fail(fmt.Errorf("no Go packages found under %s",absRoot)) }
	diagnostics:=[]string{}
	for _,p:=range pkgs { for _,e:=range p.Errors { diagnostics=append(diagnostics,p.PkgPath+": "+e.Msg) } }
	prog,ssaPkgs:=ssautil.AllPackages(pkgs,ssa.InstantiateGenerics); prog.Build()
	graph:=cha.CallGraph(prog)
	functionsBySSA:=map[*ssa.Function]Function{}
	functionsByID:=map[string]Function{}
	for _,pkg:=range ssaPkgs {
		if pkg==nil { continue }
		for _,member:=range pkg.Members {
			fn,ok:=member.(*ssa.Function);if !ok||fn==nil { continue }
			p:=prog.Fset.Position(fn.Pos()); path:=rel(absRoot,p.Filename);if path=="" {continue}
			id:=path+"::"+fnName(fn)
			f:=Function{ID:id,Name:fnName(fn),Kind:fnKind(fn),Signature:fn.Signature.String(),Path:path,StartLine:p.Line,EndLine:p.Line,Resolver:"go/packages + go/types + SSA + CHA",Status:"resolved"}
			functionsBySSA[fn]=f;functionsByID[id]=f
		}
	}
	for fn:=range graph.Nodes {
		if fn==nil {continue};if _,ok:=functionsBySSA[fn];ok {continue}
		p:=prog.Fset.Position(fn.Pos());path:=rel(absRoot,p.Filename);if path=="" {continue}
		id:=path+"::"+fnName(fn)
		f:=Function{ID:id,Name:fnName(fn),Kind:fnKind(fn),Signature:fn.Signature.String(),Path:path,StartLine:p.Line,EndLine:p.Line,Resolver:"go/packages + go/types + SSA + CHA",Status:"resolved"}
		functionsBySSA[fn]=f;functionsByID[id]=f
	}
	edges:=[]Edge{};seen:=map[string]bool{}
	for _,node:=range graph.Nodes {
		if node==nil||node.Func==nil {continue}
		caller,ok:=functionsBySSA[node.Func];if !ok {continue}
		for _,e:=range node.Out {
			if e==nil||e.Callee==nil||e.Callee.Func==nil {continue}
			callee,inside:=functionsBySSA[e.Callee.Func]
			if !inside { callee=Function{ID:"external::"+fnName(e.Callee.Func),Name:fnName(e.Callee.Func),Kind:fnKind(e.Callee.Func),Signature:e.Callee.Func.Signature.String(),Resolver:"go/types",Status:"external"} }
			p:=token.Position{};expr:="";dispatch:="direct"
			if e.Site!=nil {
				p=prog.Fset.Position(e.Site.Pos());expr=e.Site.String()
				if call,ok:=e.Site.(ssa.CallInstruction);ok&&call.Common()!=nil&&call.Common().IsInvoke(){dispatch="cha"}
			}
			path:=rel(absRoot,p.Filename);key:=caller.ID+"|"+callee.ID+"|"+path+"|"+fmt.Sprint(p.Line)
			if seen[key]{continue};seen[key]=true
			status:="resolved";basis:="go_types_direct_call"
			if dispatch=="cha"{status="resolved_approximate";basis="go_types_cha_interface_dispatch"}
			if !inside{status="external";basis="go_types_external_symbol"}
			edges=append(edges,Edge{ID:fmt.Sprintf("edge-%05d",len(edges)+1),Caller:caller.ID,Callee:callee.ID,CallerName:caller.Name,CalleeName:callee.Name,Expression:expr,Path:path,Line:p.Line,Status:status,Basis:basis,Dispatch:dispatch})
		}
	}
	fnList:=make([]Function,0,len(functionsByID));for _,f:=range functionsByID{fnList=append(fnList,f)}
	sort.Slice(fnList,func(i,j int)bool{if fnList[i].Path==fnList[j].Path{return fnList[i].StartLine<fnList[j].StartLine};return fnList[i].Path<fnList[j].Path})
	sort.Slice(edges,func(i,j int)bool{if edges[i].Path==edges[j].Path{return edges[i].Line<edges[j].Line};return edges[i].Path<edges[j].Path})
	result:=Output{Language:"go",Resolver:"go/packages + go/types + SSA + CHA",Functions:fnList,Edges:edges,Diagnostics:diagnostics}
	data,err:=json.MarshalIndent(result,"","  ");if err!=nil{fail(err)}
	if err:=os.MkdirAll(filepath.Dir(*outPath),0755);err!=nil{fail(err)}
	if err:=os.WriteFile(*outPath,append(data,'\n'),0644);err!=nil{fail(err)}
	fmt.Printf("Go semantic analysis: %d functions, %d call edges, %d package diagnostics\n",len(fnList),len(edges),len(diagnostics))
}
func fail(err error){fmt.Fprintln(os.Stderr,err);os.Exit(1)}

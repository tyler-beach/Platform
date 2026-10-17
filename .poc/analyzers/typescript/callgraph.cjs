#!/usr/bin/env node
"use strict";
const fs=require("fs"),path=require("path"),ts=require("typescript");
const argv=process.argv.slice(2),args={};
for(let i=0;i<argv.length;i++)if(argv[i].startsWith("--"))args[argv[i].slice(2)]=argv[i+1]&&!argv[i+1].startsWith("--")?argv[++i]:"true";
if(!args.root||!args.out){console.error("usage: callgraph.cjs --root DIR --out FILE --language typescript|javascript");process.exit(2);}
const root=path.resolve(args.root),language=args.language||"typescript";
const extensions=new Set([".ts",".tsx",".js",".jsx",".mts",".cts",".mjs",".cjs"]);
function rel(f){const r=path.relative(root,f).split(path.sep).join("/");return r.startsWith("../")?"":r;}
function walk(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(e=>{if(["node_modules",".git","vendor","target","build"].includes(e.name))return [];const p=path.join(dir,e.name);return e.isDirectory()?walk(p):(extensions.has(path.extname(p))?[p]:[]);});}
let options={allowJs:true,checkJs:true,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.NodeNext,moduleResolution:ts.ModuleResolutionKind.NodeNext,skipLibCheck:true,noEmit:true,strict:false};
let roots=walk(root),configPath=ts.findConfigFile(root,ts.sys.fileExists,"tsconfig.json");
if(configPath){const c=ts.readConfigFile(configPath,ts.sys.readFile);if(!c.error){const parsed=ts.parseJsonConfigFileContent(c.config,ts.sys,path.dirname(configPath),{noEmit:true,allowJs:true,checkJs:true});options={...options,...parsed.options,noEmit:true,allowJs:true,checkJs:true};roots=parsed.fileNames.filter(f=>extensions.has(path.extname(f)));}}
const program=ts.createProgram({rootNames:roots,options}),checker=program.getTypeChecker();
const sourceFiles=program.getSourceFiles().filter(sf=>!sf.isDeclarationFile&&sf.fileName.startsWith(root+path.sep));
const functions=[],edges=[],diagnostics=[],nodeToId=new Map(),classes=[];
function line(sf,n){return sf.getLineAndCharacterOfPosition(n.getStart(sf)).line+1;}
function nameOf(n,sf){return n.name&&(ts.isIdentifier(n.name)||ts.isPrivateIdentifier(n.name)||ts.isStringLiteral(n.name))?n.name.text:"<anonymous@"+line(sf,n)+">";}
function functionLike(n){return ts.isFunctionDeclaration(n)||ts.isMethodDeclaration(n)||ts.isConstructorDeclaration(n)||ts.isGetAccessor(n)||ts.isSetAccessor(n)||ts.isFunctionExpression(n)||ts.isArrowFunction(n)||ts.isMethodSignature(n);}
function firstPass(sf,node,scope){
  let next=scope;
  if(ts.isClassDeclaration(node)||ts.isClassExpression(node)||ts.isInterfaceDeclaration(node)||ts.isModuleDeclaration(node)){
    next=[...scope,nameOf(node,sf)];
    if(ts.isClassDeclaration(node)||ts.isClassExpression(node))classes.push(node);
  }
  if(functionLike(node)){
    const name=nameOf(node,sf),qualified=rel(sf.fileName)+"::"+[...next,name].join(".");
    const sig=checker.getSignatureFromDeclaration(node),id="ts:"+rel(sf.fileName)+":"+node.pos+":"+name;
    nodeToId.set(node,id);
    functions.push({symbol_id:id,qualified_name:qualified,symbol_kind:ts.isMethodDeclaration(node)||ts.isConstructorDeclaration(node)?"method":"function",signature:sig?checker.signatureToString(sig):name,declared_type:"",path:rel(sf.fileName),start_line:line(sf,node),end_line:sf.getLineAndCharacterOfPosition(node.end).line+1,resolver:"typescript_compiler_checker",resolution_status:"resolved"});
    next=[...next,name];
  }
  ts.forEachChild(node,ch=>firstPass(sf,ch,next));
}
sourceFiles.forEach(sf=>firstPass(sf,sf,[]));
function localDeclId(decl){return decl?nodeToId.get(decl)||null:null;}
function selectDecl(symbol,call){
  if(!symbol){const sig=checker.getResolvedSignature(call);return sig&&sig.declaration||null;}
  if(symbol.flags&ts.SymbolFlags.Alias){try{symbol=checker.getAliasedSymbol(symbol);}catch(_){}}
  const ds=symbol.getDeclarations()||[];
  return ds.find(d=>d.getSourceFile()&&d.getSourceFile().fileName.startsWith(root+path.sep))||ds[0]||null;
}
function methodName(n,sf){return n.name?nameOf(n,sf):"";}
function emits(caller,callee,callerName,calleeName,expression,file,ln,status,basis,dispatch){
  edges.push({edge_id:"ts-edge-"+String(edges.length+1).padStart(5,"0"),caller_symbol_id:caller,callee_symbol_id:callee,caller_qualified_name:callerName,callee_qualified_name:calleeName,call_expression:expression,path:rel(file),line:ln,resolution_status:status,resolution_basis:basis,dispatch_kind:dispatch});
}
function interfaceImplementations(decl){
  if(!decl||!ts.isMethodSignature(decl)||!ts.isInterfaceDeclaration(decl.parent))return [];
  const intName=decl.parent.name.text,method=methodName(decl,decl.getSourceFile()),out=[];
  for(const c of classes){
    const sf=c.getSourceFile(),clauses=c.heritageClauses||[];
    const implementsIt=clauses.filter(h=>h.token===ts.SyntaxKind.ImplementsKeyword).some(h=>h.types.some(t=>t.expression.getText(sf).split(".").pop()===intName));
    if(!implementsIt)continue;
    for(const member of c.members||[]){
      if(!functionLike(member)||methodName(member,sf)!==method)continue;
      const id=nodeToId.get(member);if(!id)continue;
      const f=functions.find(x=>x.symbol_id===id);
      out.push({id,name:f?f.qualified_name:id});
    }
  }
  return out;
}
function visit(sf,node,current){
  let owner=current;
  if(nodeToId.has(node))owner=nodeToId.get(node);
  if(ts.isCallExpression(node)&&owner){
    const callerFn=functions.find(f=>f.symbol_id===owner),signature=checker.getResolvedSignature(node);
    let decl=signature&&signature.declaration||null;
    if(!decl)decl=selectDecl(checker.getSymbolAtLocation(node.expression),node);
    let callee=localDeclId(decl),calleeName=node.expression.getText(sf),status="unresolved_dynamic",basis="typescript_checker_no_declaration",dispatch="unknown";
    if(decl){
      const declSf=decl.getSourceFile();calleeName=(decl.name&&decl.name.getText(declSf))||calleeName;
      if(callee){status="resolved";basis="typescript_checker_resolved_signature";dispatch=ts.isMethodDeclaration(decl)||ts.isMethodSignature(decl)?"virtual_or_method":"direct";}
      else{callee="external:"+declSf.fileName+":"+decl.pos+":"+calleeName;status=declSf.fileName.startsWith(root+path.sep)?"unresolved_dynamic":"external";basis="typescript_checker_symbol_without_local_body";}
      if(ts.isMethodSignature(decl)&&ts.isInterfaceDeclaration(decl.parent)){status="resolved_approximate";basis="typescript_checker_interface_contract";dispatch="interface";}
    }
    emits(owner,callee||("unresolved:"+owner+":"+line(sf,node)+":"+calleeName),callerFn?callerFn.qualified_name:owner,calleeName,node.getText(sf),sf.fileName,line(sf,node),status,basis,dispatch);
    for(const candidate of interfaceImplementations(decl)){
      emits(owner,candidate.id,callerFn?callerFn.qualified_name:owner,candidate.name,node.getText(sf),sf.fileName,line(sf,node),"resolved_approximate","typescript_checker_project_implements_expansion","interface_candidate");
    }
  }
  ts.forEachChild(node,ch=>visit(sf,ch,owner));
}
sourceFiles.forEach(sf=>visit(sf,sf,null));
for(const d of ts.getPreEmitDiagnostics(program)){
  let where="";if(d.file&&d.start!==undefined)where=rel(d.file.fileName)+":"+(d.file.getLineAndCharacterOfPosition(d.start).line+1);
  diagnostics.push({code:d.code,message:ts.flattenDiagnosticMessageText(d.messageText," "),location:where});
}
functions.sort((a,b)=>a.path.localeCompare(b.path)||a.start_line-b.start_line);
const result={language,resolver:"TypeScript compiler API / type checker",functions,edges,diagnostics};
fs.mkdirSync(path.dirname(path.resolve(args.out)),{recursive:true});fs.writeFileSync(args.out,JSON.stringify(result,null,2)+"\n");
console.log("TypeScript semantic analysis: "+functions.length+" symbols, "+edges.length+" call edges, "+diagnostics.length+" compiler diagnostics");

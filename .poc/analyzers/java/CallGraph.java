import com.sun.source.tree.*;
import com.sun.source.util.*;
import javax.lang.model.element.*;
import javax.tools.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;

/** JDK compiler-backed method symbol resolver and conservative project call graph. */
public final class CallGraph {
  static String root, outPath;
  static Trees trees;
  static final List<Map<String,Object>> functions = new ArrayList<>();
  static final List<Map<String,Object>> edges = new ArrayList<>();
  static final List<Map<String,Object>> diagnostics = new ArrayList<>();
  static final Map<String,String> elementToId = new HashMap<>();
  static final Map<String,Map<String,Object>> functionById = new HashMap<>();
  static final Map<String,String> classOwnerByElement = new HashMap<>();
  static final Map<String,List<String>> interfacesByClass = new HashMap<>();
  static final Map<String,List<String>> concreteMethodsByOwnerAndName = new HashMap<>();
  static String currentCaller = null;
  static int edgeNum = 0;

  static String rel(Path p) {
    if (p == null) return "";
    try { String r=Paths.get(root).relativize(p.toAbsolutePath().normalize()).toString().replace(File.separatorChar,'/'); return r.startsWith("../")?"":r; }
    catch(Exception e){ return ""; }
  }
  static String json(Object v) {
    if (v == null) return "null";
    if (v instanceof String) {
      String s=(String)v; StringBuilder b=new StringBuilder("\"");
      for (int i=0;i<s.length();i++) { char c=s.charAt(i); switch(c) { case '"':b.append("\\\"");break; case '\\':b.append("\\\\");break; case '\n':b.append("\\n");break; case '\r':b.append("\\r");break; case '\t':b.append("\\t");break; default: if(c<32)b.append(String.format("\\u%04x",(int)c));else b.append(c); } }
      return b.append('"').toString();
    }
    if (v instanceof Number || v instanceof Boolean) return v.toString();
    if (v instanceof Map) { List<String> a=new ArrayList<>(); ((Map<?,?>)v).forEach((k,x)->a.add(json(k.toString())+":"+json(x))); return "{"+String.join(",",a)+"}"; }
    if (v instanceof Iterable) { List<String> a=new ArrayList<>(); for(Object x:(Iterable<?>)v)a.add(json(x));return "["+String.join(",",a)+"]"; }
    return json(v.toString());
  }
  static Map<String,Object> row(Object... args) {
    Map<String,Object> m=new LinkedHashMap<>(); for(int i=0;i+1<args.length;i+=2)m.put((String)args[i],args[i+1]);return m;
  }
  static String ownerName(ExecutableElement e) {
    Element owner=e.getEnclosingElement();
    return owner instanceof TypeElement ? ((TypeElement)owner).getQualifiedName().toString() : owner.toString();
  }
  static String key(ExecutableElement e) { return ownerName(e)+"."+e.getSimpleName()+":"+e.asType().toString(); }
  static Path sourcePath(TreePath p) {
    if (p==null) return null;
    CompilationUnitTree u=p.getCompilationUnit();
    try { return Paths.get(u.getSourceFile().toUri()); } catch(Exception ex){ return null; }
  }
  static long start(CompilationUnitTree u, Tree n) { return trees.getSourcePositions().getStartPosition(u,n); }
  static int line(CompilationUnitTree u, Tree n) { long s=start(u,n); return s<0?0:(int)u.getLineMap().getLineNumber(s); }
  static void mainRun(String[] args) throws Exception {
    for(int i=0;i<args.length;i++) {
      if(args[i].equals("--root")&&i+1<args.length)root=Paths.get(args[++i]).toAbsolutePath().normalize().toString();
      else if(args[i].equals("--out")&&i+1<args.length)outPath=args[++i];
    }
    if(root==null||outPath==null) throw new IllegalArgumentException("usage: CallGraph --root DIR --out FILE");
    JavaCompiler compiler=ToolProvider.getSystemJavaCompiler();
    if(compiler==null)throw new IllegalStateException("JDK compiler unavailable; use a JDK, not a JRE");
    List<Path> sourcePaths=new ArrayList<>();
    try(var walk=Files.walk(Paths.get(root))) {
      walk.filter(Files::isRegularFile).filter(p->p.toString().endsWith(".java")).filter(p->!p.toString().contains(File.separator+"target"+File.separator)&&!p.toString().contains(File.separator+"build"+File.separator)).forEach(sourcePaths::add);
    }
    Collections.sort(sourcePaths);
    DiagnosticCollector<JavaFileObject> collector=new DiagnosticCollector<>();
    try(StandardJavaFileManager manager=compiler.getStandardFileManager(collector,Locale.ROOT,StandardCharsets.UTF_8)) {
      Iterable<? extends JavaFileObject> units=manager.getJavaFileObjectsFromPaths(sourcePaths);
      List<String> options=Arrays.asList("-proc:none","-Xlint:none","-implicit:none");
      JavacTask task=(JavacTask)compiler.getTask(null,manager,collector,options,null,units);
      List<CompilationUnitTree> parsed=new ArrayList<>();
      for(CompilationUnitTree u:task.parse())parsed.add(u);
      try { task.analyze(); } catch(Exception ex) { diagnostics.add(row("code","ANALYZE","message",String.valueOf(ex.getMessage()),"path","","line",0)); }
      trees=Trees.instance(task);
      for(Diagnostic<? extends JavaFileObject> d:collector.getDiagnostics()) {
        String p=""; if(d.getSource()!=null)try{p=rel(Paths.get(d.getSource().toUri()));}catch(Exception ignored){}
        diagnostics.add(row("code",d.getCode(),"message",d.getMessage(Locale.ROOT),"path",p,"line",d.getLineNumber(),"kind",d.getKind().toString()));
      }
      // Index declarations after attribution so Trees/Elements provide the compiler binding.
      for(CompilationUnitTree u:parsed) new TreePathScanner<Void,Void>() {
        @Override public Void visitClass(ClassTree n,Void v) {
          TreePath p=getCurrentPath(); Element el=trees.getElement(p);
          if(el instanceof TypeElement) {
            TypeElement te=(TypeElement)el; String owner=te.getQualifiedName().toString();
            List<String> impl=new ArrayList<>();
            for(Tree t:n.getImplementsClause())impl.add(t.toString());
            for(Tree t:n.getExtendsClause()==null?Collections.<Tree>emptyList():Collections.singletonList(n.getExtendsClause()))impl.add(t.toString());
            interfacesByClass.put(owner,impl);
          }
          return super.visitClass(n,v);
        }
        @Override public Void visitMethod(MethodTree n,Void v) {
          Element e=trees.getElement(getCurrentPath());
          if(e instanceof ExecutableElement) {
            ExecutableElement ee=(ExecutableElement)e; String k=key(ee);
            long s=start(u,n); Path src=sourcePath(getCurrentPath()); String rp=rel(src);
            if(!rp.isEmpty()) {
              String id="java:"+rp+":"+line(u,n)+":"+k;
              elementToId.put(k,id);
              Map<String,Object> f=row("symbol_id",id,"qualified_name",k,"symbol_kind",ee.getKind()==ElementKind.CONSTRUCTOR?"constructor":"method","signature",ee.asType().toString(),"declared_type",ee.getReturnType().toString(),"path",rp,"start_line",line(u,n),"end_line",(int)u.getLineMap().getLineNumber(Math.max(s,start(u,n)+n.toString().length())),"resolver","jdk_compiler_trees_elements","resolution_status","resolved");
              functions.add(f); functionById.put(id,f);
              concreteMethodsByOwnerAndName.computeIfAbsent(ownerName(ee)+"#"+ee.getSimpleName(),z->new ArrayList<>()).add(id);
              classOwnerByElement.put(k,ownerName(ee));
            }
          }
          return super.visitMethod(n,v);
        }
      }.scan(u,null);
      for(CompilationUnitTree u:parsed) new TreePathScanner<Void,Void>() {
        @Override public Void visitMethod(MethodTree n,Void v) {
          Element e=trees.getElement(getCurrentPath()); String prior=currentCaller;
          if(e instanceof ExecutableElement)currentCaller=elementToId.get(key((ExecutableElement)e));
          Void x=super.visitMethod(n,v); currentCaller=prior; return x;
        }
        @Override public Void visitMethodInvocation(MethodInvocationTree n,Void v) {
          if(currentCaller!=null) {
            Element el=trees.getElement(new TreePath(getCurrentPath(),n.getMethodSelect()));
            String targetName=n.getMethodSelect().toString(), targetId=null, status="unresolved_dynamic", basis="javac_binding_unavailable", dispatch="unknown";
            if(el instanceof ExecutableElement) {
              ExecutableElement ee=(ExecutableElement)el; String k=key(ee); targetName=k;
              targetId=elementToId.get(k);
              if(targetId!=null) {
                status="resolved"; basis="jdk_compiler_element_binding";
                Element owner=ee.getEnclosingElement();
                if(owner instanceof TypeElement && ((TypeElement)owner).getKind().isInterface()) {status="resolved_approximate";basis="jdk_compiler_interface_contract";dispatch="interface";}
                else if(!ee.getModifiers().contains(Modifier.STATIC)&&!ee.getModifiers().contains(Modifier.FINAL)) {dispatch="virtual";basis="jdk_compiler_virtual_method_binding";}
                else dispatch="direct";
              } else {targetId="external:"+k;status="external";basis="jdk_compiler_external_symbol";}
            }
            int ln=line(u,n); String p="";try{p=rel(Paths.get(u.getSourceFile().toUri()));}catch(Exception ignored){}
            edges.add(row("edge_id","java-edge-"+String.format("%05d",++edgeNum),"caller_symbol_id",currentCaller,"callee_symbol_id",targetId==null?"unresolved:"+currentCaller+":"+ln+":"+targetName:targetId,"caller_qualified_name",functionById.containsKey(currentCaller)?functionById.get(currentCaller).get("qualified_name"):currentCaller,"callee_qualified_name",targetName,"call_expression",n.toString(),"path",p,"line",ln,"resolution_status",status,"resolution_basis",basis,"dispatch_kind",dispatch));
          }
          return super.visitMethodInvocation(n,v);
        }
      }.scan(u,null);
    }
    Map<String,Object> result=row("language","java","resolver","JDK compiler Trees + Elements","functions",functions,"edges",edges,"diagnostics",diagnostics);
    Path out=Paths.get(outPath);Files.createDirectories(out.toAbsolutePath().getParent());Files.writeString(out,json(result)+"\n",StandardCharsets.UTF_8);
    System.out.println("Java semantic analysis: "+functions.size()+" methods, "+edges.size()+" call sites, "+diagnostics.size()+" compiler diagnostics");
  }
  public static void main(String[] args) { try{mainRun(args);}catch(Exception ex){System.err.println(ex);System.exit(1);} }
}

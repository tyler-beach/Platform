import React, { useEffect, useMemo, useState } from 'react';
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate, useParams } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import rehypeSlug from 'rehype-slug';
import DOMPurify from 'dompurify';
import {
  ArrowDownRight, ArrowLeft, ArrowRight, ArrowUpRight, BookOpen, Boxes, Braces,
  Check, ChevronDown, ChevronRight, CircleDot, Command, FileCode2, GitBranch,
  Github, Layers3, Menu, Search, ShieldCheck, Sparkles, Workflow, X,
} from 'lucide-react';
import {
  BASE_URL, cleanMarkdown, documentIndex, documentMetadata, documentPaths, documents,
  groupedDocuments, matchDocPath, navigationGroups, resolveDocumentHref,
  resolveLegacyPath, routeForDocument, titleForDocument,
} from './content.js';
import DemoExplorer from './components/DemoExplorer.jsx';

const BRAND = 'Pathfinder';
const repository = document.querySelector('meta[name="adr-repository"]')?.content || 'tyler-beach/Platform';
const repo = `https://github.com/${repository}`;
const pageAsset = (relative) => `${BASE_URL}${relative.replace(/^\//, '')}`;

function Logo({ compact = false }) {
  return <Link className="brand" to="/" aria-label={`${BRAND} home`}>
    <img src={pageAsset('content/assets/brand-mark.svg')} alt="" />
    {!compact && <span><strong>Pathfinder</strong><small>From intent to reality</small></span>}
  </Link>;
}

function Header() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  useEffect(() => setOpen(false), [location.pathname]);
  return <header className="app-header">
    <Logo />
    <button className="mobile-menu-toggle" aria-label={open ? 'Close navigation' : 'Open navigation'} aria-expanded={open} onClick={() => setOpen(!open)}>
      {open ? <X size={20} /> : <Menu size={20} />}
    </button>
    <nav className={`global-nav ${open ? 'is-open' : ''}`} aria-label="Main navigation">
      <NavLink to="/architecture" className={({ isActive }) => `global-nav__link ${isActive ? 'is-active' : ''}`}><BookOpen size={16} /> Architecture</NavLink>
      <a href={pageAsset('pathfinder-flow/')} className="global-nav__link global-nav__link--explore"><Workflow size={16} /> Explore workflow <span className="nav-live-mark" aria-hidden="true" /></a>
    </nav>
    <div className="header-actions"><a className="github-link" href={repo} target="_blank" rel="noreferrer"><Github size={16} /><span>Repository</span><ArrowUpRight size={13} /></a></div>
  </header>;
}

function Footer() {
  return <footer className="app-footer"><Logo compact /><span>Evidence first. Human reviewed.</span><a href={repo} target="_blank" rel="noreferrer">Open source on GitHub <ArrowUpRight size={13} /></a></footer>;
}

function Shell({ children, wide = false }) {
  return <><Header /><main className={`app-main ${wide ? 'app-main--wide' : ''}`}>{children}</main><Footer /></>;
}

function Home() {
  return <Shell wide>
    <div className="home-page">
      <section className="hero-grid">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-dot" /> PATHFINDER · ARCHITECTURE ASSURANCE</div>
          <h1>Do the changes follow the rules?</h1>
          <p className="hero-lede">Pathfinder checks code against the rules your team agreed on. It shows the evidence, points out gaps, and lets a person make the final call.</p>
          <div className="hero-actions"><a className="button button--light" href={pageAsset('pathfinder-flow/')}><Workflow size={16} /> Explore the workflow <ArrowRight size={16} /></a><Link className="button button--outline" to="/architecture">How it works</Link></div>
          <div className="hero-proof"><span><Check size={14} /> See the source</span><span><Check size={14} /> Find missing proof</span><span><Check size={14} /> Review each result</span></div>
        </div>
        <PipelineCanvas />
        <div className="hero-glow" aria-hidden="true" />
      </section>

      <section className="experience-section" aria-labelledby="experience-title">
        <div className="section-heading"><div><span className="section-kicker">TWO WAYS IN</span><h2 id="experience-title">One platform. Two clear views.</h2></div><p>Explore how the system is designed, or watch the workflow turn evidence into a reviewable result.</p></div>
        <div className="experience-grid">
          <Link className="experience-card experience-card--docs" to="/architecture">
            <div className="experience-icon"><Layers3 size={21} /></div><span className="experience-index">01 / ARCHITECTURE</span><h3>Understand the system</h3><p>Explore the architecture, decisions, API contracts, evidence model, and engineering playbook.</p><span className="experience-card__link">Browse the reference <ArrowRight size={16} /></span>
            <div className="experience-art experience-art--docs" aria-hidden="true"><span /><span /><span /><i /><i /></div>
          </Link>
          <Link className="experience-card experience-card--demo" to="/demo">
            <div className="experience-icon"><Workflow size={21} /></div><span className="experience-index">02 / PATHFINDER WALKTHROUGH</span><h3>Follow the paved path</h3><p>See a decision checked against implementation evidence, explore what is known and missing, and make the review call yourself.</p><span className="experience-card__link">Start an investigation <ArrowRight size={16} /></span>
            <div className="experience-art experience-art--demo" aria-hidden="true"><span /><span /><span /><b /><b /></div>
          </Link>
        </div>
      </section>

      <section className="principles-strip"><div><ShieldCheck size={19} /><strong>Evidence before inference</strong><span>Claims trace to a pinned source version.</span></div><div><Braces size={19} /><strong>Language-neutral by design</strong><span>Assess behavior and intent across stacks.</span></div><div><CircleDot size={19} /><strong>Uncertainty stays visible</strong><span>Missing evidence is never compliance.</span></div></section>
      <div className="home-disclaimer"><Sparkles size={17} /><p><strong>This is a demo.</strong> It uses example data, not a live scan of your code.</p><Link to="/architecture/ROADMAP">Read the roadmap <ArrowRight size={14} /></Link></div>
    </div>
  </Shell>;
}

function PipelineCanvas() {
  const steps = [
    { code: '01', icon: <FileCode2 size={16} />, title: 'Pin source versions', text: 'ADR · spec · code revision', state: 'LOCKED' },
    { code: '02', icon: <Search size={16} />, title: 'Assemble evidence', text: 'Scope · changes · observations', state: 'TRACEABLE' },
    { code: '03', icon: <Sparkles size={16} />, title: 'Assess with limits', text: 'Bounded mock or provider call', state: 'BOUNDED' },
    { code: '04', icon: <ShieldCheck size={16} />, title: 'Validate and review', text: 'Evidence IDs · versions · outcome', state: 'AUDITABLE' },
  ];
  return <div className="pipeline-visual" aria-label="Four-stage evidence-first analysis pipeline">
    <div className="pipeline-orbit pipeline-orbit--one" /><div className="pipeline-orbit pipeline-orbit--two" />
    <div className="pipeline-card">
      <div className="pipeline-card__top"><span><span className="pulse-dot" /> ANALYSIS PIPELINE</span><span className="pipeline-label">DESIGN + POC</span></div>
      <div className="pipeline-steps">{steps.map((step, index) => <React.Fragment key={step.code}><div className="pipeline-step"><span className="pipeline-step__number">{step.code}</span><span className="pipeline-step__icon">{step.icon}</span><div className="pipeline-step__copy"><strong>{step.title}</strong><span>{step.text}</span></div><span className="pipeline-step__state">{step.state}</span></div>{index < steps.length - 1 && <div className="pipeline-wire"><i /></div>}</React.Fragment>)}</div>
      <div className="pipeline-card__bottom"><span><GitBranch size={13} /> REVIEWABLE RESULT</span><span>source → evidence → assessment</span></div>
    </div>
  </div>;
}

function ArchitectureHome() {
  return <div className="architecture-home">
    <div className="architecture-hero"><span className="eyebrow eyebrow--light">PLATFORM REFERENCE</span><h1>Architecture, made inspectable.</h1><p>Follow the system from source intake through evidence collection, bounded assessment, and human review. These documents describe the design baseline and clearly label what remains proposed.</p><div className="architecture-stats"><span><strong>03</strong><small>Comparison paths</small></span><span><strong>04</strong><small>Core guarantees</small></span><span><strong>01</strong><small>Runnable PoC</small></span></div></div>
    <div className="doc-feature-grid">
      <FeatureDoc path="system-architecture.md" label="SYSTEM DESIGN" icon={<Boxes size={18} />} />
      <FeatureDoc path="contracts/EVIDENCE.md" label="PROVENANCE" icon={<ShieldCheck size={18} />} />
      <FeatureDoc path="AI_PIPELINE.md" label="ANALYSIS" icon={<Sparkles size={18} />} />
      <FeatureDoc path="ENGINEERING_PLAYBOOK.md" label="BUILD PRACTICE" icon={<Braces size={18} />} />
      <FeatureDoc path="adr/POD-DISRUPTION-BUDGETS.md" label="AVAILABILITY ADR" icon={<ShieldCheck size={18} />} />
      <FeatureDoc path="adr/SESSION-TTL.md" label="SESSION SECURITY ADR" icon={<CircleDot size={18} />} />
    </div>
    <div className="architecture-bottom-grid"><div className="architecture-callout"><span className="section-kicker">START WITH THE SHAPE</span><h2>Three comparisons. One evidence standard.</h2><p>Implementation ↔ ADR, specification ↔ ADR, and specification ↔ implementation all use version-bound references. Similarity alone does not establish applicability.</p><Link to={routeForDocument('system-architecture.md')}>Explore system architecture <ArrowRight size={15} /></Link></div><div className="architecture-document-list"><div className="section-heading section-heading--compact"><div><span className="section-kicker">REFERENCE LIBRARY</span><h2>Explore by topic</h2></div></div><div className="topic-links">{navigationGroups.slice(1).map((group) => <Link key={group.title} to={routeForDocument(group.paths[0])}><span>{group.title}</span><span>{group.paths.length} topics <ArrowRight size={14} /></span></Link>)}</div></div></div>
  </div>;
}

function FeatureDoc({ path, label, icon }) {
  const metadata = documentMetadata[path];
  if (!metadata) return null;
  return <Link className="doc-feature" to={routeForDocument(path)}><span className="doc-feature__icon">{icon}</span><span className="doc-feature__label">{label}</span><h3>{metadata.title}</h3><p>{metadata.summary || 'Open the reference document.'}</p><span className="doc-feature__more">Open reference <ArrowRight size={14} /></span></Link>;
}

function ArchitectureLayout({ children }) {
  const location = useLocation();
  const [query, setQuery] = useState('');
  const [mobileDocsOpen, setMobileDocsOpen] = useState(false);
  const groups = groupedDocuments(query);
  const activeRoute = location.pathname;
  useEffect(() => setMobileDocsOpen(false), [activeRoute]);
  return <div className="architecture-layout">
    <aside className={`docs-sidebar ${mobileDocsOpen ? 'docs-sidebar--open' : ''}`}>
      <div className="docs-sidebar__head"><div><span className="section-kicker">ARCHITECTURE</span><h2>Reference library</h2></div><span className="docs-count">{documentIndex.length}</span></div>
      <label className="docs-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a document…" aria-label="Search architecture documents" />{query && <button onClick={() => setQuery('')} aria-label="Clear search"><X size={13} /></button>}</label>
      <nav aria-label="Architecture documents" className="docs-nav">{groups.map((group) => <div className="docs-nav__group" key={group.title}><h3>{group.title}</h3>{group.items.map((item) => <NavLink key={item.path} to={item.href} end={item.path === 'index.md'} className={({ isActive }) => `docs-nav__link ${isActive ? 'is-active' : ''}`}>{item.title}</NavLink>)}</div>)}{groups.length === 0 && <p className="no-results">No matching references.</p>}</nav>
      <div className="docs-sidebar__foot"><span className="mini-status" /><span>Design baseline · PoC runnable</span></div>
    </aside>
    <div className="docs-reading-area"><button className="mobile-docs-toggle" onClick={() => setMobileDocsOpen(!mobileDocsOpen)} aria-expanded={mobileDocsOpen}><Menu size={16} /> Browse references <ChevronDown size={14} /></button>{children}</div>
  </div>;
}

function ArchitectureRouter() {
  const { '*': wildcard = '' } = useParams();
  const slug = wildcard.replace(/\/+$/, '');
  if (!slug) return <ArchitectureLayout><ArchitectureHome /></ArchitectureLayout>;
  if (slug.toLowerCase() === 'openapi' || slug.toLowerCase() === 'openapi.yaml') return <ArchitectureLayout><OpenAPIReference /></ArchitectureLayout>;
  const doc = matchDocPath(slug, documentPaths);
  if (!doc) return <ArchitectureLayout><NotFound embedded /></ArchitectureLayout>;
  return <ArchitectureLayout><DocumentPage docPath={doc} /></ArchitectureLayout>;
}

function DocumentPage({ docPath }) {
  const [raw, setRaw] = useState('');
  const source = cleanMarkdown(raw);
  const title = documentMetadata[docPath]?.title || docPath;
  const toc = useMemo(() => Array.from(source.matchAll(/^##+\s+(.+)$/gm)).map((match) => ({ title: match[1].replace(/[`*_]/g, ''), id: slugHeading(match[1]) })), [source]);
  useEffect(() => {
    let alive = true;
    setRaw('');
    documents[docPath]?.().then((text) => { if (alive) setRaw(text); }).catch(() => { if (alive) setRaw('# Reference unavailable\n\nThe checked-in source document could not be loaded.'); });
    return () => { alive = false; };
  }, [docPath]);
  useEffect(() => {
    if (!raw) return undefined;
    let alive = true;
    import('../docs/javascripts/diagram-viewer.js').then(() => {
      if (alive) globalThis.DiagramViewerCore?.install(document, globalThis);
    });
    return () => { alive = false; };
  }, [docPath, raw]);
  return <article className="document-page">
    <div className="breadcrumbs"><Link to="/architecture">Architecture</Link><ChevronRight size={13} /><span>{title}</span></div>
    <div className="document-heading"><span className="section-kicker">{categoryForPath(docPath)}</span><h1>{title}</h1><p>Design reference · Source maintained in <code>docs/{docPath}</code></p></div>
    <div className="document-layout"><div className="markdown-content">{raw ? <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize, rehypeSlug]} components={markdownComponents(docPath)}>{normalizeMkdocs(source)}</ReactMarkdown> : <div className="document-loading" role="status">Loading reference <span /> <span /> <span /></div>}</div>{toc.length > 1 && <aside className="document-toc"><strong>ON THIS PAGE</strong>{toc.map((item) => <a key={`${item.id}-${item.title}`} href={`#${item.id}`}>{item.title}</a>)}</aside>}</div>
  </article>;
}

function markdownComponents(docPath) {
  return {
    a({ href = '', children, ...props }) {
      const resolved = resolveDocumentHref(href, `docs/${docPath}`, documentPaths, '/');
      if (resolved === '/demo' || resolved?.startsWith('/architecture/')) return <Link to={resolved} {...props}>{children}</Link>;
      if (resolved?.startsWith('/content/')) return <a href={pageAsset(resolved)} {...props}>{children}</a>;
      return <a href={resolved} {...props} target={resolved?.startsWith('http') ? '_blank' : undefined} rel={resolved?.startsWith('http') ? 'noreferrer' : undefined}>{children}</a>;
    },
    img({ src = '', alt = '', ...props }) {
      const resolved = resolveDocumentHref(src, `docs/${docPath}`, documentPaths, '/');
      return <img src={resolved?.startsWith('/content/') ? pageAsset(resolved) : src} alt={alt} loading="lazy" {...props} />;
    },
    table({ children, ...props }) { return <div className="markdown-table-scroll"><table {...props}>{children}</table></div>; },
    code({ className = '', children, ...props }) {
      if (/language-mermaid/.test(className)) return <MermaidBlock source={String(children).replace(/\n$/, '')} />;
      return <code className={className} {...props}>{children}</code>;
    },
  };
}

function normalizeMkdocs(markdown) {
  return markdown.replace(/^( {0,3})(!!!|\?{3}\+?)\s+([\w-]+)(?:\s+["']([^"']+)["'])?\s*\n((?:(?: {4,}|\t).*(?:\n|$))+)/gm, (_, indent, marker, kind, title, body) => {
    const heading = title || kind.replace(/-/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
    return `> **${heading}**\n>\n${body.split('\n').map((line) => line ? `> ${line.replace(/^(?: {4}|\t)/, '')}` : '>').join('\n')}\n`;
  });
}

function MermaidBlock({ source }) {
  const [svg, setSvg] = useState('');
  const [error, setError] = useState(false);
  useEffect(() => {
    let cancelled = false;
    import('mermaid').then(async ({ default: mermaid }) => {
      const instance = mermaid.default || mermaid;
      instance.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'neutral', flowchart: { htmlLabels: false } });
      const rendered = await instance.render(`mermaid-${Math.random().toString(36).slice(2)}`, source);
      if (!cancelled) setSvg(DOMPurify.sanitize(rendered.svg, { USE_PROFILES: { svg: true, svgFilters: true } }));
    }).catch(() => { if (!cancelled) setError(true); });
    return () => { cancelled = true; };
  }, [source]);
  if (error) return <pre className="mermaid-error"><code>{source}</code></pre>;
  if (!svg) return <div className="mermaid-placeholder" role="status">Rendering architecture diagram…</div>;
  return <div className="mermaid-rendered" dangerouslySetInnerHTML={{ __html: svg }} />;
}

function OpenAPIReference() {
  const [yaml, setYaml] = useState('Loading API contract…');
  useEffect(() => { fetch(pageAsset('content/openapi.yaml')).then((response) => response.ok ? response.text() : Promise.reject()).then(setYaml).catch(() => setYaml('API document unavailable.')); }, []);
  return <article className="document-page"><div className="breadcrumbs"><Link to="/architecture">Architecture</Link><ChevronRight size={13} /><span>OpenAPI reference</span></div><div className="document-heading"><span className="section-kicker">API CONTRACT</span><h1>Proposed HTTP interface</h1><p>Interactive source view for the versioned OpenAPI contract. This is a proposed façade, not a deployed API server.</p></div><pre className="openapi-source"><code>{yaml}</code></pre></article>;
}

function DemoRoute() {
  return <Shell wide><DemoExplorer /></Shell>;
}

function LegacyRoute() {
  const location = useLocation();
  const resolved = resolveLegacyPath(location.pathname, documentPaths, BASE_URL);
  if (!resolved) return <Navigate to="/not-found" replace />;
  return <Navigate to={resolved} replace />;
}

function NotFound({ embedded = false }) {
  const body = <div className="not-found"><span className="section-kicker">404 · PAGE NOT FOUND</span><h1>This reference moved.</h1><p>Browse the architecture library or open the workflow demo.</p><div><Link className="button button--dark" to="/architecture">Architecture <ArrowRight size={15} /></Link><Link className="button button--outline-light" to="/demo">Workflow demo <ArrowRight size={15} /></Link></div></div>;
  return embedded ? body : <Shell>{body}</Shell>;
}

function slugHeading(title) { return title.toLowerCase().trim().replace(/[`*_]/g, '').replace(/[^\w\s-]/g, '').replace(/\s+/g, '-'); }
function categoryForPath(path) {
  if (path.startsWith('contracts/') || path === 'DATA_MODEL.md' || path === 'RPC_AND_PROTOBUF.md' || path === 'api/index.md') return 'API & CONTRACTS';
  if (path.startsWith('how-to/')) return 'ENGINEERING GUIDE';
  if (path.startsWith('diagrams/')) return 'ARCHITECTURE';
  if (path.startsWith('evaluation/')) return 'EVALUATION';
  return 'ENGINEERING REFERENCE';
}

export default function App() {
  return <Routes><Route path="/" element={<Home />} /><Route path="/architecture/*" element={<Shell wide><ArchitectureRouter /></Shell>} /><Route path="/demo/*" element={<DemoRoute />} /><Route path="/not-found" element={<NotFound />} /><Route path="*" element={<LegacyRoute />} /></Routes>;
}

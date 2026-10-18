import routeCore from './site-routes.cjs';
import index from './generated-doc-index.json';

export const { routeForDocument, matchDocPath, resolveDocumentHref, resolveLegacyPath } = routeCore;
export const BASE_URL = import.meta.env.BASE_URL;
const loaders = import.meta.glob('../docs/**/*.md', { query: '?raw', import: 'default' });
export const documents = Object.fromEntries(Object.entries(loaders).map(([path, loader]) => [path.replace(/^\.\.\/docs\//, ''), loader]));
export const documentIndex = [...index, { path: 'openapi.yaml', title: 'OpenAPI specification', summary: 'Proposed machine-readable API contract; no live service is implied.' }].map((item) => ({ ...item, href: routeForDocument(item.path) }));
export const documentPaths = documentIndex.map((item) => item.path);

export function cleanMarkdown(source = '') {
  return source.replace(/^---\s*\n[\s\S]*?\n---\s*\n/, '').replace(/\r\n/g, '\n');
}

export function titleForDocument(path, source) {
  const heading = cleanMarkdown(source).match(/^#\s+(.+)$/m);
  if (heading) return heading[1].replace(/[*_`]/g, '').trim();
  const filename = path.split('/').at(-1).replace(/\.md$/i, '').replace(/[-_]/g, ' ');
  return filename.replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export const documentMetadata = Object.fromEntries(documentIndex.map((item) => [item.path, item]));

export const navigationGroups = [
  { title: 'Start here', paths: ['index.md', 'PROJECT_BRIEF.md', 'getting-started.md', 'ROADMAP.md', 'PRE_IMPLEMENTATION_READINESS.md', 'MVP_DECISION_PACKET.md', 'DECISIONS.md', 'OPEN_QUESTIONS.md'] },
  { title: 'Architecture', paths: ['system-architecture.md', 'architecture-overview.md', 'architecture.md', 'diagrams/architecture.md', 'diagrams/README.md', 'assets/aws-icons/README.md', 'AI_PIPELINE.md', 'FUNCTIONAL_CORE.md', 'RPC_AND_PROTOBUF.md'] },
  { title: 'API & contracts', paths: ['api/index.md', 'contracts/API_CONTRACT.md', 'contracts/CONTRACTS.md', 'DATA_MODEL.md', 'contracts/EVIDENCE.md', 'contracts/LOGGING_AND_AUDIT.md', 'contracts/AI_RUNTIME.md', 'openapi.yaml'] },
  { title: 'Engineering', paths: ['ENGINEERING_PLAYBOOK.md', 'OPEN_SPEC_WORKFLOW.md', 'ADVERSARIAL_DESIGN_REVIEW.md', 'GO_TOOLING.md', 'ADR_SCOPE_RETRIEVAL.md', 'EXECUTABLE_POC.md', 'functional-analysis-demo.md', 'how-to/index.md', 'how-to/add-input-source.md', 'how-to/add-go-worker.md', 'how-to/add-comparison-mode.md', 'TOOLS_AND_REFERENCES.md', 'CONTRIBUTING.md'] },
  { title: 'Trust & quality', paths: ['SECURITY.md', 'OPERATIONS.md', 'EVALUATION.md', 'REUSABLE_REQUIREMENT_EVALUATION.md', 'FINDING_CONTRACT.md', 'AI_EVALUATION_OBSERVABILITY.md', 'AI_TECHNOLOGY_SELECTION.md', 'AI_TECHNOLOGY_DECISION_MATRIX.md', 'REQUIREMENT_TO_PROOF_MATRIX.md', 'evaluation/README.md', 'evaluation/STARTER_CORPUS.md'] },
];

export function groupedDocuments(query = '') {
  const needle = query.trim().toLowerCase();
  return navigationGroups.map((group) => ({
    ...group,
    items: group.paths.filter((path) => documentMetadata[path] && (!needle || `${documentMetadata[path].title} ${path}`.toLowerCase().includes(needle)))
      .map((path) => ({ path, title: documentMetadata[path].title, href: routeForDocument(path) })),
  })).filter((group) => group.items.length);
}

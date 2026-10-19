const e=`---
hide:
  - navigation
  - toc
---
<div class="home-hero">
<div class="home-hero__main">
<span class="home-eyebrow"><span class="home-eyebrow__dot"></span> ARCHITECTURE · EVIDENCE · GOVERNANCE</span>
<h1>Make architectural drift <em>visible.</em></h1>
<p class="home-hero__lede">Connect architectural decisions, plain-English technical specifications, and implementation changes. Surface potential divergence with traceable evidence—not unsupported AI opinions.</p>
<div class="home-hero__actions">
<a class="md-button md-button--primary" href="./system-architecture/">Explore the architecture</a>
<a class="md-button md-button--primary" href="./demo/">Run the interactive PoC demo</a>
<a class="md-button" href="./ENGINEERING_PLAYBOOK/">Engineering playbook</a>
</div>
<div class="home-hero__signals">
<div class="home-hero__signal"><strong>Three comparison modes</strong><span>Code, decisions and specifications</span></div>
<div class="home-hero__signal"><strong>Evidence by design</strong><span>Version-bound, reviewable findings</span></div>
<div class="home-hero__signal"><strong>Human-governed</strong><span>Bounded model use, explicit review</span></div>
</div>
</div>
<div class="home-hero__visual">
<div class="pipeline-preview">
<div class="pipeline-preview__head"><span>Analysis pipeline</span><span class="pipeline-preview__status">Reference design</span></div>
<div class="pipeline-step"><span class="pipeline-step__icon">01</span><span class="pipeline-step__text"><strong>Source snapshot</strong><span>ADR · specification · code revision</span></span><span class="pipeline-step__tag">Pinned</span></div>
<div class="pipeline-connector"></div>
<div class="pipeline-step"><span class="pipeline-step__icon">02</span><span class="pipeline-step__text"><strong>Evidence assembly</strong><span>Scope, diff, rules and retrieval</span></span><span class="pipeline-step__tag">Deterministic</span></div>
<div class="pipeline-connector"></div>
<div class="pipeline-step"><span class="pipeline-step__icon">03</span><span class="pipeline-step__text"><strong>Bounded assessment</strong><span>Versioned prompt · token and cost limits</span></span><span class="pipeline-step__tag">Constrained</span></div>
<div class="pipeline-connector"></div>
<div class="pipeline-step"><span class="pipeline-step__icon">04</span><span class="pipeline-step__text"><strong>Validate and review</strong><span>Evidence checks, freshness and disposition</span></span><span class="pipeline-step__tag">Auditable</span></div>
<div class="pipeline-preview__foot">Target architecture. The GitHub Actions PoC is runnable; the production service and Step Functions workflow remain proposed.</div>
</div>
</div>
</div>

<section class="experience-switch" aria-label="Choose a platform experience">
  <a class="experience-card experience-card--architecture" href="./system-architecture/">
    <span class="experience-card__label">01 / ARCHITECTURE</span>
    <strong>Understand the system</strong>
    <span>Architecture, decisions, API contracts, evidence rules, and engineering guidance.</span>
    <b>Explore the architecture <span aria-hidden="true">↗</span></b>
  </a>
  <a class="experience-card experience-card--demo" href="./demo/">
    <span class="experience-card__label">02 / WORKFLOW DEMO</span>
    <strong>Explore a real run</strong>
    <span>Walk through synthetic scenarios, inspect evidence, and browse verified workflow history.</span>
    <b>Open the workflow explorer <span aria-hidden="true">↗</span></b>
  </a>
</section>

<section class="home-section">
<div class="home-section__head">
<div><span class="home-section__eyebrow">Explore the platform</span><h2>Designed for engineering rigor.</h2></div>
<p class="home-section__intro">Start with the system shape, then go deeper into the contracts and practices that make the proposed platform safe to build and operate.</p>
</div>
<div class="home-feature-grid">
<article class="home-feature"><span class="home-feature__index">01</span><h3>System architecture</h3><p>Understand component ownership, trust boundaries, asynchronous orchestration, storage and model-provider integration.</p><a href="./system-architecture/">Explore architecture →</a></article>
<article class="home-feature"><span class="home-feature__index">02</span><h3>API and data contracts</h3><p>Review proposed operations, lifecycle semantics, compatibility rules and invariants for jobs, findings and evidence.</p><a href="./contracts/API_CONTRACT/">Explore contracts →</a></article>
<article class="home-feature"><span class="home-feature__index">03</span><h3>Evidence and provenance</h3><p>Follow a claim back to immutable source versions, precise locators, hashes and the supporting or contradicting evidence.</p><a href="./contracts/EVIDENCE/">Explore evidence →</a></article>
<article class="home-feature"><span class="home-feature__index">04</span><h3>AI runtime controls</h3><p>See how token budgets, spend limits, prompt versions, output validation and redacted telemetry fit into the harness.</p><a href="./contracts/AI_RUNTIME/">Explore AI controls →</a></article>
<article class="home-feature"><span class="home-feature__index">05</span><h3>OpenSpec engineering</h3><p>Connect behavior requirements to regression tests, contract tests, implementation, evaluations and verified changes.</p><a href="./ENGINEERING_PLAYBOOK/">Explore the playbook →</a></article>
<article class="home-feature"><span class="home-feature__index">06</span><h3>Adversarial review</h3><p>Examine the highest-risk distributed-system failures, concurrency gaps, security boundaries and unresolved decisions.</p><a href="./ADVERSARIAL_DESIGN_REVIEW/">Explore the review →</a></article>
</div>
</section>

<section class="home-comparison">
<div class="home-comparison__intro"><span class="home-section__eyebrow">What it compares</span><h2>Three paths to architectural confidence.</h2><p>Each comparison has a defined evidence set and an explicit outcome. Similarity alone does not make an ADR applicable, and missing evidence never proves compliance.</p></div>
<div class="home-comparison__list">
<div class="home-comparison__item"><span class="home-comparison__letter">A</span><div><strong>Implementation ↔ ADR</strong><span>Does a code change conflict with an accepted, applicable architectural decision?</span></div></div>
<div class="home-comparison__item"><span class="home-comparison__letter">B</span><div><strong>Specification ↔ ADR</strong><span>Does the technical design align with architectural constraints and decision scope?</span></div></div>
<div class="home-comparison__item"><span class="home-comparison__letter">C</span><div><strong>Specification ↔ implementation</strong><span>Does observed implementation behavior satisfy the stated technical requirements?</span></div></div>
</div>
</section>

<section class="home-section">
<div class="home-section__head"><div><span class="home-section__eyebrow">Engineering principles</span><h2>Make the guarantees testable.</h2></div></div>
<div class="home-principles">
<div class="home-principle"><strong>Evidence before inference</strong><span>Every actionable claim resolves to a versioned source.</span></div>
<div class="home-principle"><strong>One workflow owner</strong><span>Distributed state and retries have clear authority.</span></div>
<div class="home-principle"><strong>Bounded model calls</strong><span>Context, spend, concurrency and time are controlled.</span></div>
<div class="home-principle"><strong>Specs are not proof</strong><span>Acceptance scenarios and tests verify shipped behavior.</span></div>
</div>
</section>

<div class="home-status"><span class="home-status__mark">i</span><div><strong>Current status: design baseline plus runnable PoC</strong><p>The repository includes GitHub Actions workflows and a deterministic local/mock analysis harness; these are not the proposed production API, AWS workers, database, or Step Functions state machine. <a href="./demo/">Explore the PoC and its run outputs</a>, then follow the <a href="./ROADMAP/">roadmap</a> and <a href="./OPEN_QUESTIONS/">open questions</a> for outstanding implementation and approval decisions.</p></div></div>
`;export{e as default};

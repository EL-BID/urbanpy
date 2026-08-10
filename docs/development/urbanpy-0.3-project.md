# UrbanPy 0.3 production-readiness project

## Mission

Ship UrbanPy 0.3 as a reproducible, typed, tested, documented, and maintainable
geospatial library that EL-BID can safely recommend to external users and that
new contributors can improve without relying on maintainer-specific machines.

This is the parent roadmap for the GitHub Project **UrbanPy 0.3 — Production
Readiness**. Large workstreams are parent issues. Work that can be reviewed and
verified independently is a sub-issue and normally one pull request.

The evidence behind this roadmap is recorded in
[`current-state-audit.md`](current-state-audit.md). The OSRM and runtime-model
workstreams have dedicated plans:

- [`osrm-0.3.md`](osrm-0.3.md)
- [`typed-models-0.3.md`](typed-models-0.3.md)

## Release principles

- SonarQube remains enabled and required for EL-BID compliance.
- Pull requests with human approval are the only path to the default branch.
- PR checks are deterministic and do not call live public geospatial services.
- The package declares direct dependencies; the development lock records a
  reproducible environment. Published wheels do not pin every transitive package.
- Public API compatibility is intentional, documented, and tested.
- Runtime validation is concentrated at untrusted and serialized boundaries.
- Native GeoPandas, pandas, NumPy, Shapely, and NetworkX types remain native in
  computational paths.
- AI agents may prepare branches and PRs, but may not approve, merge, change
  repository security, or publish releases.
- 0.3 scope favors reliability over adding new data sources or algorithms.

## Decisions to record before implementation

Each decision becomes a short architecture decision record (ADR), with owner,
date, alternatives, consequences, and reversal plan.

1. **Python support.** The recommended baseline is Python 3.11 through 3.14.
   Current OSMnx releases require Python 3.11 or newer. Confirm wheel availability
   for every direct dependency and operating system before finalizing it.
2. **Build and versioning.** Use `pyproject.toml`, `uv`, a PEP 517 build backend,
   and one authoritative version source. Remove tag-time source rewriting.
3. **Dependency boundaries.** Decide which capabilities are base installation
   requirements and which become extras, then remove eager imports that defeat
   those boundaries.
4. **Runtime typing.** Adopt the boundary-first Pydantic policy in the dedicated
   plan and select the static type checker used in CI.
5. **OSRM lifecycle.** Adopt the Python-owned, catalog-backed architecture in the
   dedicated OSRM plan.
6. **External services.** Define common timeouts, identification, retries,
   caching, errors, and live-contract testing for Nominatim, Overpass, HDX, ORS,
   Google Maps, Geofabrik, and OSRM.
7. **License policy.** EL-BID confirms the precise project SPDX expression and
   approves a dependency-license allowlist and exception process. Tool output is
   evidence, not legal advice.
8. **Default branch.** Treat a possible `master` to `main` rename as a separate,
   coordinated migration. It is not required to make 0.3 technically sound.

## Workstreams and parent issues

### W0. Project governance and issue triage

**Outcome:** contributors can see the scope, decision owners, dependencies, and
release gates without reconstructing them from old issues.

- Create the organization-level GitHub Project and the fields/views below.
- Create parent issues W0 through W10 and attach the dedicated plans.
- Link existing issues and PRs instead of creating duplicates.
- Add issue forms, a pull-request template, `CODEOWNERS`, `SECURITY.md`,
  `SUPPORT.md`, and a lightweight governance/maintainer policy.
- Record ADRs for the eight decisions above.
- Define supported-version, deprecation, and vulnerability-response policies.
- Assign at least two humans to release-critical ownership where possible.

### W1. Packaging, `uv`, and dependency architecture

**Outcome:** users install a small, correct package; contributors reproduce CI
with documented `uv` commands.

- Replace `setup.py`, the fully pinned runtime `requirements.txt`, and duplicated
  metadata with PEP 621 metadata in `pyproject.toml`.
- Declare only direct runtime dependencies with justified lower/upper bounds.
- Define PEP 735 groups for test, lint/type, docs, security, and release tooling.
- Define extras only after import boundaries make them real, for example
  `plotting`, `hdx`, `google`, and `cli`.
- Commit the cross-platform `uv.lock`; CI uses `uv sync --locked` and checks
  `uv lock --check`.
- Add a `.python-version` for the contributor default without limiting the CI
  compatibility matrix.
- Add `urbanpy.__version__`, complete package metadata/project URLs, classifiers,
  and `py.typed` if the public typing contract is accepted.
- Stop importing every optional module and initializing HDX configuration during
  `import urbanpy`.
- Build sdist and wheel with `uv build`; run metadata, contents, `pip check`, and
  clean-install smoke tests on both artifacts.
- Verify that installed-wheel behavior—not only source-tree behavior—is tested.
- Retire `environment.yml` as a dependency authority. Keep a generated example
  only if it adds user value.

### W2. Deterministic CI, Trunk, and required quality gates

**Outcome:** one stable set of checks answers whether a PR is mergeable.

- Split the monolithic workflow into PR CI, SonarQube, documentation, scheduled
  contracts, and release workflows with narrow triggers.
- Add concurrency cancellation, job timeouts, dependency caching, minimal token
  permissions, and `persist-credentials: false` where checkout credentials are
  unnecessary.
- Pin third-party Actions to immutable commit SHAs and automate reviewed updates.
- Prevent duplicate `push` and `pull_request` runs for the same contribution.
- Make one stable aggregate check (`CI / required`) represent the supported
  Python matrix so branch rules do not depend on changing matrix job names.
- Run formatting/linting, static typing, hermetic unit tests with coverage, docs
  with warnings as errors, and artifact checks.
- Perform a time-boxed Trunk Code Quality spike. If it remains suitable, use
  Trunk locally and in CI to orchestrate pinned Ruff, format, Markdown/YAML,
  ShellCheck/shfmt, actionlint, and other repository checks. Keep the standard
  tool configurations authoritative so contributors and remote agents have a
  direct `uv run` fallback.
- Do not enable Trunk Flaky Tests quarantine until tests are hermetic and the
  team agrees that quarantine cannot conceal regressions.
- Preserve CodeQL, secret scanning/push protection, and applicable EL-BID checks.

#### SonarQube hardening

- Keep the SonarQube scan mandatory.
- Remove all `continue-on-error` and `|| true` behavior from required analysis.
- Produce coverage once in the test workflow and pass the exact artifact to the
  scan; a missing or invalid report fails the job.
- Set `sonar.sources=urbanpy`, `sonar.tests=tests`, coverage paths, Python versions,
  and focused exclusions instead of analyzing the entire repository as source.
- Enable quality-gate waiting or reliable PR decoration so a failed gate fails
  the GitHub check.
- Confirm the EL-BID SonarQube edition/configuration supports the intended PR
  analysis and record the quality gate applied to new code.

#### Default-branch rules

- Require one human approval, resolution of review threads, and approval after
  the latest material push (or dismissal of stale approvals).
- Require `CI / required`, the SonarQube quality gate, security analysis, and the
  approved license/vulnerability check from their expected GitHub Apps.
- Block deletion and force pushes and require PRs to be up to date or use a
  tested merge queue.
- Keep AI review advisory; it never satisfies the human-approval requirement.

### W3. Supply-chain security, licensing, and release credentials

**Outcome:** the dependency and release chain has an auditable disposition.

- Complete incident closure for the exposed PyPI credential and removed
  malicious workflow: revoke/rotate credentials, review audit logs and release
  history, document impact, and close the relevant security work.
- Merge or supersede PR #60 only after its workflow is green and trusted
  publishing is configured end to end.
- Remove long-lived PyPI tokens; use a protected GitHub environment and OIDC
  trusted publishing with `id-token: write` only in the publish job.
- Triage the current “License Compliance” failure instead of suppressing it.
- Generate a dependency inventory and CycloneDX SBOM from the `uv` resolution.
- Scan locked dependencies for known vulnerabilities and define severity/SLA and
  exception-expiry policy.
- Review direct and transitive dependency licenses against the EL-BID-approved
  policy; store machine-readable output and human decisions separately.
- Add OpenSSF-friendly metadata, `SECURITY.md`, dependency update automation, and
  release provenance/attestations where supported.
- Remove obsolete analytics beacons and accidental personal identifiers from
  tests and documentation.

### W4. Safe, always-on agentic development

**Outcome:** remote agents can continuously deliver reviewable work without
receiving release or administrative authority.

- Add concise repository instructions describing bootstrap commands, architecture,
  allowed test doubles, style, verification, and protected areas.
- Create an `agent:ready` issue label. Eligible issues must have bounded scope,
  dependencies resolved, acceptance criteria, expected files/interfaces, and
  exact verification commands.
- Agents work on short-lived branches and open draft PRs. They may not push to the
  default branch, merge, approve, modify rulesets/secrets, or publish packages.
- Use least-privilege short-lived credentials; workflows from forks receive no
  secrets and untrusted code never runs with `pull_request_target` privileges.
- Require PR bodies to identify generated changes, tests run, unresolved risks,
  API/dependency effects, and the issue closed.
- Require CODEOWNER review for workflows, packaging/release, security, public
  models, and compatibility shims.
- Measure agent PR rework, escaped defects, review latency, and abandoned work;
  adjust task size and instructions based on evidence.

#### AI code-review pilot

- Continue to treat GitHub Copilot review as advisory while measuring its signal.
- Pilot one additional reviewer at a time to avoid duplicate noise. CodeRabbit is
  the leading free candidate because public open-source repositories currently
  receive its OSS review tier. Greptile's OSS program is limited to qualifying
  MIT/Apache projects, so GPL-licensed UrbanPy would rely on its individual
  Starter allowance rather than the OSS program.
- Run the pilot for at least 20 representative PRs. Track actionable findings,
  false-positive rate, duplicate comments, time-to-review, data access, permissions,
  and maintainer effort.
- Do not make an AI reviewer a required check. Human review, tests, SonarQube,
  and deterministic static analysis remain authoritative.

### W5. Test architecture and external-service reliability

**Outcome:** PR failures indicate code regressions, while scheduled jobs detect
upstream service drift.

- Divide tests into `unit`, `contract`, `integration`, `docker`, and `live`
  markers with explicit ownership and budgets.
- Replace PR-time Nominatim, HDX, OSMnx/Overpass, ORS, Google, Geofabrik, and OSRM
  calls with recorded minimal fixtures and HTTP/subprocess fakes.
- Block accidental network access in the unit-test job.
- Add small live contract tests on a schedule and manual dispatch with clear
  provider-friendly rates; their failure opens or updates an issue but does not
  retroactively make unrelated PRs fail.
- Build a shared HTTP boundary with an identifying User-Agent, explicit connect
  and read timeouts, bounded retries with jitter, `raise_for_status`, typed error
  translation, optional endpoint override, and response-size limits.
- Respect provider policy, rate limits, caching headers, attribution, and privacy.
  Nominatim usage in particular must stay at or below its public-service limit,
  identify UrbanPy, and be switchable/configurable.
- Add deterministic fixtures for CRS, coordinate order, geometry validity, units,
  empty data, nulls, and disconnected networks.
- Use coverage as a ratchet: no regression in total coverage and at least 80%
  coverage on new code, aligned with the SonarQube quality gate.
- Add a small benchmark suite for the performance work merged in PR #59 and fail
  only on agreed, repeatable regressions.

### W6. OSRM and Geofabrik lifecycle

**Outcome:** local OSRM is reproducible and cross-platform, and extract selection
does not depend on fragile path naming.

Implement the dedicated [`osrm-0.3.md`](osrm-0.3.md). It absorbs issues #21,
#26, and #29 and retires the duplicate `osrm_routing.py` implementation and the
platform-specific orchestration scripts.

### W7. Pydantic models, static typing, and API contracts

**Outcome:** untrusted inputs and stable public results have safe, documented
contracts without slowing geospatial computation.

Implement [`typed-models-0.3.md`](typed-models-0.3.md). Start with shared OSRM and
Geofabrik boundaries, then migrate external service clients module by module.

### W8. Geospatial correctness and existing defect backlog

**Outcome:** supported features behave correctly with the current geospatial
ecosystem and state their CRS/coordinate/unit assumptions.

- Fix and regression-test current H3 compatibility (#38).
- Fix current OSMnx API and coordinate-order compatibility (#20).
- Guarantee or explicitly require CRS on created and consumed objects (#27).
- Resolve HDX failures (#19 and #52) through the shared service boundary.
- Reproduce and fix `merge_shape_hex` re-use behavior (#14).
- Decide whether masked HDX population retrieval (#30) is feasible without
  misleading performance claims; otherwise defer it from 0.3.
- Add meaningful progress reporting for genuinely long operations (#31) without
  coupling library functions to one terminal renderer.
- Audit every `__all__` export and classify it as supported, deprecated, internal,
  or removed. Add public API and signature snapshots.
- Replace broad exception swallowing, sentinel mixes (`None`, `-1`, `NaN`), and
  library-level `print` calls with documented results, warnings, and exceptions.
- Standardize longitude/latitude order, CRS expectations, and distance/duration
  units across routing, download, geometry, and accessibility modules.

New feature PR #46 is evaluated separately. It is not on the 0.3 critical path
unless it satisfies the new data-source, dependency, test, and maintenance rules.

### W9. Documentation and community readiness

**Outcome:** installation, common workflows, limits, and contribution paths are
accurate for 0.3.

- Keep Sphinx for 0.3 unless a short ADR demonstrates that migration pays for
  itself; update it and build with warnings as errors.
- Rewrite installation and quickstart material against built artifacts and `uv`.
- Add task-oriented guides for downloads, H3 geometry, accessibility, remote
  routing APIs, and local OSRM.
- Add an external-service matrix covering credentials, endpoint configuration,
  rate limits, caching, attribution, privacy, failure modes, and live-test policy.
- Publish API reference, model JSON Schemas where useful, and a 0.3 migration guide.
- Turn maintained notebooks into deterministic examples or documentation tests;
  archive stale outputs and notebooks that cannot be reproduced (#28).
- Add `CITATION.cff`, accurate author/maintainer information, governance, support,
  security reporting, and a maintenance-status statement.
- Document OSM/Geofabrik attribution and data licensing separately from UrbanPy's
  software license.
- After a stable PyPI release, pursue a community-maintained conda-forge recipe
  rather than a private Anaconda channel (#16).

### W10. Release engineering and post-release operation

**Outcome:** exactly the reviewed artifacts are promoted, published, and supported.

- Use separate build and publish workflows; build once and promote the same
  immutable sdist/wheel artifacts.
- Trigger releases from protected, signed `v*` tags or an approved release
  workflow; validate tag and package versions without modifying source files.
- Publish alpha, beta, and release-candidate artifacts to TestPyPI and exercise
  documented clean-install smoke tests before production.
- Publish PyPI through trusted publishing, create GitHub release notes/changelog,
  and deploy documentation from the released version.
- Define rollback/yank criteria, post-release smoke tests, and on-call ownership.
- Monitor installation failures, security reports, upstream service contracts,
  and top user issues for at least four weeks after 0.3.0.

## Delivery phases and gates

### Phase 0 — Stabilize and secure

Required before new architecture work is merged:

- credential/security incident closed;
- PR test workflow is green and hermetic;
- SonarQube remains operational and is no longer best-effort;
- default-branch rules require human review and successful checks;
- current license-compliance failure has an owner and documented disposition;
- old issues and PRs are triaged into the Project.

### Phase 1 — 0.3.0a1 foundation

- `pyproject.toml`, supported Python range, `uv.lock`, and direct dependencies;
- stable lint/type/test/docs/package commands locally and in CI;
- artifact install tests and trusted-publishing dry run;
- Pydantic primitives and Geofabrik catalog models;
- OSRM catalog resolver and command-runner foundations.

### Phase 2 — 0.3.0b1 functional migration

- Python-owned OSRM prepare/start/status/stop lifecycle;
- typed external-service boundaries and consistent error behavior;
- priority compatibility issues (#14, #19, #20, #27, #38, #52) resolved;
- user and contributor documentation updated.

### Phase 3 — 0.3.0rc1 release hardening

- full supported Python/OS matrix green;
- manual OSRM acceptance evidence on macOS, Linux, and Windows;
- migration guide and API compatibility report complete;
- SBOM, vulnerability, dependency-license, package-content, and provenance gates
  pass;
- no unresolved P0/P1 defects or unowned high risks.

### Phase 4 — 0.3.0 and follow-through

- publish reviewed artifacts through trusted publishing;
- deploy versioned documentation and release notes;
- run post-release installation and OSRM smoke tests;
- begin conda-forge submission and four-week support observation.

## GitHub Project configuration

Recommended fields:

- Status: Triage, Backlog, Ready, In progress, In review, Blocked, Done
- Workstream: W0 through W10
- Priority: P0, P1, P2
- Work type: Decision, Implementation, Test, Documentation, Security, Release
- Target: Phase 0, 0.3.0a1, 0.3.0b1, 0.3.0rc1, 0.3.0, Post-0.3
- Risk: Low, Medium, High
- Effort: XS, S, M, L; split anything larger than L
- Agent readiness: Not suitable, Needs decision, Ready, Agent working
- Owner

Enable GitHub's native **Parent issue**, **Sub-issue progress**, and issue
dependency relationships rather than duplicating dependency state in a text
field.

Recommended views:

- Roadmap grouped by target and workstream
- Current iteration board
- Release gates (`priority:P0,P1` or `work-type:Release,Security`)
- Agent-ready queue
- Blocked work with dependency relationships
- Existing bugs and community contributions

Milestones represent published checkpoints. The Project represents execution.
Labels describe stable properties such as `area:osrm`, `area:typing`,
`area:packaging`, `breaking-change`, `good-first-issue`, `needs-design`, and
`agent:ready`.

## Issue definition of ready

Before an issue moves to Ready it has:

- one testable outcome and an explicit non-goal;
- linked parent, dependencies, and existing issue/PR history;
- public API, dependency, security, data-license, and migration impact identified;
- acceptance criteria and exact local verification commands;
- fixture/test strategy that avoids unapproved live services;
- owner/reviewer and estimated effort no larger than L.

## Pull-request definition of done

- linked issue acceptance criteria are satisfied;
- tests cover success, failure, and compatibility behavior;
- `uv lock --check` passes and dependency changes are explained;
- required lint, type, unit, docs, package, security, license, and SonarQube checks
  pass;
- public behavior, schemas, changelog, and migration notes are updated;
- generated/AI-assisted changes are disclosed and independently reviewed;
- no unrelated cleanup is bundled into the PR;
- one human reviewer approves after the latest material change.

## Definition of done for UrbanPy 0.3

- A new contributor can clone, bootstrap, check, test, build, and preview docs
  using documented `uv` and Trunk/fallback commands.
- PRs cannot merge without human approval, deterministic green CI, SonarQube,
  security analysis, and approved dependency compliance.
- Supported Python versions and operating systems pass clean wheel-install tests.
- `import urbanpy` has no network side effects and optional capabilities have
  honest dependency boundaries.
- OSRM uses one Python implementation on all platforms, canonical Geofabrik IDs
  and URLs, pinned container inputs, safe storage, readiness checks, and targeted
  cleanup.
- New boundary models provide actionable errors and stable schemas while large
  geospatial objects avoid per-row runtime validation.
- External-service calls identify UrbanPy, set timeouts, respect provider policy,
  and have hermetic PR tests plus scheduled live contracts.
- Public APIs state coordinate order, CRS, units, null behavior, and exceptions;
  compatibility changes have tests and migration notes.
- Built sdist/wheel contents, metadata, license, SBOM, provenance, and clean
  installation are verified before trusted publication.
- Documentation, citation, governance, security, support, and release ownership
  are current, and no P0/P1 issue or unowned high risk remains.


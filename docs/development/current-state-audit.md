# UrbanPy current-state audit for the 0.3 roadmap

Audit date: 2026-08-09

This is a planning baseline, not a claim that every defect has been reproduced on
every platform. Repository facts were inspected locally at commit `ddd0360`; live
GitHub/PyPI/tool facts should be refreshed when implementation begins.

## Executive assessment

UrbanPy has a useful domain scope and recent performance improvements, but the
current default branch is not release-ready. The highest risks are the unprotected
merge path, nondeterministic live-service tests, release credential/workflow
history, unresolved dependency-license status, legacy packaging, and an OSRM path
that can report success without a usable server.

The 0.3 roadmap is viable if work is sequenced as stabilization and release-chain
hardening first, then packaging/typing/OSRM migration, then public API and release
polish. Treating uv, Trunk, Pydantic, or an AI reviewer as a standalone solution
would leave the main production risks untouched.

## Repository baseline

- Default branch: `master` at `ddd0360` (merged PR #59).
- Package code plus tests: approximately 3,425 Python lines in the current tree.
- Packaging: legacy `setup.py`; package version is rewritten during release;
  `python_requires` still says Python 3.6 or newer.
- Dependency input: `requirements.txt` pins more than 100 direct and transitive
  packages together. `environment.yml` and docs requirements are additional,
  inconsistent sources.
- Latest OSMnx metadata requires Python 3.11 or newer, while current CI tests 3.9,
  3.10, and 3.11. The declared and tested support policies do not agree.
- PyPI's latest stable release is 0.2.1 from 2021; development releases appeared
  in 2023. Repository tags, PyPI releases, and source versioning need reconciliation.
- `urbanpy.__init__` eagerly imports all feature modules. Optional feature imports
  therefore cannot be optional, and HDX configuration is created at import time.
- `urbanpy/routing/osrm_routing.py` duplicates functionality in `routing.py` but is
  not part of the documented export path.
- Bash and PowerShell files are tracked but are not included as package data by the
  current wheel configuration.
- Pydantic is pinned in the dependency file but not used by UrbanPy; it appears as
  dependency-tree baggage rather than an intentional contract.

## Pull-request and automation baseline

Current repository workflows visibly provide:

- test/docs/release/deploy workflow;
- SonarQube scan;
- CodeQL;
- GitGuardian;
- organization-level License Compliance status;
- Copilot pull-request review.

Findings:

- The organization ruleset requires a PR and blocks deletion/non-fast-forward
  updates, but currently requires zero approvals, no thread resolution, and no
  successful status checks.
- The latest inspected PR (#60) is unstable: Python build jobs fail, while docs,
  SonarQube, CodeQL, and GitGuardian pass.
- Six geometry tests fail because live Nominatim requests return HTTP 403; the
  response body is then parsed as JSON. Other tests call live HDX and OSMnx/Overpass.
- The OSRM test is deselected in CI rather than replaced by unit/contract coverage.
- The same PR received duplicate test/docs runs from overlapping push and PR events.
- The License Compliance status reports 104 issues and has no result URL. The exact
  findings require owner/tool investigation; the failure must not be waived blindly.
- SonarQube dependency installation and coverage are marked best-effort, failures
  are suppressed, and `sonar.sources=.` makes source/test/notebook scope ambiguous.
- The scan job can pass without proving that tests or coverage succeeded and does
  not explicitly wait for the quality gate in repository configuration.
- CI still uses old major Actions and several floating `@master`/`@latest` action
  references. Current runner logs warn about forced Node runtime compatibility.
- The combined workflow gives release/deploy logic a very large blast radius and
  mutates source files to create a version.

## Test and API baseline

- The current suite collects roughly 15 tests. Most geometry tests and the HDX
  test depend on changing public data/services.
- Tests include a maintainer's personal email address as Nominatim identification.
- There are placeholder/pass tests for important Google and ORS behavior.
- Assertions sometimes compare `.all()` booleans instead of numeric arrays and
  several expected live results are inherently unstable.
- HTTP calls generally omit explicit timeouts and consistent status handling.
- Nominatim currently uses `requests`' default User-Agent, contrary to public
  service identification requirements, which explains the observed 403 risk.
- Broad `except Exception`, printing, and mixed sentinels (`None`, `-1`, `NaN`,
  raw `Response`) make failure behavior hard to automate or type safely.
- Coordinate order, CRS, and seconds/minutes are not consistently encoded in names
  or types. Some docstrings and examples disagree with current functions.
- Public exports are controlled by star imports and module `__all__` lists, with no
  compatibility snapshot or explicit stability classification.

## OSRM baseline

- The API requires hand-authored `country` and `continent` fragments.
- Geofabrik nested paths and slash-containing canonical IDs are unsupported.
- The official Geofabrik v1 catalog already supplies unique IDs, parents, ISO
  aliases, and complete PBF URLs with a versioned stable structure.
- Bash and PowerShell implementations diverge and hard-code platform paths.
- Docker image, port, temporary names, sleeps, cleanup, and error output are not
  safe for concurrent or automated use.
- The MLD command sequence uses the PBF filename for partition/customize/routed,
  rather than the prepared `.osrm` base shown by OSRM's supported flow.
- No manifest proves which PBF/profile/image created existing artifacts.

## Security, licensing, and community baseline

- Recent repository history includes removal of a malicious workflow and an open
  PR to replace an exposed PyPI token. Incident closure and credential revocation
  must be evidenced, not inferred from file deletion alone.
- Secret scanning and push protection are enabled, which is a useful existing
  control to preserve.
- GPL-3 is stated, but package metadata and an EL-BID-approved precise SPDX/license
  compatibility policy are not present.
- There is no `SECURITY.md`, CODEOWNERS policy, support policy, or release ownership
  document in the inspected tree.
- README and Sphinx docs still recommend Python 3.6-era environments and old
  operating systems; README also contains obsolete analytics beacon markup.
- Citation exists as BibTeX text but not `CITATION.cff`.
- Contribution guidance references an internal repository/automatic merge process
  that does not match the visible public workflow.

## Existing issue/PR reconciliation

| Existing item | 0.3 disposition |
| --- | --- |
| PR #60 trusted publishing | Phase 0; fix CI, verify credential revocation, then merge/supersede |
| PR #58 Sonar config | Triage as likely superseded by merged Sonar files; preserve intent |
| PRs #54–#56 dependency bumps | Re-evaluate after direct-dependency/uv migration; do not merge stale full-lock pins blindly |
| PR #46 satellite embeddings | Separate feature review; not on critical path by default |
| #21 nested Geofabrik regions | Absorb into OSRM catalog resolver |
| #26 Windows OSRM | Absorb into one cross-platform Python manager |
| #29 missing OSRM scripts | Close by eliminating script-owned logic and wheel-test the replacement |
| #38 latest H3 incompatibility | Phase 2 compatibility gate |
| #20 OSMnx nearest-node API | Phase 2 compatibility gate |
| #27 CRS on generated frames | Phase 2 correctness gate |
| #19 and #52 HDX failures | Shared typed HTTP/client boundary plus regression fixtures |
| #14 merge reuse bug | Reproduce and fix in Phase 2 |
| #15 download API compatibility | Address through versioning, release notes, and deprecation policy |
| #16 Conda distribution | Submit to conda-forge after stable PyPI 0.3, not a private release job |
| #28 notebook docs | Convert maintained examples; archive stale outputs |
| #30 masked HDX retrieval | Feasibility decision; defer if upstream format prevents real savings |
| #31 progress feedback | Presentation adapter after operations expose progress events |

## Plan changes resulting from this review

The original plans were directionally sound but incomplete. This review adds:

- a Phase 0 stabilization/security gate before new architecture;
- supply-chain, license, SBOM, credential, and provenance work as a separate
  workstream;
- exact branch-rules and human-review requirements;
- a vendor-neutral, least-privilege operating model for remote AI agents;
- a measured CodeRabbit/Copilot review pilot rather than an automatic required bot;
- explicit Trunk adoption criteria and standard-tool fallback;
- external-service compliance and scheduled live contracts;
- direct dependency/optional import architecture and Python 3.11+ recommendation;
- correct OSRM `.osm.pbf` to `.osrm` sequencing, manifests, atomic downloads,
  locking, readiness, labeling, and safe cleanup;
- public versus internal Pydantic model taxonomy, schema stability, redaction,
  static typing, and migration rules;
- measurable phase gates, issue Definition of Ready, PR Definition of Done, and
  post-release support.

## Primary external references

- uv project locking/syncing: <https://docs.astral.sh/uv/concepts/projects/sync/>
- uv package build/publish: <https://docs.astral.sh/uv/guides/package/>
- Geofabrik catalog schema: <https://download.geofabrik.de/technical.html>
- OSRM backend: <https://github.com/Project-OSRM/osrm-backend>
- Pydantic documentation: <https://docs.pydantic.dev/latest/>
- SonarQube quality gates:
  <https://docs.sonarsource.com/sonarqube-server/2026.1/quality-standards-administration/managing-quality-gates/introduction-to-quality-gates/>
- GitHub rulesets:
  <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets>
- GitHub sub-issues and dependencies:
  <https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/about-issues>
- Nominatim usage policy:
  <https://operations.osmfoundation.org/policies/nominatim/>
- CodeRabbit plans: <https://docs.coderabbit.ai/management/plans>
- Greptile pricing: <https://www.greptile.com/pricing>
- conda-forge package contribution:
  <https://conda-forge.org/docs/maintainer/adding_pkgs/>


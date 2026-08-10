# UrbanPy 0.3 release-readiness record

Status recorded on 2026-08-10 for the dependency-ordered stack rooted at PR #61.
This record distinguishes code-complete evidence from decisions that require an
EL-BID administrator, security reviewer, or legal reviewer.

## Code-complete gates

| Area | Evidence |
| --- | --- |
| Development | uv lock, PEP 621 metadata, Python 3.11–3.14 CI, Trunk, Ruff, and strict mypy boundary scope |
| PR reliability | Network-blocked hermetic suite, captured provider contracts, 88 passing tests, and 86.9% Sonar new-code coverage |
| SonarQube | Mandatory scanner waits for and fails on the EL-BID quality gate; no bypass or best-effort path |
| Geofabrik | Official `index-v1-nogeom.json`, exact canonical IDs/ISO aliases, and advertised PBF URLs |
| OSRM | Shell-free Python lifecycle, pinned digest, atomic/resumable data, MLD paths, locks, ownership, readiness, cleanup, and typed HTTP client |
| Compatibility | Current H3, OSMnx, GeoPandas, HDX, Plotly MapLibre, CRS, and rerunnable geometry regression coverage |
| Boundaries | Strict public Pydantic values, private provider transports, safe exceptions, explicit module exports, and documented coordinate/unit conventions |
| Supply chain | Immutable Action SHAs, locked runtime audit, fail-closed license evidence, SBOM/provenance release build, and private vulnerability reporting |
| Publishing | Build-once OIDC promotion, protected-environment hooks, tag/artifact/commit validation, and stable/prerelease target policy |
| Community | Security, support, governance, contribution, changelog, citation, release, and API-stability documentation |
| Automation | Bounded agent instructions/CODEOWNERS and advisory CodeRabbit configuration for drafts and stacked PRs |

## Required external decisions

These tasks are intentionally not agent-completable and block the corresponding
milestone:

- #101: inspect and remediate 13 Sonar findings and review every security hotspot
  in the restricted SonarQube dashboard. Never weaken the quality gate.
- #99: reconcile 95 FOSSA findings with EL-BID legal policy and confirm revocation
  and audit history for legacy PyPI/TestPyPI tokens.
- #102: configure protected `release-testpypi` and `release-pypi` environments,
  exact trusted publishers, reviewers, and protected `v*` tags before publishing.
- #100: optionally approve the CodeRabbit GitHub App after permission and data
  review. AI review remains advisory and is not a release blocker.
- #104: after `contracts.yml` reaches the default branch, dispatch and record the
  first live-provider and Docker OSRM acceptance run. GitHub does not permit the
  manual dispatch while the workflow exists only on a feature branch.

## Merge and release rule

Review and merge the stack in the dependency order documented on PR #61. Do not
tag or publish while required Sonar/FOSSA findings are unresolved. After the
admin setup is complete, exercise an alpha or release candidate on TestPyPI and
the documented small-region OSRM smoke test before deciding that `0.3.0` is
stable. Release authority remains human-only.

# Release runbook

Only a human maintainer may tag, approve, publish, yank, or release UrbanPy.
Automation builds and verifies artifacts but never chooses to release them.

## One-time trusted-publishing setup

Repository and PyPI administrators must create protected GitHub environments
named `release-testpypi` and `release-pypi`, require designated maintainer
reviewers, prevent self-review, and restrict deployment to protected `v*` tags.
Configure matching trusted publishers on TestPyPI and PyPI for
`release-publish.yml` and the exact environment name. Do not add API tokens.

Protect release tags and require the same human review, CI, mandatory SonarQube,
security, and dependency-compliance gates used for the default branch. These are
administrator actions and are intentionally not performed by coding agents.

## Prerelease procedure

1. Reconcile `CHANGELOG.md`, version metadata, deprecations, and migration docs.
2. Confirm supported Python CI, docs, package, vulnerability, license, and
   mandatory SonarQube checks are green on the reviewed commit.
3. Set an alpha, beta, or release-candidate version and merge through normal
   review. A maintainer creates the matching protected tag, such as `v0.3.0rc1`.
4. `release-build.yml` validates the tag, builds once, inspects the artifacts,
   creates a CycloneDX SBOM, runs a clean install, attests provenance, and stores
   one immutable bundle.
5. Inspect the build log, SBOM, provenance, wheel/sdist, and artifact run ID.
6. Dispatch `release-publish.yml` with that run ID, exact version, and
   `testpypi`. A protected-environment reviewer approves OIDC publication.
7. Install from TestPyPI in a clean environment and exercise imports, a local
   geometry workflow, canonical Geofabrik resolution, and the documented OSRM
   smoke test on each claimed platform.

The workflow rejects prerelease versions sent to production PyPI.

## Stable release procedure

Repeat the review with a stable version and protected tag. Dispatch publish with
target `pypi`. The exact already-built artifacts are promoted through OIDC; no
build occurs in the publish job. After PyPI succeeds, the workflow creates the
GitHub release from the same bundle and existing tag.

Deploy versioned documentation from the released version only after package
publication and smoke tests succeed. Submit a conda-forge recipe after the stable
PyPI artifact has community validation; do not maintain a private Conda publish
workflow.

## Failure, rollback, and post-release

- Before publication, abandon the tag and create a corrected version; never
  replace artifacts under an existing version.
- After publication, yank only for security, data-loss, installation, or severe
  correctness defects. Publish a fixed patch; do not silently overwrite files.
- Use a private security advisory and coordinated disclosure for vulnerabilities.
- Record the incident, affected versions, mitigations, and upgrade path in the
  changelog and GitHub release.
- For four weeks, monitor installation failures, provider contracts, security
  reports, dependency alerts, and OSRM platform evidence. Assign an accountable
  maintainer before starting the release.

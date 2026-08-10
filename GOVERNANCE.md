# Governance

UrbanPy is an EL-BID open-source project maintained in public on GitHub.

## Roles and decisions

Maintainers triage issues, define supported APIs, review contributions, manage
security reports, and approve releases. Contributors propose work through issues
and pull requests. Technical decisions are documented in the relevant issue or
PR; public API, dependency, data-license, security, and migration impact must be
explicit.

Changes are accepted by maintainer review after required automation is green.
SonarQube is mandatory under EL-BID policy. Dependency/license findings require
an explicit maintainer disposition and are not dismissed by automation.

## Automation and agents

Automation may create branches, issues, and dependency-ordered pull requests.
It may not approve or merge its own work, publish packages, change repository
secrets or branch protection, or dismiss security and license findings. Human
maintainers retain release and administrative authority. The repository's
`AGENTS.md`, CODEOWNERS, and pull-request template define the operational rules.

## Releases and compatibility

UrbanPy follows semantic versioning. Deprecations emit a documented warning for
at least one minor release when practical. Breaking changes require an issue,
migration notes, and a major version unless needed to correct a security or data
integrity defect during a prerelease.

Release artifacts are built once from a reviewed tag and promoted through
protected environments. A maintainer approves publication and post-release
support. The release-engineering workstream maintains the operational runbook
alongside the publish workflows.

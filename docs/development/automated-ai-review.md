# Automated AI review

## Decision

CodeRabbit is the recommended optional first-pass reviewer for UrbanPy pull
requests. As verified in August 2026, its Free plan supports unlimited public
repositories without a credit card, and qualifying open-source projects can use
additional features without a paid subscription. Greptile's free open-source
offer is restricted to qualified non-commercial MIT or Apache projects, so it
does not fit UrbanPy's GPL-3.0-only license.

This is a convenience layer, not a release or compliance authority. AI comments
do not replace maintainer review, hermetic tests, Trunk, mandatory SonarQube,
FOSSA/legal review, or protected publishing approval. The AI reviewer must not be
the only required approval.

## Repository configuration

The checked-in `.coderabbit.yaml` opts into automatic and incremental review for
every target branch, including draft and stacked pull requests. Its path-specific
instructions reinforce `AGENTS.md` for Python boundaries, OSRM, tests, workflows,
and documentation. Keeping policy in the repository makes review behavior
versioned and visible even though the service installation is external.

## Maintainer activation

An EL-BID organization owner must complete issue #100:

1. Review CodeRabbit's current terms, data handling, and requested GitHub App
   permissions. At the time of evaluation it requested read access to Actions,
   checks, discussions, members, and metadata, plus write access to code, commit
   statuses, issues, and pull requests.
2. Install the GitHub App for `EL-BID/urbanpy` only; do not grant organization-wide
   repository access by default.
3. Confirm that reviews run on a draft stacked PR and on a PR targeting `master`.
4. Keep findings advisory until maintainers have measured signal, noise, latency,
   and data-governance fit across several PRs.
5. Reassess pricing and permissions before making any automation a required check.

No API key, workflow secret, or self-hosted action is needed for the GitHub App
integration. If the app is removed, the repository continues to function with
its deterministic required gates.

## Sources checked

- <https://docs.coderabbit.ai/management/plans>
- <https://docs.coderabbit.ai/platforms/github-com>
- <https://docs.coderabbit.ai/configuration/auto-review>
- <https://docs.coderabbit.ai/configuration/path-instructions>
- <https://www.greptile.com/pricing>

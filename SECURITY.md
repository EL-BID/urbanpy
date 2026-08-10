# Security policy

## Supported versions

Security fixes are made on the default branch and released in the newest
maintained minor series. During the 0.3 prerelease cycle, `0.3.0a*`, `0.3.0b*`,
and `0.3.0rc*` are evaluation builds and may receive breaking fixes. The 0.2
series receives critical fixes only until 0.3.0 is stable; older versions are
unsupported.

## Report a vulnerability privately

Do not disclose vulnerabilities in a public issue, pull request, discussion,
notebook, or chat. Use **Security → Advisories → Report a vulnerability** in
the [UrbanPy repository](https://github.com/EL-BID/urbanpy/security/advisories/new).
GitHub private vulnerability reporting is enabled for this repository.

Include the affected version or commit, impact, reproduction prerequisites,
minimal proof of concept, and any suggested mitigation. Remove credentials,
personal data, and sensitive provider responses.

Maintainers aim to acknowledge a report within five working days, provide a
triage decision within ten working days, and coordinate publication after a fix
is available. These are response targets, not a bug-bounty or compensation
commitment.

## Scope

UrbanPy code, packaging, published artifacts, release automation, and unsafe
handling of external data are in scope. Vulnerabilities in upstream services or
dependencies should also be reported to their owners; tell UrbanPy privately
when the library needs a mitigation or dependency update.

Security advisories, CVEs when appropriate, patched-version ranges, and upgrade
instructions are published through GitHub and the changelog. SonarQube remains
a mandatory EL-BID quality gate and does not replace coordinated disclosure.

# Support policy

UrbanPy is community-maintained open-source software. Public support is provided
on a best-effort basis; no service-level agreement is implied.

- Use [GitHub Issues](https://github.com/EL-BID/urbanpy/issues) for reproducible
  bugs and scoped feature proposals.
- Use the bug form and include UrbanPy/Python versions, operating system, CRS,
  a minimal synthetic example, and redacted logs.
- Search existing issues before opening a new report.
- Do not use public issues for vulnerabilities; follow [SECURITY.md](SECURITY.md).
- Questions about institutional deployments, private data, or EL-BID policy
  should use the appropriate institutional support channel rather than the
  public tracker.

The supported Python range is declared in `pyproject.toml` and exercised in CI.
Provider-backed features depend on third-party availability and policy; unit
tests use captured contracts, while scheduled live checks detect upstream drift.
Docker-backed OSRM support is limited to platforms for which release evidence is
recorded. See the OSRM guide before processing large regions.

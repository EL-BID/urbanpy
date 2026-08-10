# UrbanPy pull request

## Summary

<!-- What changes for users or maintainers? -->

## Issue and stack

<!-- Use "Closes #..." and name the base/next PR for stacked work. -->

## Validation

- [ ] `uv run pytest`
- [ ] `uv run ruff check urbanpy tests`
- [ ] `trunk check`
- [ ] Documentation and changelog updated when behavior changes

## Risk checklist

- [ ] Default tests remain hermetic (no network or Docker)
- [ ] Public API compatibility was preserved or the break is explicitly approved
- [ ] No credentials, personal data, or non-redistributable fixtures were added
- [ ] SonarQube and other required checks were not bypassed or weakened
- [ ] Third-party Actions are pinned to immutable SHAs

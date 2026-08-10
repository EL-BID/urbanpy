# Runtime dependency license review

Snapshot date: 2026-08-09. This is an engineering control and inventory, not
legal advice or a substitute for EL-BID review.

## Scope and result

`scripts/check_licenses.py` walks installed distribution metadata from the
UrbanPy project through its active runtime requirements. It excludes development
extras and emits a deterministic JSON inventory. Against the locked 0.3 alpha
environment, 89 runtime distributions have an explicit reviewed disposition.

The exact accepted metadata strings live in `license-policy.toml`. A new package
or a changed license string fails closed so a maintainer must investigate it.
This repository check complements, and does not remove or dismiss, the external
FOSSA License Compliance check. FOSSA findings remain blocking until EL-BID
records an acceptable disposition in that system.

## Package-specific dispositions

- `defopt` 7.0.0 reports no license in wheel metadata. Its official repository
  license is MIT; the policy records that source rather than globally allowing
  `UNKNOWN`.
- `text-unidecode` 1.3 offers GPL/GPLv2+ or Artistic terms in its official
  license file. UrbanPy relies on the GPLv2+ option, which permits use under
  GPLv3. The package override records that selection explicitly.

The runtime closure otherwise reports permissive, public-domain, weak-copyleft,
or GPL-compatible alternatives covered by the reviewed exact policy. Compound
expressions and legacy classifier strings are retained in the output so the
evidence does not overstate metadata quality.

## Release evidence

Normal CI uploads the locked requirements export and dependency-license JSON.
The release build additionally stores them beside the CycloneDX SBOM and
attested wheel/sdist. The publish job promotes that bundle unchanged.

## Maintainer obligations

- Review every policy change and the corresponding primary license source.
- Reconcile FOSSA's complete finding set, including source, development,
  generated, and vendored assets that are outside the runtime closure.
- Obtain EL-BID legal approval when license compatibility or data licensing is
  ambiguous; do not encode an automated guess as approval.
- Preserve license notices required by distributions and data providers.

Contributing
============

Search existing issues before proposing work. Reproducible bug reports should
include UrbanPy and Python versions, operating system, CRS, a small synthetic
example, and redacted logs. Never put credentials, personal data, or private
provider payloads in an issue or fixture.

Development setup
-----------------

.. code-block:: console

   uv sync --locked --all-groups
   uv run pytest
   trunk check

The default tests disable network sockets. Captured provider contracts belong
in the normal suite; real-provider tests use ``@pytest.mark.live`` and Docker
tests use ``@pytest.mark.docker``. Run those only in an explicitly prepared
environment.

Pull requests
-------------

Keep changes focused, link an issue with acceptance criteria, and add regression
tests for fixes. Dependency-ordered stacked pull requests are welcome when each
layer remains independently reviewable. Update documentation and the changelog
for user-visible behavior.

Required CI, security, dependency-compliance, and documentation checks must
pass. SonarQube is mandatory under EL-BID policy and is never best effort. A
human maintainer reviews and merges changes; automation and agents do not
approve, merge, or release their own work.

Read the full `repository contribution guide
<https://github.com/EL-BID/urbanpy/blob/master/CONTRIBUTING.md>`__, `governance
policy <https://github.com/EL-BID/urbanpy/blob/master/GOVERNANCE.md>`__, and
:doc:`code_of_conduct` before contributing.

# Contributing guidelines

## Pull request checklist

Before sending a pull request, be sure to follow this list.

* Read the [contributing guidelines](CONTRIBUTING.md)
* Read the [code of conduct](CODE_OF_CONDUCT.md)
* Check if your changes comply with the [style guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md)

## How to become a contributor and submit your own code

We'd love to accept your changes, suggestions and patches! Be sure that your
changes, source code, and other ideas/implementations do not cause intellectual property
issues.

## Contributing code

If you have any improvements or new functionality that is interesting for UrbanPy,
send us your pull requests! If you are new to pull requests, see Github's [how to guide](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/about-pull-requests).

UrbanPy team members will be assigned to review your pull requests. Once the pull requests are approved and pass continuous integration checks, a UrbanPy team member will apply ready to pull label to your change. This means we are working on getting your pull request submitted to our internal repository. After the change has been submitted internally, your pull request will be merged automatically on GitHub.

## Contribution guidelines and standards

Before sending your pull request for review, make sure your changes are consistent with the guidelines and follow the Google coding style.

### General guidelines and philosophy for contribution

* Include unit tests when you contribute new features, as they help to a) prove that your code works correctly, and b) guard against future breaking changes to lower the maintenance cost.
* Bug fixes also generally require unit tests, because the presence of bugs usually indicates insufficient test coverage.
* When you contribute a new feature to UrbanPy, the maintenance burden is (by default) transferred to the UrbanPy team. This means that the benefit of the contribution must be compared against the cost of maintaining the feature.
* Full new features (e.g., a cutting-edge travel time matrix computation algorithm) typically will live in urbanpy/utils to get some airtime before a decision is made regarding whether they are to be migrated to the core modules.
* As every PR may require several CPU hours of CI testing, we discourage submitting PRs to fix one typo, one warning, etc. We recommend fixing the same issue at the file level at least (e.g.: fix all typos in a file, fix all compiler warning in a file, etc.)

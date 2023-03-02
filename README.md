Ramble is a multi-platform experimentation framework to increase exploration
productivity and improve reproducibility. Ramble is capable of driving software
installation, acquire input files, configure experiments, and extract results.
It works on Linux, macOS, and many supercomputers.

Ramble can be used to configure a variety of experiments for applications.
These can include anything from:
 - Scientific parameter sweeps
 - Performance focused scalaing studies
 - Compiler flag sweeps

To install ramble and configure your experiment workspace, make sure you have Python.
Then:

    $ git clone -c feature.manyFiles=true https://github.com/GoogleCloudPlatform/ramble.git
    $ cd ramble/bin
    $ ./ramble workspace create -d test_workspace -c ../examples/basic_hostname_config.yaml

Dependencies
------------

Ramble’s python dependencies can be installed using the included requirements.txt file.

e.g.

    $ pip install -r requirements.txt

Outside of these requirements, ramble requires an existing installation of
spack for some application definition. See
[Spack’s documentation](https://github.com/spack/spack#-spack) to install Spack.

Documentation
----------------

For help with Ramble’s commands, run `ramble help` or `ramble help --all`.

For more information on concepts in Ramble, see Ramble’s
[Getting Started](./lib/ramble/docs/getting_started.rst) guide.

Example configuration files are also contained in the
[examples](./examples) directory.

Community
------------------------

Ramble is an open source project.  Questions, discussion, and
contributions are welcome. Contributions can be anything from new
packages to bugfixes, documentation, or even new core features.

Resources:

* [**Github Discussions**](https://github.com/GoogleCloudPlatform/ramble/discussions): not just for discussions, also Q&A.

Contributing
------------------------
Contributing to Ramble is relatively easy.  Just send us a
[pull request](https://help.github.com/articles/using-pull-requests/).
When you send your request, make ``develop`` the destination branch on the
[Ramble repository](https://github.com/GoogleCloudPlatform/ramble).

Your PR must pass Ramble's unit tests and documentation tests, and must be
[PEP 8](https://www.python.org/dev/peps/pep-0008/) compliant.  We enforce
these guidelines with our CI process. To run these tests locally,
please use the test runners:
 - share/ramble/qa/run-unit-tests
 - share/ramble/qa/run-flake8-tests

 For additional requirements about contributing, including Google’s CLA, see our
 [Contribution Guide](.github/CONTRIBUTING.md).


Ramble's `develop` branch has the latest contributions. Pull requests
should target `develop`, and users who want the latest package versions,
features, etc. can use `develop`.

Releases
--------

Each Ramble release series also has a corresponding branch, e.g.
`releases/v0.1` has `0.1.x` versions of Ramble, and `releases/v0.2` has
`0.2.x` versions. We backport important bug fixes to these branches but
we do not advance the application definitions or make other changes that would
change the way experiments Ramble would create within a release branch.
So, you can base your Ramble deployment on a release branch subsequent updates
can be considered non-breaking.

The latest release is always available with the `releases/latest` tag.

Code of Conduct
------------------------

Please note that Ramble has a
[**Code of Conduct**](.github/CODE_OF_CONDUCT.md). By participating in
the Ramble community, you agree to abide by its rules.

Authors
----------------
Many thanks go to Ramble's [contributors](https://github.com/GoogleCloudPlatform/ramble/graphs/contributors).

Ramble was created by Doug Jacobsen, dwjacobsen@google.com.

License
----------------

This software is distributed under the terms of both the MIT license and the
Apache License (Version 2.0).

See LICENSE for details.

SPDX-License-Identifier: (Apache-2.0 OR MIT)

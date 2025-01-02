#!/bin/bash -e
# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

#
# Description:
#     Common setup code to be sourced by Ramble's test scripts.
#

QA_DIR="$(dirname ${BASH_SOURCE[0]})"
export RAMBLE_ROOT=$(realpath "$QA_DIR/../../..")

# Source the setup script
. "$RAMBLE_ROOT/share/ramble/setup-env.sh"

# by default coverage is off.
coverage=""
coverage_run=""

# Set up some variables for running coverage tests.
if [[ "$COVERAGE" == "true" ]]; then
    # these set up coverage for Python
    coverage=coverage
    coverage_run="coverage run"

    # bash coverage depends on some other factors
    mkdir -p coverage
    bashcov=$(readlink -f ${QA_DIR}/bashcov)

    # instrument scripts requiring shell coverage
    if [ "$(uname -o)" != "Darwin" ]; then
        # On darwin, #! interpreters must be binaries, so no sbang for bashcov
        sed -i~ "s@#\!/bin/sh@#\!${bashcov}@"   "$RAMBLE_ROOT/bin/sbang"
    fi
fi

#
# Description:
#     Check to see if dependencies are installed.
#     If not, warn the user and tell them how to
#     install these dependencies.
#
# Usage:
#     check-deps <dep> ...
#
# Options:
#     One or more dependencies. Must use name of binary.
check_dependencies() {
    for dep in "$@"; do
        if ! which $dep &> /dev/null; then
            # Map binary name to package name
            case $dep in
                sphinx-apidoc|sphinx-build)
                    pip_package=sphinx
                    ;;
                coverage)
                    pip_package=coverage
                    ;;
                flake8)
                    pip_package=flake8
                    ;;
                dot)
                    search_package=graphviz
                    ;;
                git)
                    search_package=git
                    ;;
                hg)
                    pip_package=mercurial
                    ;;
                kcov)
                    search_package=kcov
                    ;;
                svn)
                    search_package=subversion
                    ;;
                *)
                    search_package=$dep
                    pip_package=$dep
                    ;;
            esac

            echo "ERROR: $dep is required to run this script."
            echo

            if [[ $pip_package ]]; then
                echo "To install with pip, run:"
                echo "    $ pip install $pip_package"
            fi


            if [[ $search_package ]]; then
                echo "Please ensure the following package is installed:"
                echo "    $search_package"
            fi


            if [[ $search_package || $pip_package ]]; then
                echo "Then add the bin directory to your PATH."
            fi

            exit 1
        fi

        # Flake8 and Sphinx require setuptools in order to run.
        # Otherwise, they print out this error message:
        #
        #   Traceback (most recent call last):
        #     File: "/usr/bin/flake8", line 5, in <module>
        #       from pkg_resources import load_entry_point
        #   ImportError: No module named pkg_resources
        #
        # Print a more useful error message if setuptools not found.
        if [[ $dep == flake8 || $dep == sphinx* ]]; then
            # Find which Python is being run
            # Spack-installed packages have a hard-coded shebang
            python_cmd=$(head -n 1 $(which $dep) | cut -c 3-)
            # May not have a shebang
            if [[ $python_cmd != *python* ]]; then
                python_cmd=python
            fi
            # Check if setuptools is in the PYTHONPATH
            if ! $python_cmd -c "import setuptools" 2> /dev/null; then
                echo "ERROR: setuptools is required to run $dep."
                echo "Please add it to your PYTHONPATH."

                exit 1
            fi
        fi
    done
    echo "Dependencies found."
}

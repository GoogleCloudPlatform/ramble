# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Consolidated module for all imports done by Ramble.

Many parts of Ramble have to import Python code. This utility package
wraps Ramble's interface with Python's import system.

We do this because Python's import system is confusing and changes from
Python version to Python version, and we should be able to adapt our
approach to the underlying implementation.

Currently, this uses ``importlib.machinery`` where available and ``imp``
when ``importlib`` is not completely usable.
"""

# TODO: (dwjacobsen) This logic matches spack v0.16.0.
#       The import logic should be updated to match v0.18.0
#       at some point in the future.

try:
    from .importlib_importer import load_source  # noqa
except ImportError:
    from .imp_importer import load_source  # noqa

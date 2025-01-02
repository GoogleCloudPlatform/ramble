# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import platform
import sys

import pytest

import ramble
from ramble.main import RambleCommand

python = RambleCommand("python")


def test_python():
    out = python("-c", "import ramble; print(ramble.ramble_version)")
    assert out.strip() == ramble.ramble_version


def test_python_interpreter_path():
    out = python("--path")
    assert out.strip() == sys.executable


def test_python_version():
    out = python("-V")
    assert platform.python_version() in out


def test_python_with_module():
    # pytest rewrites a lot of modules, which interferes with runpy, so
    # it's hard to test this.  Trying to import a module like sys, that
    # has no code associated with it, raises an error reliably in python
    # 2 and 3, which indicates we successfully ran runpy.run_module.
    with pytest.raises(ImportError, match="No code object"):
        python("-m", "sys")


def test_python_raises():
    out = python("--foobar", fail_on_error=False)
    assert "Error: Unknown arguments" in out

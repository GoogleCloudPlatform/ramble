# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import shutil
import subprocess

import pytest

import ramble.paths

pytestmark = pytest.mark.maybeslow

# TODO: add tests for other supported shells
_SHELLS_TO_TEST = ["bash", "fish"]

_SETUP_ENV_FILE = {
    "bash": "setup-env.sh",
    "fish": "setup-env.fish",
}


@pytest.mark.parametrize("shell", _SHELLS_TO_TEST)
def test_shell_wrapper_workspace_activate_missing(shell, tmpdir):
    """Test activation of missing workspace fails with proper exit code."""
    if not shutil.which(shell):
        pytest.skip(f"{shell} not found")

    setup_env = os.path.join(ramble.paths.prefix, "share", "ramble", _SETUP_ENV_FILE[shell])
    test_script_path = str(tmpdir.join("test_missing.sh"))

    with open(test_script_path, "w") as f:
        f.write(
            f"""
. "{setup_env}"
ramble workspace activate non_existent_workspace
"""
        )

    cmd = [shell, test_script_path]
    process = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(tmpdir), env=os.environ.copy()
    )

    assert process.returncode == 1

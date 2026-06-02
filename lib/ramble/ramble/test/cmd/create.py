# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.main import RambleCommand

repo_cmd = RambleCommand("repo")
create_cmd = RambleCommand("create")


def test_create_help():
    """Verify create --help options."""
    with pytest.raises(SystemExit):
        create_cmd("--help")
    assert create_cmd.returncode in (None, 0)


def test_create_application_and_modifier(mutable_config, tmpdir):
    """Verify successful generation of new stubs inside a mock repo."""
    repo_path = str(tmpdir.join("test_repo"))
    repo_name = "mockrepo"

    # 1. Setup temporary repository
    repo_cmd("create", repo_path, repo_name)
    repo_cmd("add", "-t", "applications", "--scope=site", repo_path)
    repo_cmd("add", "-t", "modifiers", "--scope=site", repo_path)

    # 2. Create Application definition
    create_cmd(
        "application",
        "my-test-app",
        "--repo",
        repo_path,
        "--maintainers",
        "alice,bob",
        "--tags",
        "bio,gpu",
    )

    app_file = os.path.join(repo_path, "applications", "my-test-app", "application.py")
    assert os.path.exists(app_file)

    with open(app_file) as f:
        content = f.read()
        assert "class MyTestApp(ExecutableApplication):" in content
        assert 'name = "my-test-app"' in content
        assert "maintainers = ['alice', 'bob']" in content
        assert "tags = ['bio', 'gpu']" in content

    # 3. Create Modifier definition with custom base class
    create_cmd("modifier", "my-custom-mod", "--repo", repo_path, "--base", "BasicModifier")

    mod_file = os.path.join(repo_path, "modifiers", "my-custom-mod", "modifier.py")
    assert os.path.exists(mod_file)

    with open(mod_file) as f:
        content = f.read()
        assert "class MyCustomMod(BasicModifier):" in content
        assert 'name = "my-custom-mod"' in content


def test_create_duplicate_raises_error(mutable_config, tmpdir):
    """Verify error is thrown if creating a duplicate object."""
    repo_path = str(tmpdir.join("test_repo"))
    repo_name = "mockrepo"

    repo_cmd("create", repo_path, repo_name)
    repo_cmd("add", "-t", "applications", "--scope=site", repo_path)

    # Create first app
    create_cmd("application", "duplicate-app", "--repo", repo_path)

    from ramble.error import RambleCommandError

    # Second creation of same name should fail
    with pytest.raises(RambleCommandError):
        create_cmd("application", "duplicate-app", "--repo", repo_path)

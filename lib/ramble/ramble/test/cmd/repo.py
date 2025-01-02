# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
import os

import pytest

from ramble.main import RambleCommand
from ramble.repository import BadRepoError

repo = RambleCommand("repo")


def test_help_option():
    with pytest.raises(SystemExit):
        repo("--help")
    assert repo.returncode in (None, 0)


def test_create_add_list_remove(mutable_config, tmpdir):
    # Create a new repository and check that the expected
    # files are there
    repo("create", str(tmpdir), "mockrepo")
    assert os.path.exists(os.path.join(str(tmpdir), "repo.yaml"))
    assert os.path.exists(os.path.join(str(tmpdir), "applications"))

    # Add the new repository and check it appears in the list output
    repo("add", "-t", "applications", "--scope=site", str(tmpdir))
    output = repo("list", "--scope=site", output=str)
    assert "mockrepo" in output

    # Then remove it and check it's not there
    repo("remove", "--scope=site", str(tmpdir))
    output = repo("list", "--scope=site", output=str)
    assert "mockrepo" not in output


@pytest.mark.parametrize("subdir", ["applications", "", "foo"])
def test_create_add_list_remove_flags(mutable_config, tmpdir, subdir):
    # Create a new repository and check that the expected
    # files are there
    repo("create", str(tmpdir), "mockrepo", "-d", subdir)
    assert os.path.exists(os.path.join(str(tmpdir), "repo.yaml"))
    assert os.path.exists(os.path.join(str(tmpdir), subdir))

    # Add the new repository and check it appears in the list output
    repo("add", "-t", "applications", "--scope=site", str(tmpdir))
    output = repo("list", "--scope=site", output=str)
    assert "mockrepo" in output

    # Then remove it and check it's not there
    repo("remove", "--scope=site", str(tmpdir))
    output = repo("list", "--scope=site", output=str)
    assert "mockrepo" not in output


def test_add_behavior(mutable_config, tmpdir):
    # Create an app-only repo
    repo("create", str(tmpdir), "mockrepo", "-t", "applications")
    assert os.path.exists(os.path.join(str(tmpdir), "application_repo.yaml"))
    assert os.path.exists(os.path.join(str(tmpdir), "applications"))

    # Complains when specified repo type is not found
    with pytest.raises(
        BadRepoError, match="Failed to find valid repo with type ObjectTypes.modifiers"
    ):
        repo("add", "-t", "modifiers", "--scope=site", str(tmpdir))
    output = repo("list", "--scope=site", output=str)
    assert "mockrepo" not in output

    # Do not complain when type is not specified
    repo("add", "--scope=site", str(tmpdir))
    output = repo("list", "--scope=site", output=str)
    assert "mockrepo" in output

    # Complains if the given path contains no valid repo for all object types
    os.rmdir(os.path.join(tmpdir, "applications"))
    with pytest.raises(BadRepoError, match="not a valid repo for any object types"):
        repo("add", "--scope=site", str(tmpdir))

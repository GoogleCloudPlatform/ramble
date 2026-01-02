# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
import os
import shutil

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
    shutil.rmtree(os.path.join(tmpdir, "applications"))
    with pytest.raises(BadRepoError, match="not a valid repo for any object types"):
        repo("add", "--scope=site", str(tmpdir))


def test_remove_from_any_scope(mutable_config, tmpdir):
    """Tests that 'repo rm' without a scope removes from the correct scope."""
    repo_path = str(tmpdir.join("test_repo"))
    repo_name = "test_repo_namespace"

    # Create a new repository
    repo("create", repo_path, repo_name)

    # Add the new repository to the 'site' scope
    repo("add", "-t", "applications", "--scope=site", repo_path)

    apps_repos_in_site = mutable_config.get("repos", scope="site")
    assert repo_path in apps_repos_in_site, "Repo should be in site config after add."

    # Check that it's in the list (merged scopes)
    output = repo("list", output=str)
    assert repo_name in output
    print(output)

    # Then remove it without specifying a scope
    repo("remove", "--scope=site", repo_path)

    # Check it's not in the site scope list anymore
    output = repo("list", "--scope=site", output=str)
    assert repo_name not in output
    print(output)

    apps_repos_in_site_after_remove = mutable_config.get("repos", scope="site")
    assert (
        repo_path not in apps_repos_in_site_after_remove
    ), "Repo should be removed from site config."

# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.repository


@pytest.fixture(params=["applications", "", "foo"])
def extra_repo(tmpdir_factory, request):
    repo_namespace = "extra_test_repo"
    repo_dir = tmpdir_factory.mktemp(repo_namespace)
    repo_dir.ensure(request.param, dir=True)

    with open(str(repo_dir.join("repo.yaml")), "w", encoding="utf-8") as f:
        f.write("""
repo:
  namespace: extra_test_repo
""")
        if request.param != "applications":
            f.write(f"  subdirectory: '{request.param}'")
    return (
        ramble.repository.Repo(
            str(repo_dir), object_type=ramble.repository.ObjectTypes.applications
        ),
        request.param,
    )


def test_repo_getapp(mutable_mock_apps_repo):
    mutable_mock_apps_repo.get("basic")
    mutable_mock_apps_repo.get("builtin.mock.basic")


def test_repo_multi_getapp(mutable_mock_apps_repo, extra_repo):
    mutable_mock_apps_repo.put_first(extra_repo[0])
    mutable_mock_apps_repo.get("basic")
    mutable_mock_apps_repo.get("builtin.mock.basic")


def test_repo_multi_getappclass(mutable_mock_apps_repo, extra_repo):
    mutable_mock_apps_repo.put_first(extra_repo[0])
    mutable_mock_apps_repo.get_obj_class("basic")
    mutable_mock_apps_repo.get_obj_class("builtin.mock.basic")


def test_repo_app_with_unknown_namespace(mutable_mock_apps_repo):
    with pytest.raises(ramble.repository.UnknownNamespaceError):
        mutable_mock_apps_repo.get("unknown.a")


def test_repo_unknown_app(mutable_mock_apps_repo):
    with pytest.raises(ramble.repository.UnknownObjectError):
        mutable_mock_apps_repo.get("builtin.mock.nonexistentapplication")


@pytest.mark.parametrize(
    "obj_name,obj_type,expected",
    [
        (
            "openfoam-org",
            ramble.repository.ObjectTypes.applications,
            [
                ("applications", "openfoam-org/application.py", "builtin"),
                ("base_applications", "openfoam/base_application.py", "builtin"),
            ],
        ),
        (
            "lscpu",
            ramble.repository.ObjectTypes.modifiers,
            [
                ("modifiers", "lscpu/modifier.py", "builtin"),
            ],
        ),
        (
            "spack",
            ramble.repository.ObjectTypes.package_managers,
            [
                ("package_managers", "spack/package_manager.py", "builtin"),
                ("package_managers", "spack-lightweight/package_manager.py", "builtin"),
            ],
        ),
    ],
)
def test_list_object_files(
    obj_name,
    obj_type,
    expected,
    mutable_apps_repo_path,
    mutable_mods_repo_path,
    mutable_pkg_mans_repo_path,
):
    if obj_type == ramble.repository.ObjectTypes.applications:
        repo = mutable_apps_repo_path
    elif obj_type == ramble.repository.ObjectTypes.modifiers:
        repo = mutable_mods_repo_path
    else:
        repo = mutable_pkg_mans_repo_path
    obj_inst = repo.get(obj_name)
    actual = ramble.repository.list_object_files(obj_inst, obj_type)
    assert len(expected) == len(actual)
    for i in range(len(expected)):
        assert len(expected[i]) == len(actual[i])
        assert expected[i][0] == actual[i][0]
        assert actual[i][1].endswith(expected[i][1])
        assert expected[i][2] == actual[i][2]

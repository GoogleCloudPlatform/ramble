# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.repository
import ramble.paths


@pytest.fixture(params=["applications", "", "foo"])
def extra_repo(tmpdir_factory, request):
    repo_namespace = "extra_test_repo"
    repo_dir = tmpdir_factory.mktemp(repo_namespace)
    repo_dir.ensure(request.param, dir=True)

    with open(str(repo_dir.join("repo.yaml")), "w") as f:
        f.write(
            """
repo:
  namespace: extra_test_repo
"""
        )
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
                ("applications", "openfoam-org/application.py"),
                ("base_applications", "openfoam/base_application.py"),
            ],
        ),
        (
            "lscpu",
            ramble.repository.ObjectTypes.modifiers,
            [
                ("modifiers", "lscpu/modifier.py"),
            ],
        ),
        (
            "spack",
            ramble.repository.ObjectTypes.package_managers,
            [
                ("package_managers", "spack/package_manager.py"),
                ("package_managers", "spack-lightweight/package_manager.py"),
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
        assert expected[i][0] == actual[i][0]
        assert actual[i][1].endswith(expected[i][1])


#
#
# def test_repo_anonymous_app(mutable_mock_apps_repo):
#     with pytest.raises(ramble.repository.UnknownObjectError):
#         mutable_mock_apps_repo.get('+variant')
#
#
# @pytest.mark.maybeslow
# def test_repo_last_mtime():
#     latest_mtime = max(os.path.getmtime(p.module.__file__)
#                        for p in ramble.repository.path.all_applications())
#     assert ramble.repository.path.last_mtime() == latest_mtime
#
#
# def test_repo_invisibles(mutable_mock_apps_repo, extra_repo):
#     with open(os.path.join(extra_repo.root, 'applications', '.invisible'),
#                            'w'):
#         pass
#     extra_repo.all_application_names()

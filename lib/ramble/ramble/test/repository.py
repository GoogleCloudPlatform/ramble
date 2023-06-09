# Copyright 2022-2023 Google LLC
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
    repo_namespace = 'extra_test_repo'
    repo_dir = tmpdir_factory.mktemp(repo_namespace)
    repo_dir.ensure(request.param, dir=True)

    with open(str(repo_dir.join('repo.yaml')), 'w') as f:
        f.write("""
repo:
  namespace: extra_test_repo
""")
        if request.param != "applications":
            f.write(f"  subdirectory: '{request.param}'")
    return (ramble.repository.Repo(str(repo_dir),
            object_type=ramble.repository.ObjectTypes.applications),
            request.param)


def test_repo_getapp(mutable_mock_apps_repo):
    mutable_mock_apps_repo.get('basic')
    mutable_mock_apps_repo.get('builtin.mock.basic')


def test_repo_multi_getapp(mutable_mock_apps_repo, extra_repo):
    mutable_mock_apps_repo.put_first(extra_repo[0])
    mutable_mock_apps_repo.get('basic')
    mutable_mock_apps_repo.get('builtin.mock.basic')


def test_repo_multi_getappclass(mutable_mock_apps_repo, extra_repo):
    mutable_mock_apps_repo.put_first(extra_repo[0])
    mutable_mock_apps_repo.get_obj_class('basic')
    mutable_mock_apps_repo.get_obj_class('builtin.mock.basic')


def test_repo_app_with_unknown_namespace(mutable_mock_apps_repo):
    with pytest.raises(ramble.repository.UnknownNamespaceError):
        mutable_mock_apps_repo.get('unknown.a')


def test_repo_unknown_app(mutable_mock_apps_repo):
    with pytest.raises(ramble.repository.UnknownObjectError):
        mutable_mock_apps_repo.get('builtin.mock.nonexistentapplication')
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

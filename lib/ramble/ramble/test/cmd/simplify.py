# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import sys
import pytest

from ramble.main import RambleCommand
import ramble.repository
import ramble.error

pytestmark = pytest.mark.usefixtures("config")

simplify_cmd = RambleCommand("simplify")


def test_simplify_runs():
    with pytest.raises(SystemExit):
        simplify_cmd("-h")


def test_simplify_applications(mock_applications):
    out = simplify_cmd("-t", "applications", "basic")
    assert "=== Application: basic ===" in out
    assert "Unused Variables: [" in out
    assert "my_var" in out
    assert "my_base_var" in out


def test_simplify_diff_and_apply(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testns\n")

    app_dir = os.path.join(repo_path, "applications", "testapp")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    original_code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Testapp(ExecutableApplication):
    name = "testapp"
    executable('foo', 'bar', use_mpi=False)
    workload('test_wl', executable='foo')
    workload_variable('my_var', default='1.0', workload='test_wl')
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(original_code)

    # Need to clean the cached instance for applications in paths mapping
    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    # Overlay the test repo on top of applications repositories
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        # 1. Test running simplify without flags (shows unused variables)
        out = simplify_cmd("-t", "applications", "testapp")
        assert "Unused Variables: ['my_var']" in out

        # 2. Test running simplify with --diff flag
        out_diff = simplify_cmd("-t", "applications", "-d", "testapp")
        assert "Proposed Changes:" in out_diff
        assert "-    workload_variable('my_var', default='1.0', workload='test_wl')" in out_diff

        # Verify file is still unmodified
        with open(app_file, "r", encoding="utf-8") as f:
            assert "workload_variable('my_var'" in f.read()

        # 3. Test running simplify with --apply flag
        out_apply = simplify_cmd("-t", "applications", "-a", "testapp")
        assert "Successfully simplified" in out_apply

        # Verify file is now simplified
        with open(app_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "workload_variable('my_var'" not in content
            assert 'name = "testapp"' in content

    # Clean sys.modules cache and recreate repo to force reloading from disk
    sys_module_name = "ramble.app.testns.testapp"
    sys.modules.pop(sys_module_name, None)
    parent = sys.modules.get("ramble.app.testns")
    if parent and "testapp" in parent.__dict__:
        del parent.__dict__["testapp"]

    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo_new = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo_new, object_type=obj_type):
        # 4. Test running simplify again, should find 0 unused elements
        out_clean = simplify_cmd("-t", "applications", "testapp")
        assert "Found 0 unused variables" in out_clean


def test_simplify_compilers_and_broken_refs(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo2"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testns2\n")

    app_dir = os.path.join(repo_path, "applications", "testapp2")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    original_code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Testapp2(ExecutableApplication):
    name = "testapp2"
    define_compiler('gcc14', pkg_spec='gcc@14.1.0')
    define_compiler('clang15', pkg_spec='llvm@15.0.0')

    software_spec('my_pkg', pkg_spec='zlib@1.2.11', compiler='gcc14')

    executable('foo', 'bar {var1}', use_mpi=False)
    workload('test_wl', executable='foo')

    workload_variable('var1', default='1.0', workload='test_wl')
    workload_variable('var2', default='2.0', workload='nonexistent_wl')
    workload_group('group1', workloads=['nonexistent_wl2'])
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(original_code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        out = simplify_cmd("-t", "applications", "testapp2")
        # Assert no unused variables (since var1 is used in 'bar {var1}')
        assert "Unused Variables" not in out or "var1" not in out
        # Assert unused compilers detected
        assert "Unused Compilers: ['clang15']" in out
        # Assert broken variables detected
        assert "Variables with Broken Workload/Group Refs: ['var2']" in out
        # Assert broken workload groups detected
        assert "Workload Groups with Broken Workload Refs: ['group1 -> nonexistent_wl2']" in out

        # Test applying simplifications
        out_apply = simplify_cmd("-t", "applications", "-a", "testapp2")
        assert "Successfully simplified" in out_apply

        # Verify clang15 and var2 were deleted from file
        with open(app_file, "r", encoding="utf-8") as f:
            content = f.read()
            assert "define_compiler('clang15'" not in content
            assert "workload_variable('var2'" not in content
            # gcc14 and var1 should be untouched (since var1 is used and define_compiler('gcc14') is used!)
            assert "define_compiler('gcc14'" in content
            assert "workload_variable('var1'" in content
            # workload group is untouched (not auto-deleted)
            assert "workload_group('group1'" in content


def test_simplify_broken_template_references(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo3"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testns3\n")

    app_dir = os.path.join(repo_path, "applications", "testapp3")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    original_code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Testapp3(ExecutableApplication):
    name = "testapp3"
    required_package('wrf')
    software_spec('orca-{application::orca::version}', pkg_spec='orca@5.0.4')
    input_file('my_input', url='https://host.com/file.tar.gz', description='my input file')
    executable('foo', 'bar {my_var} {my_input} {nonexistent_var_typo} {wrf_path} {orca_path}', use_mpi=False)
    workload('test_wl', executable='foo')
    workload_variable('my_var', default='1.0', workload='test_wl')
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(original_code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        out = simplify_cmd("-t", "applications", "testapp3")
        # Assert broken template reference is detected
        assert "Broken Variable References in Templates: ['nonexistent_var_typo']" in out
        # Assert valid variables, inputs, and spec paths are NOT reported as broken references
        assert "my_var" not in out or "Broken Variable References" not in out.split("my_var")[0]
        assert "my_input" not in out
        assert "wrf_path" not in out
        assert "orca_path" not in out


def test_simplify_repo_filter(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo4"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testrepo\n")

    app_dir = os.path.join(repo_path, "applications", "testapp4")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    original_code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Testapp4(ExecutableApplication):
    name = "testapp4"
    executable('foo', 'bar', use_mpi=False)
    workload('test_wl', executable='foo')
    workload_variable('my_var', default='1.0', workload='test_wl')
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(original_code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        # Scan with repository filter set to 'testrepo'
        out = simplify_cmd("-t", "applications", "-r", "testrepo")
        assert "=== Application: testapp4 ===" in out
        assert "Unused Variables: ['my_var']" in out

        # Scan with nonexistent repo namespace should return failure
        with pytest.raises(ramble.error.RambleCommandError):
            simplify_cmd("-t", "applications", "-r", "nonexistent")


def test_simplify_wildcard_workloads(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo5"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testns5\n")

    app_dir = os.path.join(repo_path, "applications", "testapp5")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    original_code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Testapp5(ExecutableApplication):
    name = "testapp5"
    executable('foo', 'bar {dict_delim} {nonexistent_var}', use_mpi=False)
    workload('motorbike_20m', executable='foo')
    workload_variable('dict_delim', default='.', workloads=['motorbike*'])
    workload_variable('nonexistent_var', default='.', workloads=['other*'])
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(original_code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        out = simplify_cmd("-t", "applications", "testapp5")
        # Assert nonexistent_var is detected as broken because 'other*' matches zero workloads
        assert "Variables with Broken Workload/Group Refs: ['nonexistent_var']" in out
        # dict_delim should NOT be detected as broken because 'motorbike*' matches 'motorbike_20m'
        assert "dict_delim" not in out or "Variables with Broken Workload" not in out.split("dict_delim")[0]

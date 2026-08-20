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

import ramble.error
import ramble.repository
from ramble.main import RambleCommand

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
        with open(app_file, encoding="utf-8") as f:
            assert "workload_variable('my_var'" in f.read()

        # 3. Test running simplify with --apply flag
        out_apply = simplify_cmd("-t", "applications", "-a", "testapp")
        assert "Successfully simplified" in out_apply

        # Verify file is now simplified
        with open(app_file, encoding="utf-8") as f:
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
        with open(app_file, encoding="utf-8") as f:
            content = f.read()
            assert "define_compiler('clang15'" not in content
            assert "workload_variable('var2'" not in content
            # gcc14 and var1 should be untouched (since var1 is used and
            # define_compiler('gcc14') is used!)
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
    executable(
        'foo',
        'bar {my_var} {my_input} {nonexistent_var_typo} {wrf_path} '
        '{orca_path} {my_var - 1} {my_var -1} {my_var-1} '
        '{min(my_var, 2)} {sqrt(my_var)} \\\\{escaped\\\\} '
        '{my_var ? application::my_var : my_input}',
        use_mpi=False,
    )
    workload('test_wl', executable='foo')
    workload_variable('my_var', default='1.0', workload='test_wl')
    workload_variable('my_formatted_var', default='{{{my_var}/2}:0.0f}', workload='test_wl')
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
        # Assert format specifier parts are NOT extracted/reported as broken references
        assert ":0" not in out
        assert "0f" not in out
        # Assert valid variables, inputs, and spec paths are NOT reported as broken references
        assert "my_var" not in out or "Broken Variable References" not in out.split("my_var")[0]
        assert "my_input" not in out
        assert "wrf_path" not in out
        assert "orca_path" not in out


def test_simplify_environment_variable_references(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo_env_vars"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testns_env_vars\n")

    app_dir = os.path.join(repo_path, "applications", "testapp_env")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    original_code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class TestappEnv(ExecutableApplication):
    name = "testapp_env"
    executable('foo', 'bar', use_mpi=False)
    workload('test_wl', executable='foo')
    workload_variable(
        'var_in_env_val',
        environment_variable_name='MY_ENV_VAR',
        default='1.0',
        workload='test_wl'
    )
    workload_variable(
        'var_in_env_name',
        environment_variable_name='MY_ENV_{var_in_env_name_ref}',
        default='2.0',
        workload='test_wl'
    )
    workload_variable(
        'var_in_env_name_ref',
        default='suffix',
        workload='test_wl'
    )
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
        out = simplify_cmd("-t", "applications", "testapp_env")
        # Assert none of the variables are reported as unused
        assert "Unused Variables" not in out
        assert "Found 0 unused variables" in out


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
        assert (
            "dict_delim" not in out
            or "Variables with Broken Workload" not in out.split("dict_delim")[0]
        )


def test_get_node_end_lineno_fallback():
    import ast

    from ramble.cmd.simplify import get_node_end_lineno

    content = """executable(
    'foo',
    'bar',
    use_mpi=False
)
"""
    tree = ast.parse(content)
    node = tree.body[0]

    # Force fallback by deleting end_lineno if it exists
    if hasattr(node, "end_lineno"):
        del node.end_lineno

    file_lines = content.splitlines()
    end_line = get_node_end_lineno(node, file_lines)
    assert end_line == 5


def test_extract_referenced_names():
    from ramble.cmd.simplify import extract_referenced_names

    assert extract_referenced_names("foo {application::orca::version}") == {"version"}
    assert extract_referenced_names("foo {simple_var}") == {"simple_var"}
    assert extract_referenced_names(123) == set()
    assert extract_referenced_names(
        "foo {inputs-u-of-alberta}",
        defined_inputs={"inputs-u-of-alberta"},
        all_defined_variables=set(),
    ) == {"inputs-u-of-alberta"}
    assert extract_referenced_names("notes: {u of alberta inputs} awk '{print $NF}'") == set()
    assert (
        extract_referenced_names(
            "echo ${SERVER_NUMBER} ${CLIENT_NUMBER}",
            all_defined_variables=set(),
        )
        == set()
    )
    assert extract_referenced_names(
        "echo ${my_var}",
        all_defined_variables={"my_var"},
    ) == {"my_var"}
    assert extract_referenced_names(
        "cat {hostfile}",
        all_defined_variables=set(),
    ) == {"hostfile"}
    assert extract_referenced_names(
        "run {altair-radioss}/bin/optistruct",
        defined_software_specs={"altair-radioss"},
        all_defined_variables=set(),
    ) == {"altair-radioss"}


def test_find_template_file_direct(tmpdir):
    from ramble.cmd.simplify import find_template_file

    class DummyClass:
        __module__ = "ramble.app.dummy"

    # Create dummy module in sys.modules
    import types

    dummy_module = types.ModuleType("ramble.app.dummy")
    dummy_module.__file__ = os.path.join(str(tmpdir), "application.py")
    sys.modules["ramble.app.dummy"] = dummy_module

    # Test absolute path
    abs_path = os.path.join(str(tmpdir), "absolute_template.in")
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write("test")
    assert find_template_file(DummyClass, abs_path) == abs_path
    assert find_template_file(DummyClass, "/nonexistent/abs/path") is None

    # Test relative path
    rel_path = "relative_template.in"
    full_rel_path = os.path.join(str(tmpdir), rel_path)
    with open(full_rel_path, "w", encoding="utf-8") as f:
        f.write("test")
    assert find_template_file(DummyClass, rel_path) == full_rel_path
    assert find_template_file(DummyClass, "nonexistent_rel.in") is None

    # Clean up sys.modules
    sys.modules.pop("ramble.app.dummy", None)


def test_get_arg_value_direct():
    import ast

    from ramble.cmd.simplify import get_arg_value

    tree = ast.parse("foo(bar)")
    stmt = tree.body[0]
    assert isinstance(stmt, ast.Expr)
    call = stmt.value
    assert isinstance(call, ast.Call)
    # call.args[0] is ast.Name (bar)
    assert get_arg_value(call.args[0]) is None


def test_get_node_end_lineno_fallback_detailed():
    import ast

    from ramble.cmd.simplify import get_node_end_lineno

    # 1. Comment outside strings
    content1 = """executable(
        'foo', # this is a comment
        'bar'
    )"""
    tree1 = ast.parse(content1)
    node1 = tree1.body[0]
    if hasattr(node1, "end_lineno"):
        del node1.end_lineno
    assert get_node_end_lineno(node1, content1.splitlines()) == 4

    # 2. Escaped quotes and different quote types
    content2 = """executable('foo', "bar \\' baz", 'qux')"""
    tree2 = ast.parse(content2)
    node2 = tree2.body[0]
    if hasattr(node2, "end_lineno"):
        del node2.end_lineno
    assert get_node_end_lineno(node2, content2.splitlines()) == 1

    # 3. Triple quotes
    content3 = """executable(
        'foo',
        \"""triple
        double
        quote\""",
        '''triple
        single
        quote''',
        'bar'
    )"""
    tree3 = ast.parse(content3)
    node3 = tree3.body[0]
    if hasattr(node3, "end_lineno"):
        del node3.end_lineno
    assert get_node_end_lineno(node3, content3.splitlines()) == 10

    # 4. No parens first line fallback
    content4 = "x = 1"
    tree4 = ast.parse(content4)
    node4 = tree4.body[0]
    if hasattr(node4, "end_lineno"):
        del node4.end_lineno
    assert get_node_end_lineno(node4, content4.splitlines()) == 1


def test_locate_directive_lines_errors(tmpdir, monkeypatch):
    import ramble.util.logger
    from ramble.cmd.simplify import locate_directive_lines

    # Mock logger.warn to verify it was called
    warn_calls = []
    monkeypatch.setattr(ramble.util.logger.logger, "warn", lambda msg: warn_calls.append(msg))

    # Test file that does not exist (OSError)
    res = locate_directive_lines("/nonexistent/file/path", set(), set(), set(), set(), [])
    assert res == []
    assert any("Could not parse" in c for c in warn_calls)

    # Test file with syntax error
    bad_file = os.path.join(str(tmpdir), "bad_syntax.py")
    with open(bad_file, "w", encoding="utf-8") as f:
        f.write("class BadClass:\n   def foo(:\n")

    warn_calls.clear()
    res = locate_directive_lines(bad_file, set(), set(), set(), set(), [])
    assert res == []
    assert any("Could not parse" in c for c in warn_calls)


def test_locate_directive_lines_no_class(tmpdir):
    from ramble.cmd.simplify import locate_directive_lines

    empty_file = os.path.join(str(tmpdir), "empty.py")
    with open(empty_file, "w", encoding="utf-8") as f:
        f.write("# just comment, no class\n")

    assert locate_directive_lines(empty_file, set(), set(), set(), set(), []) == []


def test_simplify_comprehensive(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("ramble_repo_comprehensive"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testcomp\n")

    app_dir = os.path.join(repo_path, "applications", "compapp")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    # Write registered template
    tpl_file = os.path.join(app_dir, "my_template.in")
    with open(tpl_file, "w", encoding="utf-8") as f:
        f.write(
            "template referencing {var1} and {broken_tpl_ref} and {application::orca::version}\n"
        )

    code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Compapp(ExecutableApplication):
    name = "compapp"

    # Compilers
    define_compiler('gcc14', pkg_spec='gcc@14')
    define_compiler('unused_compiler', pkg_spec='gcc@13')

    # Software specs
    software_spec('orca-{version}', pkg_spec='orca@5.0.4')
    software_spec('my_pkg', pkg_spec='zlib', compiler='gcc14')

    # Inputs
    input_file('my_input', url='https://host.com/file-{var1}.tar.gz', description='my input')
    input_file('unused_input', url='https://host.com/unused-{broken_input_ref}.tar.gz', description='unused input')

    # Executables
    executable('foo', 'bar {var1} {my_input} {application_version}', use_mpi=False)
    executable('unused_exec', 'baz', use_mpi=False)

    # Workloads
    workload('test_wl', executable='foo')

    # Workload groups
    workload_group('group1', workloads=['test_wl'])

    # Variables
    workload_variable('var1', default='1.0', workload='test_wl')
    workload_variable('var2', default='{var1}', workload='nonexistent_wl')
    workload_variable('version', default='5.0', workload='test_wl')

    # Non-constant variable definition
    local_name = 'some_local_name'
    workload_variable(local_name, default='2.0', workload='test_wl')

    # Figure of Merit
    figure_of_merit('my_fom', fom_regex=r'Result: (?P<fom_val>\\d+)', group_name='fom_val', log_file='{var1}.log')
    figure_of_merit('fom_with_refs', fom_regex=r'Result: (?P<fom_val>\\d+)', group_name='fom_val', log_file='{fom_val} {broken_fom_ref}.log')

    # Success Criteria
    success_criteria('my_crit', 'fom_comparison', file='{var1}.log', formula='{var1} > 0')
    success_criteria('fom_value_crit', 'fom_comparison', file='{var1}.log', fom_name='my_fom', formula='{value} > 0')
    success_criteria('broken_crit', 'fom_comparison', file='{broken_crit_ref}.log', formula='{broken_formula_ref}')

    # Templates
    register_template('tpl1', src_path='my_template.in', dest_path='my_template.out')

    # Fallback check for python reference
    def some_method(self):
        x = 'referenced_in_python_code'

    workload_variable('referenced_in_python_code', default='val', workload='test_wl')
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        # 1. Run simplify without flags, verify all outputs
        out = simplify_cmd("-t", "applications", "compapp")

        # Verify unused compilers, inputs, executables
        assert "Unused Compilers: ['unused_compiler']" in out
        assert "Unused Inputs: ['unused_input']" in out
        assert "Unused Executables: ['unused_exec']" in out
        assert "Unused Variables" not in out or "referenced_in_python_code" not in out

        # Verify variables with broken workload group references
        assert "Variables with Broken Workload/Group Refs: ['var2']" in out

        # Verify broken variable references in templates
        assert "broken_crit_ref" in out
        assert "broken_fom_ref" in out
        assert "broken_formula_ref" in out
        assert "broken_tpl_ref" in out
        assert "broken_input_ref" in out

        # 2. Run simplify --apply, verify file changes
        out_apply = simplify_cmd("-t", "applications", "-a", "compapp")
        assert "Successfully simplified" in out_apply

        with open(app_file, encoding="utf-8") as f:
            content = f.read()
            # Verify unused/broken entities are deleted
            assert "define_compiler('unused_compiler'" not in content
            assert "input_file('unused_input'" not in content
            assert "executable('unused_exec'" not in content
            assert "workload_variable('var2'" not in content

            # Verify valid entities remain
            assert "define_compiler('gcc14'" in content
            assert "input_file('my_input'" in content
            assert "executable('foo'" in content
            assert "workload_variable('var1'" in content
            assert "workload_variable('referenced_in_python_code'" in content


def test_simplify_modifier(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("ramble_mod_repo"))
    os.makedirs(os.path.join(repo_path, "modifiers"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testmodns\n")

    mod_dir = os.path.join(repo_path, "modifiers", "testmod")
    os.makedirs(mod_dir)
    mod_file = os.path.join(mod_dir, "modifier.py")

    code = """# Copyright 2022-2026 The Ramble Authors
from ramble.modkit import *

class Testmod(BasicModifier):
    name = "testmod"

    # Modifiers use 'variable' instead of 'workload_variable'
    # We define a variable that is unused, and one that is used in a template
    variable('used_var', default='1.0', description='used variable')
    variable('unused_var', default='{broken_mod_ref}', description='unused variable')

    def some_method(self):
        self.used_var
"""
    with open(mod_file, "w", encoding="utf-8") as f:
        f.write(code)

    obj_type = ramble.repository.ObjectTypes.modifiers
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        out = simplify_cmd("-t", "modifiers", "testmod")
        assert "=== Modifier: testmod ===" in out
        assert "Unused Variables: ['unused_var']" in out
        assert "Broken Variable References in Templates: ['broken_mod_ref']" in out

        # Test apply
        out_apply = simplify_cmd("-t", "modifiers", "-a", "testmod")
        assert "Successfully simplified" in out_apply

        with open(mod_file, encoding="utf-8") as f:
            content = f.read()
            assert "variable('unused_var'" not in content
            assert "variable('used_var'" in content


def test_simplify_repo_filter_with_names_and_all_names(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo_names"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: repotests\n")

    app_dir = os.path.join(repo_path, "applications", "app1")
    os.makedirs(app_dir)
    with open(os.path.join(app_dir, "application.py"), "w", encoding="utf-8") as f:
        f.write("""# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *
class App1(ExecutableApplication):
    name = "app1"
""")

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        # Scan with repository filter and specific names (covers line 720)
        out1 = simplify_cmd("-t", "applications", "-r", "repotests", "app1")
        assert "Found 0 unused variables" in out1

        # Scan without specifying any names (covers line 730)
        out2 = simplify_cmd("-t", "applications")
        assert "Summary:" in out2


def test_simplify_analysis_error(tmpdir, mutable_config, monkeypatch):
    import ramble.cmd.simplify
    import ramble.util.logger

    warn_calls = []
    monkeypatch.setattr(ramble.util.logger.logger, "warn", lambda msg: warn_calls.append(msg))

    def mock_analyze(name, obj_type):
        raise RuntimeError("Simulated analysis error")

    monkeypatch.setattr(ramble.cmd.simplify, "analyze_object", mock_analyze)

    # Let's run simplify on some application. Since it's mocked to
    # raise error, it should log it as warning
    repo_path = str(tmpdir.join("test_repo_err"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: errns\n")

    app_dir = os.path.join(repo_path, "applications", "errapp")
    os.makedirs(app_dir)
    with open(os.path.join(app_dir, "application.py"), "w", encoding="utf-8") as f:
        f.write("""# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *
class Errapp(ExecutableApplication):
    name = "errapp"
""")

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        simplify_cmd("-t", "applications", "errapp")
        assert any("Error analyzing errapp: Simulated analysis error" in c for c in warn_calls)


def test_simplify_open_source_oserror(tmpdir, mutable_config, monkeypatch):
    import builtins

    import ramble.util.logger

    repo_path = str(tmpdir.join("ramble_repo_oserror"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: oserrns\n")

    app_dir = os.path.join(repo_path, "applications", "oserrapp")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")
    with open(app_file, "w", encoding="utf-8") as f:
        f.write("""# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *
class Oserrapp(ExecutableApplication):
    name = "oserrapp"
""")

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)

    original_open = builtins.open

    warn_calls = []
    monkeypatch.setattr(ramble.util.logger.logger, "warn", lambda msg: warn_calls.append(msg))

    def mock_open(file, *args, **kwargs):
        if isinstance(file, (str, bytes, os.PathLike)) and os.path.realpath(
            file
        ) == os.path.realpath(app_file):
            raise OSError("Simulated read failure")
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", mock_open)

    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        simplify_cmd("-t", "applications", "oserrapp")
        assert any("Could not read source file" in c for c in warn_calls)


def test_simplify_inheritance_attribute_move(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo_inherit"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testns_inherit\n")

    parent_dir = os.path.join(repo_path, "applications", "parent")
    os.makedirs(parent_dir)
    parent_file = os.path.join(parent_dir, "application.py")
    parent_code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Parent(ExecutableApplication):
    name = "parent"
    executable('foo', 'bar', use_mpi=False)
    workload('test_wl', executable='foo')
    workload_variable('parent_var', default='1.0', workload='test_wl')
"""
    with open(parent_file, "w", encoding="utf-8") as f:
        f.write(parent_code)

    child_a_dir = os.path.join(repo_path, "applications", "child_a")
    os.makedirs(child_a_dir)
    child_a_file = os.path.join(child_a_dir, "application.py")
    child_a_code = """# Copyright 2022-2026 The Ramble Authors
from ramble.app.testns_inherit.parent import Parent as ParentBase
from ramble.appkit import *

class ChildA(ParentBase):
    name = "child_a"
    executable('foo_a', 'bar {parent_var}', use_mpi=False)
    workload('test_wl_a', executable='foo_a')
"""
    with open(child_a_file, "w", encoding="utf-8") as f:
        f.write(child_a_code)

    child_b_dir = os.path.join(repo_path, "applications", "child_b")
    os.makedirs(child_b_dir)
    child_b_file = os.path.join(child_b_dir, "application.py")
    child_b_code = """# Copyright 2022-2026 The Ramble Authors
from ramble.app.testns_inherit.parent import Parent as ParentBase
from ramble.appkit import *

class ChildB(ParentBase):
    name = "child_b"
    executable('foo_b', 'bar', use_mpi=False)
    workload('test_wl_b', executable='foo_b')
"""
    with open(child_b_file, "w", encoding="utf-8") as f:
        f.write(child_b_code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    # Clean sys.modules cache for the classes we are going to import/define
    for m in [
        "ramble.app.testns_inherit",
        "ramble.app.testns_inherit.parent",
        "ramble.app.testns_inherit.child_a",
        "ramble.app.testns_inherit.child_b",
    ]:
        sys.modules.pop(m, None)

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        out = simplify_cmd("-t", "applications")
        assert "Move to Subclasses:" in out
        assert "parent_var -> ['child_a']" in out
        assert "Move from Parents:" in out

        # Now apply the simplification
        out_apply = simplify_cmd("-t", "applications", "-a")
        assert "Successfully simplified" in out_apply

    # Verify parent has it removed
    with open(parent_file, encoding="utf-8") as f:
        parent_content = f.read()
        assert "parent_var" not in parent_content

    # Verify child_a has it added
    with open(child_a_file, encoding="utf-8") as f:
        child_a_content = f.read()
        assert "workload_variable('parent_var'" in child_a_content

    # Verify child_b is unchanged
    with open(child_b_file, encoding="utf-8") as f:
        child_b_content = f.read()
        assert "parent_var" not in child_b_content

    # Re-verify by reloading everything and running simplify again (should be clean)
    sys.modules.pop("ramble.app.testns_inherit.parent", None)
    sys.modules.pop("ramble.app.testns_inherit.child_a", None)
    sys.modules.pop("ramble.app.testns_inherit.child_b", None)
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo_new = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo_new, object_type=obj_type):
        out_clean = simplify_cmd("-t", "applications")
        assert "Move to Subclasses" not in out_clean
        assert "Move from Parents" not in out_clean
        assert "Found 0 unused variables" in out_clean


def test_simplify_when_block_unused_variable(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("ramble_repo_when_var"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testwhenvar\n")

    app_dir = os.path.join(repo_path, "applications", "whenapp")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Whenapp(ExecutableApplication):
    name = "whenapp"

    with when("application_version@4.0:"):
        executable('foo', 'echo {used_var}', use_mpi=False)
        workload('test_wl', executable='foo')
        workload_variable('used_var', default='val', workload='test_wl')
        workload_variable('unused_when_var', default='junk', workload='test_wl')
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        out = simplify_cmd("-t", "applications", "whenapp")
        assert "Unused Variables: ['unused_when_var']" in out
        assert "used_var" not in out

        out_apply = simplify_cmd("-t", "applications", "-a", "whenapp")
        assert "Successfully simplified" in out_apply

    with open(app_file, encoding="utf-8") as f:
        content = f.read()
        assert "unused_when_var" not in content
        assert "used_var" in content


def test_simplify_substring_in_other_directive_args(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("ramble_repo_substring"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testsubstring\n")

    app_dir = os.path.join(repo_path, "applications", "substringapp")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    code = """# Copyright 2022-2026 The Ramble Authors
import os
from ramble.appkit import *

class Substringapp(ExecutableApplication):
    name = "substringapp"

    input_file(
        "nothing",
        url=f"{os.getcwd()}/foo.tgz",
        description="junk input with foo in description",
        expand=False,
    )
    workload_variable(
        "foo",
        default="bar",
        description="Blah",
        workload="test_wl",
    )
    workload(
        "test_wl",
        executables=["setup"],
    )
    executable("setup", "echo", use_mpi=False)
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        out = simplify_cmd("-t", "applications", "substringapp")
        assert "Unused Variables: ['foo']" in out
        assert "Unused Inputs: ['nothing']" in out

        out_apply = simplify_cmd("-t", "applications", "-a", "substringapp")
        assert "Successfully simplified" in out_apply

    with open(app_file, encoding="utf-8") as f:
        content = f.read()
        assert "workload_variable(" not in content
        assert "input_file(" not in content
        assert "workload(" in content
        assert "executable(" in content


def test_simplify_hyphenated_entities_and_syntax_error_braces(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo_hyphen"))
    os.makedirs(os.path.join(repo_path, "applications"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testhyphen\n")

    app_dir = os.path.join(repo_path, "applications", "hyphenapp")
    os.makedirs(app_dir)
    app_file = os.path.join(app_dir, "application.py")

    code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Hyphenapp(ExecutableApplication):
    name = "hyphenapp"

    input_file(
        "inputs-u-of-alberta",
        url="https://host.com/vasp-inputs.tgz",
        description="Input file with hyphens",
    )
    workload_variable(
        "num-objects",
        default="1000",
        description="Variable with hyphen",
        workload="test_wl",
    )
    workload_variable(
        "input_dir",
        default="{inputs-u-of-alberta}",
        workload="test_wl",
    )
    executable(
        "foo",
        "mdtest -n {num-objects} {input_dir} # notes: {u of alberta inputs} awk '{print $NF}'",
        use_mpi=False,
    )
    workload("test_wl", executables=["foo"], input="inputs-u-of-alberta")
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        out = simplify_cmd("-t", "applications", "hyphenapp")
        assert "Unused Variables" not in out
        assert "Unused Inputs" not in out
        assert "Broken Variable References in Templates" not in out
        assert "alberta" not in out
        assert "print" not in out
        assert "NF" not in out
        assert "Found 0 unused variables" in out


def test_simplify_excludes_mock_repo_by_default(tmpdir, mutable_config):
    # Create a real repo and a mock repo
    real_repo_path = str(tmpdir.join("real_repo"))
    os.makedirs(os.path.join(real_repo_path, "applications", "real_app"))
    with open(os.path.join(real_repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: realrepo\n")
    with open(
        os.path.join(real_repo_path, "applications", "real_app", "application.py"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write("""# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *
class RealApp(ExecutableApplication):
    name = "real_app"
""")

    mock_repo_path = str(tmpdir.join("mock_repo"))
    os.makedirs(os.path.join(mock_repo_path, "applications", "mock_app"))
    with open(os.path.join(mock_repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: test.mock\n")
    with open(
        os.path.join(mock_repo_path, "applications", "mock_app", "application.py"),
        "w",
        encoding="utf-8",
    ) as f:
        f.write("""# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *
class MockApp(ExecutableApplication):
    name = "mock_app"
    workload_variable('unused_mock_var', default='val', workload='wl')
""")

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    real_repo = ramble.repository.Repo(real_repo_path, object_type=obj_type)
    mock_repo = ramble.repository.Repo(mock_repo_path, object_type=obj_type)

    with ramble.repository.use_repositories(mock_repo, real_repo, object_type=obj_type):
        # 1. Default execution without -r should only check real_repo, excluding mock_app
        out_default = simplify_cmd("-t", "applications")
        assert "mock_app" not in out_default
        assert "unused_mock_var" not in out_default

        # 2. Explicit -r test.mock should check mock_app
        out_explicit = simplify_cmd("-t", "applications", "-r", "test.mock")
        assert "mock_app" in out_explicit
        assert "unused_mock_var" in out_explicit


def test_simplify_bash_vars_and_workflow_variables(tmpdir, mutable_config):
    repo_path = str(tmpdir.join("test_repo_bash"))
    os.makedirs(os.path.join(repo_path, "applications", "bashapp"))
    with open(os.path.join(repo_path, "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: testbash\n")

    app_file = os.path.join(repo_path, "applications", "bashapp", "application.py")
    code = """# Copyright 2022-2026 The Ramble Authors
from ramble.appkit import *

class Bashapp(ExecutableApplication):
    name = "bashapp"

    workload_variable(
        "log_prefix",
        default="run",
        workload="test_wl",
    )
    executable(
        "run_client",
        "cat {hostfile} >> {log_prefix}.s${SERVER_NUMBER}.c${CLIENT_NUMBER}",
        use_mpi=False,
    )
    workload("test_wl", executables=["run_client"])
"""
    with open(app_file, "w", encoding="utf-8") as f:
        f.write(code)

    obj_type = ramble.repository.ObjectTypes.applications
    try:
        ramble.repository.paths[obj_type]._instance = None
    except Exception:
        pass

    test_repo = ramble.repository.Repo(repo_path, object_type=obj_type)
    with ramble.repository.use_repositories(test_repo, object_type=obj_type):
        out = simplify_cmd("-t", "applications", "bashapp")
        assert "Broken Variable References in Templates" not in out
        assert "SERVER_NUMBER" not in out
        assert "CLIENT_NUMBER" not in out
        assert "hostfile" not in out
        assert "Found 0 unused variables" in out

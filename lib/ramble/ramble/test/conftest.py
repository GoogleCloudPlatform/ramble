# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import collections
import os
import os.path
import shutil

import py
import pytest

from llnl.util.filesystem import remove_linked_tree

import ramble.config
import ramble.paths
import ramble.repository

import spack.platforms
import spack.util.spack_yaml as syaml


def _can_access(path, perms):
    return False


# Hooks to add command line options or set other custom behaviors.
# They must be placed here to be found by pytest. See:
#
# https://docs.pytest.org/en/latest/writing_plugins.html
#
def pytest_addoption(parser):
    group = parser.getgroup("Ramble specific command line options")
    group.addoption(
        '--fast', action='store_true', default=False,
        help='runs only "fast" unit tests, instead of the whole suite')


def pytest_collection_modifyitems(config, items):
    if not config.getoption('--fast'):
        # --fast not given, run all the tests
        return

    slow_tests = ['db', 'network', 'maybeslow']
    skip_as_slow = pytest.mark.skip(
        reason='skipped slow test [--fast command line option given]'
    )
    for item in items:
        if any(x in item.keywords for x in slow_tests):
            item.add_marker(skip_as_slow)


#
# These fixtures are applied to all tests
#
@pytest.fixture(scope='function', autouse=True)
def no_chdir():
    """Ensure that no test changes Ramble's working dirctory.

    This prevents Ramble tests (and therefore Ramble commands) from
    changing the working directory and causing other tests to fail
    mysteriously. Tests should use ``working_dir`` or ``py.path``'s
    ``.as_cwd()`` instead of ``os.chdir`` to avoid failing this check.

    We assert that the working directory hasn't changed, unless the
    original wd somehow ceased to exist.

    """
    original_wd = os.getcwd()
    yield
    if os.path.isdir(original_wd):
        assert os.getcwd() == original_wd


def remove_whatever_it_is(path):
    """Type-agnostic remove."""
    if os.path.isfile(path):
        os.remove(path)
    elif os.path.islink(path):
        remove_linked_tree(path)
    else:
        shutil.rmtree(path)


@pytest.fixture
def working_env():
    saved_env = os.environ.copy()
    yield
    # os.environ = saved_env doesn't work
    # it causes module_parsing::test_module_function to fail
    # when it's run after any test using this fixutre
    os.environ.clear()
    os.environ.update(saved_env)


#
# Note on context managers used by fixtures
#
# Because these context managers modify global state, they should really
# ONLY be used persistently (i.e., around yield statements) in
# function-scoped fixtures, OR in autouse session- or module-scoped
# fixtures.
#
# If they're used in regular tests or in module-scoped fixtures that are
# then injected as function arguments, weird things can happen, because
# the original state won't be restored until *after* the fixture is
# destroyed.  This makes sense for an autouse fixture, where you know
# everything in the module/session is going to need the modified
# behavior, but modifying global state for one function in a way that
# won't be restored until after the module or session is done essentially
# leaves garbage behind for other tests.
#
# In general, we should module- or session-scope the *STATE* required for
# these global objects, but we shouldn't module- or session-scope their
# *USE*, or things can get really confusing.
#


#
# Test-specific fixtures
#
@pytest.fixture(scope='session')
def mock_repo_path():
    yield ramble.repository.Repo(ramble.paths.mock_applications_path)


@pytest.fixture(scope='function')
def mock_applications(mock_repo_path, mock_app_install):
    """Use the 'builtin.mock' repository instead of 'builtin'"""
    with ramble.repository.use_repositories(mock_repo_path) as mock_repo:
        yield mock_repo


@pytest.fixture(scope='function')
def mutable_mock_repo(mock_repo_path):
    """Function-scoped mock packages, for tests that need to modify them."""
    mock_repo = ramble.repository.Repo(ramble.paths.mock_applications_path)
    with ramble.repository.use_repositories(mock_repo) as mock_repo_path:
        yield mock_repo_path


@pytest.fixture(scope='session')
def default_config():
    """Isolates the default configuration from the user configs.

    This ensures we can test the real default configuration without having
    tests fail when the user overrides the defaults that we test against."""
    defaults_path = os.path.join(ramble.paths.etc_path, 'ramble', 'defaults')
    with ramble.config.use_configuration(defaults_path) as defaults_config:
        yield defaults_config


@pytest.fixture(scope='session')
def configuration_dir(tmpdir_factory, linux_os):
    """Copies mock configuration files in a temporary directory. Returns the
    directory path.
    """
    tmpdir = tmpdir_factory.mktemp('configurations')

    # <test_path>/data/config has mock config yaml files in it
    # copy these to the site config.
    test_config = py.path.local(ramble.paths.test_path).join('data', 'config')
    test_config.copy(tmpdir.join('site'))

    # Create temporary 'defaults', 'site' and 'user' folders
    tmpdir.ensure('user', dir=True)

    # Slightly modify config.yaml
    solver = os.environ.get('SPACK_TEST_SOLVER', 'original')
    config_yaml = test_config.join('config.yaml')
    modules_root = tmpdir_factory.mktemp('share')
    tcl_root = modules_root.ensure('modules', dir=True)
    lmod_root = modules_root.ensure('lmod', dir=True)
    content = ''.join(config_yaml.read()).format(
        solver, str(tcl_root), str(lmod_root)
    )
    t = tmpdir.join('site', 'config.yaml')
    t.write(content)
    yield tmpdir

    # Once done, cleanup the directory
    shutil.rmtree(str(tmpdir))


@pytest.fixture(scope='session')
def linux_os():
    """Returns a named tuple with attributes 'name' and 'version'
    representing the OS.
    """
    platform = spack.platforms.host()
    name, version = 'debian', '6'
    if platform.name == 'linux':
        current_os = platform.operating_system('default_os')
        name, version = current_os.name, current_os.version
    LinuxOS = collections.namedtuple('LinuxOS', ['name', 'version'])
    return LinuxOS(name=name, version=version)


@pytest.fixture(scope='session')
def mock_configuration_scopes(configuration_dir):
    """Create a persistent Configuration object from the configuration_dir."""
    defaults = ramble.config.InternalConfigScope(
        '_builtin', ramble.config.config_defaults
    )
    test_scopes = [defaults]
    test_scopes += [
        ramble.config.ConfigScope(name, str(configuration_dir.join(name)))
        for name in ['site', 'system', 'user']]
    test_scopes.append(ramble.config.InternalConfigScope('command_line'))

    yield test_scopes


@pytest.fixture(scope='function')
def config(mock_configuration_scopes):
    """This fixture activates/deactivates the mock configuration."""
    with ramble.config.use_configuration(*mock_configuration_scopes) as config:
        yield config


@pytest.fixture(scope='function')
def mutable_config(tmpdir_factory, configuration_dir):
    """Like config, but tests can modify the configuration."""
    mutable_dir = tmpdir_factory.mktemp('mutable_config').join('tmp')
    configuration_dir.copy(mutable_dir)

    scopes = [ramble.config.ConfigScope(name, str(mutable_dir.join(name)))
              for name in ['site', 'system', 'user']]

    with ramble.config.use_configuration(*scopes) as cfg:
        yield cfg


@pytest.fixture(scope='function')
def mutable_empty_config(tmpdir_factory, configuration_dir):
    """Empty configuration that can be modified by the tests."""
    mutable_dir = tmpdir_factory.mktemp('mutable_config').join('tmp')
    scopes = [ramble.config.ConfigScope(name, str(mutable_dir.join(name)))
              for name in ['site', 'system', 'user']]

    with ramble.config.use_configuration(*scopes) as cfg:
        yield cfg


@pytest.fixture()
def mock_low_high_config(tmpdir):
    """Mocks two configuration scopes: 'low' and 'high'."""
    scopes = [ramble.config.ConfigScope(name, str(tmpdir.join(name)))
              for name in ['low', 'high']]

    with ramble.config.use_configuration(*scopes) as config:
        yield config


@pytest.fixture(scope='session')
def _store_dir_and_cache(tmpdir_factory):
    """Returns the directory where to build the mock database and
    where to cache it.
    """
    store = tmpdir_factory.mktemp('mock_store')
    cache = tmpdir_factory.mktemp('mock_store_cache')
    return store, cache


class MockLayout(object):
    def __init__(self, root):
        self.root = root

    def path_for_spec(self, spec):
        return '/'.join([self.root, spec.name])

    def check_installed(self, spec):
        return True


@pytest.fixture()
def gen_mock_layout(tmpdir):
    # Generate a MockLayout in a temporary directory. In general the prefixes
    # specified by MockLayout should never be written to, but this ensures
    # that even if they are, that it causes no harm
    def create_layout(root):
        subroot = tmpdir.mkdir(root)
        return MockLayout(str(subroot))

    yield create_layout


class MockConfig(object):
    def __init__(self, configuration, writer_key):
        self._configuration = configuration
        self.writer_key = writer_key

    def configuration(self):
        return self._configuration

    def writer_configuration(self):
        return self.configuration()[self.writer_key]


class ConfigUpdate(object):
    def __init__(self, root_for_conf, writer_mod, writer_key, monkeypatch):
        self.root_for_conf = root_for_conf
        self.writer_mod = writer_mod
        self.writer_key = writer_key
        self.monkeypatch = monkeypatch

    def __call__(self, filename):
        file = os.path.join(self.root_for_conf, filename + '.yaml')
        with open(file) as f:
            mock_config = MockConfig(syaml.load_config(f), self.writer_key)

        self.monkeypatch.setattr(
            ramble.modules.common,
            'configuration',
            mock_config.configuration
        )
        self.monkeypatch.setattr(
            self.writer_mod,
            'configuration',
            mock_config.writer_configuration
        )
        self.monkeypatch.setattr(
            self.writer_mod,
            'configuration_registry',
            {}
        )

##########
# Class and fixture to work around problems raising exceptions in directives,
# which cause tests like test_from_list_url to hang for Python 2.x metaclass
# processing.
#
# At this point only version and patch directive handling has been addressed.
##########


class MockBundle(object):
    has_code = False
    name = 'mock-bundle'
    versions = {}


@pytest.fixture
def mock_directive_bundle():
    """Return a mock bundle package for directive tests."""
    return MockBundle()


@pytest.fixture
def clear_directive_functions():
    """Clear all overidden directive functions for subsequent tests."""
    yield

    # Make sure any directive functions overidden by tests are cleared before
    # proceeding with subsequent tests that may depend on the original
    # functions.
    ramble.directives.DirectiveMeta._directives_to_be_executed = []


@pytest.fixture
def mock_executable(tmpdir):
    """Factory to create a mock executable in a temporary directory that
    output a custom string when run.
    """
    import jinja2

    def _factory(name, output, subdir=('bin',)):
        f = tmpdir.ensure(*subdir, dir=True).join(name)
        t = jinja2.Template('#!/bin/bash\n{{ output }}\n')
        f.write(t.render(output=output))
        f.chmod(0o755)
        return str(f)

    return _factory


@pytest.fixture()
def mutable_mock_workspace_path(tmpdir_factory):
    """Fixture for mocking the internal ramble workspaces directory."""
    saved_path = ramble.workspace.workspace_path
    mock_path = tmpdir_factory.mktemp('mock-workspace-path')
    ramble.workspace.workspace.workspace_path = str(mock_path)
    yield mock_path
    ramble.workspace.workspace.workspace_path = saved_path


@pytest.fixture
def no_path_access(monkeypatch):
    monkeypatch.setattr(os, 'access', _can_access)

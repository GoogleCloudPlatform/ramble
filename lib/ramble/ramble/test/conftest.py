# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import builtins
import collections
import io
import os
import os.path
import shutil

import py
import pytest

from llnl.util.filesystem import remove_linked_tree

import ramble.config
import ramble.paths
import ramble.repository
import ramble.stage
from ramble.fetch_strategy import FetchError, FetchStrategyComposite, URLFetchStrategy
from ramble.util.file_util import is_dry_run_path

import spack.platforms
import spack.util.spack_yaml as syaml
import spack.util.executable


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
        "--fast",
        action="store_true",
        default=False,
        help='runs only "fast" unit tests, instead of the whole suite',
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--fast"):
        # --fast not given, run all the tests
        return

    slow_tests = ["db", "network", "maybeslow", "long"]
    skip_as_slow = pytest.mark.skip(reason="skipped slow test [--fast command line option given]")
    for item in items:
        if any(x in item.keywords for x in slow_tests):
            item.add_marker(skip_as_slow)


#
# These fixtures are applied to all tests
#
@pytest.fixture(scope="function", autouse=True)
def no_chdir():
    """Ensure that no test changes Ramble's working directory.

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
    # when it's run after any test using this fixture
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
@pytest.fixture(scope="function")
def mock_apps_repo_path():
    obj_type = ramble.repository.ObjectTypes.applications
    yield ramble.repository.Repo(ramble.paths.mock_builtin_path, obj_type)


@pytest.fixture(scope="function")
def mock_mods_repo_path():
    obj_type = ramble.repository.ObjectTypes.modifiers
    yield ramble.repository.Repo(ramble.paths.mock_builtin_path, obj_type)


@pytest.fixture(scope="function")
def mock_pkg_mans_repo_path():
    obj_type = ramble.repository.ObjectTypes.package_managers
    yield ramble.repository.Repo(ramble.paths.mock_builtin_path, obj_type)


@pytest.fixture(scope="function")
def mutable_apps_repo_path():
    obj_type = ramble.repository.ObjectTypes.applications
    yield ramble.repository.Repo(ramble.paths.builtin_path, obj_type)


@pytest.fixture(scope="function")
def mutable_mods_repo_path():
    obj_type = ramble.repository.ObjectTypes.modifiers
    yield ramble.repository.Repo(ramble.paths.builtin_path, obj_type)


@pytest.fixture(scope="function")
def mutable_pkg_mans_repo_path():
    obj_type = ramble.repository.ObjectTypes.package_managers
    yield ramble.repository.Repo(ramble.paths.builtin_path, obj_type)


@pytest.fixture(scope="function")
def mock_applications(mock_apps_repo_path):
    """Use the 'builtin.mock' repository for applications instead of 'builtin'"""
    obj_type = ramble.repository.ObjectTypes.applications
    with ramble.repository.use_repositories(
        mock_apps_repo_path, object_type=obj_type
    ) as mock_apps_repo:
        yield mock_apps_repo


@pytest.fixture(scope="function")
def mock_modifiers(mock_mods_repo_path):
    """Use the 'builtin.mock' repository for modifiersinstead of 'builtin'"""
    obj_type = ramble.repository.ObjectTypes.modifiers
    with ramble.repository.use_repositories(
        mock_mods_repo_path, object_type=obj_type
    ) as mock_mods_repo:
        yield mock_mods_repo


@pytest.fixture(scope="function")
def mock_package_managers(mock_mods_repo_path):
    """Use the 'builtin.mock' repository for package managers of 'builtin'"""
    obj_type = ramble.repository.ObjectTypes.package_managers
    with ramble.repository.use_repositories(
        mock_mods_repo_path, object_type=obj_type
    ) as mock_mods_repo:
        yield mock_mods_repo


@pytest.fixture(scope="function")
def mutable_applications(mutable_apps_repo_path):
    """Use the 'builtin.mock' repository for applications instead of 'builtin'"""
    obj_type = ramble.repository.ObjectTypes.applications
    with ramble.repository.use_repositories(
        mutable_apps_repo_path, object_type=obj_type
    ) as apps_repo:
        yield apps_repo


@pytest.fixture(scope="function")
def mutable_modifiers(mutable_mods_repo_path):
    """Use the 'builtin.mock' repository for modifiers instead of 'builtin'"""
    obj_type = ramble.repository.ObjectTypes.modifiers
    with ramble.repository.use_repositories(
        mutable_mods_repo_path, object_type=obj_type
    ) as mods_repo:
        yield mods_repo


@pytest.fixture(scope="function")
def mutable_package_managers(mutable_mods_repo_path):
    """Use the 'builtin.mock' repository for package_mangers instead of 'builtin'"""
    obj_type = ramble.repository.ObjectTypes.package_managers
    with ramble.repository.use_repositories(
        mutable_mods_repo_path, object_type=obj_type
    ) as mods_repo:
        yield mods_repo


@pytest.fixture(scope="function")
def mutable_mock_apps_repo(mock_apps_repo_path):
    """Function-scoped mock applications, for tests that need to modify them."""
    obj_type = ramble.repository.ObjectTypes.applications
    mock_repo = ramble.repository.Repo(ramble.paths.mock_builtin_path, object_type=obj_type)
    with ramble.repository.use_repositories(mock_repo, object_type=obj_type) as mock_repo_path:
        yield mock_repo_path


@pytest.fixture(scope="function")
def mutable_mock_mods_repo(mock_mods_repo_path):
    """Function-scoped mock modifiers, for tests that need to modify them."""
    obj_type = ramble.repository.ObjectTypes.modifiers
    mock_repo = ramble.repository.Repo(ramble.paths.mock_builtin_path, object_type=obj_type)
    with ramble.repository.use_repositories(mock_repo, object_type=obj_type) as mock_repo_path:
        yield mock_repo_path


@pytest.fixture(scope="function")
def mutable_mock_pkg_mans_repo(mock_mods_repo_path):
    """Function-scoped mock package managers, for tests that need to modify them."""
    obj_type = ramble.repository.ObjectTypes.package_managers
    mock_repo = ramble.repository.Repo(ramble.paths.mock_builtin_path, object_type=obj_type)
    with ramble.repository.use_repositories(mock_repo, object_type=obj_type) as mock_repo_path:
        yield mock_repo_path


@pytest.fixture(scope="function")
def default_config():
    """Isolates the default configuration from the user configs.

    This ensures we can test the real default configuration without having
    tests fail when the user overrides the defaults that we test against."""
    defaults_path = os.path.join(ramble.paths.etc_path, "ramble", "defaults")
    with ramble.config.use_configuration(defaults_path) as defaults_config:
        yield defaults_config


@pytest.fixture(scope="session")
def configuration_dir(tmpdir_factory, linux_os):
    """Copies mock configuration files in a temporary directory. Returns the
    directory path.
    """
    tmpdir = tmpdir_factory.mktemp("configurations")

    # <test_path>/data/config has mock config yaml files in it
    # copy these to the site config.
    test_config = py.path.local(ramble.paths.test_path).join("data", "config")
    test_config.copy(tmpdir.join("site"))

    # Create temporary 'defaults', 'site' and 'user' folders
    tmpdir.ensure("user", dir=True)

    # Slightly modify config.yaml
    solver = os.environ.get("SPACK_TEST_SOLVER", "original")
    config_yaml = test_config.join("config.yaml")
    modules_root = tmpdir_factory.mktemp("share")
    tcl_root = modules_root.ensure("modules", dir=True)
    lmod_root = modules_root.ensure("lmod", dir=True)
    content = "".join(config_yaml.read()).format(solver, str(tcl_root), str(lmod_root))
    t = tmpdir.join("site", "config.yaml")
    t.write(content)
    yield tmpdir

    # Once done, cleanup the directory
    shutil.rmtree(str(tmpdir))


@pytest.fixture(scope="session")
def linux_os():
    """Returns a named tuple with attributes 'name' and 'version'
    representing the OS.
    """
    platform = spack.platforms.host()
    name, version = "debian", "6"
    if platform.name == "linux":
        current_os = platform.operating_system("default_os")
        name, version = current_os.name, current_os.version
    LinuxOS = collections.namedtuple("LinuxOS", ["name", "version"])
    return LinuxOS(name=name, version=version)


@pytest.fixture(scope="session")
def mock_configuration_scopes(configuration_dir):
    """Create a persistent Configuration object from the configuration_dir."""
    defaults = ramble.config.InternalConfigScope("_builtin", ramble.config.config_defaults)
    test_scopes = [defaults]
    test_scopes += [
        ramble.config.ConfigScope(name, str(configuration_dir.join(name)))
        for name in ["site", "system", "user"]
    ]
    test_scopes.append(ramble.config.InternalConfigScope("command_line"))

    yield test_scopes


@pytest.fixture(scope="function")
def config(mock_configuration_scopes):
    """This fixture activates/deactivates the mock configuration."""
    with ramble.config.use_configuration(*mock_configuration_scopes) as config:
        yield config


@pytest.fixture(scope="function")
def mutable_config(tmpdir_factory, configuration_dir):
    """Like config, but tests can modify the configuration."""
    mutable_dir = tmpdir_factory.mktemp("mutable_config").join("tmp")
    configuration_dir.copy(mutable_dir)

    defaults = ramble.config.InternalConfigScope("_builtin", ramble.config.config_defaults)
    scopes = [defaults]
    scopes += [
        ramble.config.ConfigScope(name, str(mutable_dir.join(name)))
        for name in ["site", "system", "user"]
    ]

    with ramble.config.use_configuration(*scopes) as cfg:
        yield cfg


@pytest.fixture(scope="function")
def mutable_empty_config(tmpdir_factory, configuration_dir):
    """Empty configuration that can be modified by the tests."""
    mutable_dir = tmpdir_factory.mktemp("mutable_config").join("tmp")
    scopes = [
        ramble.config.ConfigScope(name, str(mutable_dir.join(name)))
        for name in ["site", "system", "user"]
    ]

    with ramble.config.use_configuration(*scopes) as cfg:
        yield cfg


@pytest.fixture()
def mock_low_high_config(tmpdir):
    """Mocks two configuration scopes: 'low' and 'high'."""
    scopes = [ramble.config.ConfigScope(name, str(tmpdir.join(name))) for name in ["low", "high"]]

    with ramble.config.use_configuration(*scopes) as config:
        yield config


@pytest.fixture(scope="session")
def _store_dir_and_cache(tmpdir_factory):
    """Returns the directory where to build the mock database and
    where to cache it.
    """
    store = tmpdir_factory.mktemp("mock_store")
    cache = tmpdir_factory.mktemp("mock_store_cache")
    return store, cache


class MockLayout:
    def __init__(self, root):
        self.root = root

    def path_for_spec(self, spec):
        return "/".join([self.root, spec.name])

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


class MockConfig:
    def __init__(self, configuration, writer_key):
        self._configuration = configuration
        self.writer_key = writer_key

    def configuration(self):
        return self._configuration

    def writer_configuration(self):
        return self.configuration()[self.writer_key]


class ConfigUpdate:
    def __init__(self, root_for_conf, writer_mod, writer_key, monkeypatch):
        self.root_for_conf = root_for_conf
        self.writer_mod = writer_mod
        self.writer_key = writer_key
        self.monkeypatch = monkeypatch

    def __call__(self, filename):
        file = os.path.join(self.root_for_conf, filename + ".yaml")
        with open(file) as f:
            mock_config = MockConfig(syaml.load_config(f), self.writer_key)

        self.monkeypatch.setattr(ramble.modules.common, "configuration", mock_config.configuration)
        self.monkeypatch.setattr(
            self.writer_mod, "configuration", mock_config.writer_configuration
        )
        self.monkeypatch.setattr(self.writer_mod, "configuration_registry", {})


##########
# Class and fixture to work around problems raising exceptions in directives,
# which cause tests like test_from_list_url to hang for Python 2.x metaclass
# processing.
#
# At this point only version and patch directive handling has been addressed.
##########


class MockBundle:
    has_code = False
    name = "mock-bundle"
    versions = {}


@pytest.fixture
def mock_directive_bundle():
    """Return a mock bundle package for directive tests."""
    return MockBundle()


@pytest.fixture
def clear_directive_functions():
    """Clear all overridden directive functions for subsequent tests."""
    yield

    # Make sure any directive functions overridden by tests are cleared before
    # proceeding with subsequent tests that may depend on the original
    # functions.
    ramble.directives.DirectiveMeta._directives_to_be_executed = []


@pytest.fixture
def mock_executable(tmpdir):
    """Factory to create a mock executable in a temporary directory that
    output a custom string when run.
    """
    import jinja2

    def _factory(name, output, subdir=("bin",)):
        f = tmpdir.ensure(*subdir, dir=True).join(name)
        t = jinja2.Template("#!/bin/bash\n{{ output }}\n")
        f.write(t.render(output=output))
        f.chmod(0o755)
        return str(f)

    return _factory


@pytest.fixture(scope="function")
def mutable_mock_workspace_path(tmpdir_factory, mutable_config):
    """Fixture for mocking the internal ramble workspaces directory."""
    mock_path = tmpdir_factory.mktemp("mock-workspace-path")
    with ramble.config.override("config:workspace_dirs", str(mock_path)):
        yield mock_path


@pytest.fixture
def no_path_access(monkeypatch):
    monkeypatch.setattr(os, "access", _can_access)


@pytest.fixture(scope="function", autouse=True)
def print_all_logs(monkeypatch):
    import ramble.util.logger

    monkeypatch.setattr(ramble.util.logger.logger, "msg", ramble.util.logger.logger.all_msg)


##########
# Fake archives and repositories
##########


@pytest.fixture(scope="session", params=[(".tar.gz", "z")])
def mock_archive(request, tmpdir_factory):
    """Creates a very simple archive directory with a configure script and a
    makefile that installs to a prefix. Tars it up into an archive.
    """
    tar = spack.util.executable.which("tar", required=True)

    tmpdir = tmpdir_factory.mktemp("mock-archive-dir")
    tmpdir.ensure(ramble.stage._input_subdir, dir=True)
    repodir = tmpdir.join(ramble.stage._input_subdir)

    # Create the configure script
    configure_path = str(tmpdir.join(ramble.stage._input_subdir, "configure"))
    with open(configure_path, "w") as f:
        f.write(
            "#!/bin/sh\n"
            "prefix=$(echo $1 | sed 's/--prefix=//')\n"
            "cat > Makefile <<EOF\n"
            "all:\n"
            "\techo Building...\n\n"
            "install:\n"
            "\tmkdir -p $prefix\n"
            "\ttouch $prefix/dummy_file\n"
            "EOF\n"
        )
    os.chmod(configure_path, 0o755)

    # Archive it
    with tmpdir.as_cwd():
        archive_name = f"{ramble.stage._input_subdir}{request.param[0]}"
        tar(f"-c{request.param[1]}f", archive_name, ramble.stage._input_subdir)

    Archive = collections.namedtuple(
        "Archive", ["url", "path", "archive_file", "expanded_archive_basedir"]
    )
    archive_file = str(tmpdir.join(archive_name))
    url = "file://" + archive_file

    # Return the url
    yield Archive(
        url=url,
        archive_file=archive_file,
        path=str(repodir),
        expanded_archive_basedir=ramble.stage._input_subdir,
    )


@pytest.fixture(scope="function")
def install_mockery_mutable_config(mutable_config, mock_applications):
    """Hooks fake applications and config directory into Ramble.

    This is specifically for tests which want to use 'install_mockery' but
    also need to modify configuration (and hence would want to use
    'mutable config'): 'install_mockery' does not support this.
    """
    # We use a fake package, so temporarily disable checksumming
    with ramble.config.override("config:checksum", False):
        yield


class MockCache:
    def store(self, copy_cmd, relative_dest):
        pass

    def fetcher(self, target_path, digest, **kwargs):
        return MockCacheFetcher()


class MockCacheFetcher:
    def fetch(self):
        raise FetchError("Mock cache always fails for tests")

    def __str__(self):
        return "[mock fetch cache]"


@pytest.fixture(autouse=True)
def mock_fetch_cache(monkeypatch):
    """Substitutes ramble.paths.fetch_cache with a mock object that does nothing
    and raises on fetch.
    """
    monkeypatch.setattr(ramble.caches, "fetch_cache", MockCache())


@pytest.fixture()
def mock_fetch(mock_archive, monkeypatch):
    """Fake the URL for an input so it downloads from a file."""
    mock_fetcher = FetchStrategyComposite()
    mock_fetcher.append(URLFetchStrategy(mock_archive.url))

    yield mock_fetcher


@pytest.fixture()
def mock_file_auto_create(monkeypatch):
    builtin_open = builtins.open

    def open_or_create_inmem(path, *args, **kwargs):
        if not os.path.exists(path) and is_dry_run_path(path):
            if path.endswith(".yaml") or path.endswith(".yml"):
                content = "{}"
            else:
                content = ""
            inmem = io.StringIO(content)
            return inmem
        return builtin_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", open_or_create_inmem)


def pytest_generate_tests(metafunc):
    import re

    name_regex = re.compile(r"\s*(?P<name>[a-z0-9\-\_]+)\s*$")

    if "application" in metafunc.fixturenames:
        from ramble.main import RambleCommand

        list_cmd = RambleCommand("list")

        all_applications = []
        repo_apps = list_cmd().split("\n")

        for app_str in repo_apps:
            m = name_regex.match(app_str)
            if m:
                all_applications.append(m.group("name"))

        metafunc.parametrize("application", all_applications)

    if "modifier" in metafunc.fixturenames:
        from ramble.main import RambleCommand

        list_cmd = RambleCommand("list")

        all_modifiers = []
        repo_mods = list_cmd("--type", "modifiers").split("\n")

        for mod_str in repo_mods:
            m = name_regex.match(mod_str)
            if m:
                all_modifiers.append(m.group("name"))

        metafunc.parametrize("modifier", all_modifiers)

    if "mock_modifier" in metafunc.fixturenames:
        obj_type = ramble.repository.ObjectTypes.modifiers
        repo_path = ramble.repository.Repo(ramble.paths.mock_builtin_path, obj_type)

        all_modifiers = []
        for mod_name in repo_path.all_object_names():
            all_modifiers.append(mod_name)

        metafunc.parametrize("mock_modifier", all_modifiers)

    if "package_manager" in metafunc.fixturenames:
        from ramble.main import RambleCommand

        list_cmd = RambleCommand("list")

        all_package_managers = ["None"]
        repo_pms = list_cmd("--type", "package_managers").split("\n")

        for pm_str in repo_pms:
            m = name_regex.match(pm_str)
            if m:
                all_package_managers.append(m.group("name"))

        metafunc.parametrize("package_manager", all_package_managers)

    if "mock_package_managers" in metafunc.fixturenames:
        obj_type = ramble.repository.ObjectTypes.package_managers
        repo_path = ramble.repository.Repo(ramble.paths.mock_builtin_path, obj_type)

        all_package_managers = ["None"]
        for mod_name in repo_path.all_object_names():
            all_package_managers.append(mod_name)

        metafunc.parametrize("mock_package_managers", all_package_managers)

    if "config_section" in metafunc.fixturenames:
        from ramble.main import RambleCommand

        config_cmd = RambleCommand("config")

        all_sections = []
        config_sections = config_cmd("list").split(" ")

        for section_str in config_sections:
            if section_str != "":
                all_sections.append(section_str.strip())

        metafunc.parametrize("config_section", all_sections)

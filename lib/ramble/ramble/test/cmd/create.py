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

    try:
        # 1. Setup temporary repository
        repo_cmd("create", repo_path, repo_name)
        repo_cmd("add", "-t", "applications", "--scope=site", repo_path)
        repo_cmd("add", "-t", "modifiers", "--scope=site", repo_path)

        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None
        ramble.repository.paths[ramble.repository.ObjectTypes.modifiers]._instance = None

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

        # 4. Create Application definition using repository namespace
        create_cmd(
            "application",
            "my-ns-app",
            "--repo",
            "mockrepo",
        )
        ns_app_file = os.path.join(repo_path, "applications", "my-ns-app", "application.py")
        assert os.path.exists(ns_app_file)
    finally:
        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None
        ramble.repository.paths[ramble.repository.ObjectTypes.modifiers]._instance = None


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


def test_create_interactive_non_tty(mutable_config):
    """Verify that calling create in interactive mode or with missing args on non-tty aborts."""
    from ramble.error import RambleCommandError

    with pytest.raises(RambleCommandError):
        create_cmd()


def test_create_invalid_repo(mutable_config, tmpdir):
    """Verify error when repository namespace or path is invalid."""
    repo_path = str(tmpdir.join("test_repo"))
    repo_name = "mockrepo"
    try:
        repo_cmd("create", repo_path, repo_name)
        repo_cmd("add", "-t", "applications", "--scope=site", repo_path)

        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None

        from ramble.error import RambleCommandError

        with pytest.raises(RambleCommandError):
            create_cmd("application", "test-app", "--repo", "nonexistent_repo")
    finally:
        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None


def test_create_fallback_repo(mutable_config, tmpdir):
    """Verify fallback to builtin repository namespace when no repo specified."""
    repo_path = str(tmpdir.join("test_repo"))
    try:
        repo_cmd("create", repo_path, "builtin")
        repo_cmd("add", "-t", "applications", "--scope=site", repo_path)

        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None

        create_cmd("application", "my-fallback-app")

        app_file = os.path.join(repo_path, "applications", "my-fallback-app", "application.py")
        assert os.path.exists(app_file)
    finally:
        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None


def test_create_system(mutable_config, tmpdir):
    """Verify creation of system definition stub using generic template."""
    repo_path = str(tmpdir.join("test_repo"))
    repo_name = "mockrepo"
    try:
        repo_cmd("create", repo_path, repo_name)
        repo_cmd("add", "-t", "systems", "--scope=site", repo_path)

        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.systems]._instance = None

        create_cmd("system", "my-test-system", "--repo", repo_path)

        sys_file = os.path.join(repo_path, "systems", "my-test-system", "system.py")
        assert os.path.exists(sys_file)
    finally:
        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.systems]._instance = None


def test_create_unregistered_dir_repo(mutable_config, tmpdir):
    """Verify creation when --repo is a directory not registered in configuration."""
    unreg_path = str(tmpdir.join("unregistered_repo"))
    os.makedirs(os.path.join(unreg_path, "applications"))
    with open(os.path.join(unreg_path, "repo.yaml"), "w") as f:
        f.write("repo:\n  namespace: unreg\n")

    create_cmd("application", "test-unreg-app", "--repo", unreg_path)
    assert os.path.exists(
        os.path.join(unreg_path, "applications", "test-unreg-app", "application.py")
    )


def test_create_no_registered_repos(mutable_config, tmpdir, monkeypatch):
    """Verify fallback to builtin when no repositories are registered in configuration."""
    temp_builtin = str(tmpdir.join("builtin_temp"))
    os.makedirs(os.path.join(temp_builtin, "applications"))
    with open(os.path.join(temp_builtin, "repo.yaml"), "w") as f:
        f.write("repo:\n  namespace: builtin\n")

    import ramble.paths

    monkeypatch.setattr(ramble.paths, "builtin_path", temp_builtin)

    import ramble.repository

    # Make sure repos list is empty
    empty_repo_path = ramble.repository.RepoPath(
        object_type=ramble.repository.ObjectTypes.applications
    )
    monkeypatch.setattr(
        ramble.repository.paths[ramble.repository.ObjectTypes.applications],
        "factory",
        lambda: empty_repo_path,
    )
    ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None

    try:
        create_cmd("application", "test-fallback-manual-app")
        assert os.path.exists(
            os.path.join(
                temp_builtin, "applications", "test-fallback-manual-app", "application.py"
            )
        )
    finally:
        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None


def test_create_fallback_first_repo(mutable_config, tmpdir, monkeypatch):
    """Verify fallback to the first registered repository if builtin is not registered."""
    repo_path = str(tmpdir.join("test_repo"))
    try:
        repo_cmd("create", repo_path, "notbuiltin")
        repo_cmd("add", "-t", "applications", "--scope=site", repo_path)

        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None

        instance = ramble.repository.paths[ramble.repository.ObjectTypes.applications].instance
        filtered_repo_path = ramble.repository.RepoPath(
            *[r for r in instance.repos if r.namespace != "builtin"],
            object_type=ramble.repository.ObjectTypes.applications,
        )

        monkeypatch.setattr(
            ramble.repository.paths[ramble.repository.ObjectTypes.applications],
            "factory",
            lambda: filtered_repo_path,
        )
        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None

        # Since notbuiltin is registered and builtin is not, this should fallback to notbuiltin
        create_cmd("application", "my-fallback-first-app")

        app_file = os.path.join(
            repo_path, "applications", "my-fallback-first-app", "application.py"
        )
        assert os.path.exists(app_file)
    finally:
        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None


def test_create_missing_template(mutable_config, tmpdir, monkeypatch):
    """Verify fallback template is used when template files are missing."""
    repo_path = str(tmpdir.join("test_repo"))
    repo_cmd("create", repo_path, "mockrepo")
    repo_cmd("add", "-t", "applications", "--scope=site", repo_path)

    import ramble.repository

    ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None

    import os

    orig_exists = os.path.exists

    def mock_exists(path):
        if "templates" in path:
            return False
        return orig_exists(path)

    monkeypatch.setattr(os.path, "exists", mock_exists)

    try:
        create_cmd("application", "my-missing-tpl-app", "--repo", repo_path)
        app_file = os.path.join(repo_path, "applications", "my-missing-tpl-app", "application.py")
        assert os.path.exists(app_file)
        with open(app_file) as f:
            content = f.read()
            assert "class MyMissingTplApp:" in content
    finally:
        import ramble.repository

        ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None


def test_create_interactive_wizard(mutable_config, tmpdir, monkeypatch):
    """Verify successful generation of stub using interactive wizard."""
    repo_path = str(tmpdir.join("test_repo"))
    repo_name = "mockrepo"

    repo_cmd("create", repo_path, repo_name)
    repo_cmd("add", "-t", "applications", "--scope=site", repo_path)

    import ramble.repository

    ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None

    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    inputs = ["1", "my-wizard-app", "1", "2", "charlie", "science"]
    input_generator = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(input_generator))

    create_cmd("-i")

    app_file = os.path.join(repo_path, "applications", "my-wizard-app", "application.py")
    assert os.path.exists(app_file)
    with open(app_file) as f:
        content = f.read()
        assert "class MyWizardApp(ExecutableApplication):" in content
        assert "maintainers = ['charlie']" in content
        assert "tags = ['science']" in content


def test_create_interactive_wizard_validation_and_abort(mutable_config, tmpdir, monkeypatch):
    """Verify input validation and KeyboardInterrupt handling in interactive wizard."""
    repo_path = str(tmpdir.join("test_repo"))
    repo_name = "mockrepo"

    repo_cmd("create", repo_path, repo_name)
    repo_cmd("add", "-t", "applications", "--scope=site", repo_path)

    import ramble.repository

    ramble.repository.paths[ramble.repository.ObjectTypes.applications]._instance = None

    import sys

    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)

    inputs = ["", "invalid", "99", "1", "", "my wizard", "my-validation-app", "1", "2", "", ""]
    input_generator = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(input_generator))

    create_cmd("-i")

    app_file = os.path.join(repo_path, "applications", "my-validation-app", "application.py")
    assert os.path.exists(app_file)

    # Now test KeyboardInterrupt abort
    def mock_wizard_abort():
        raise KeyboardInterrupt

    monkeypatch.setattr("ramble.cmd.create.run_interactive_wizard", mock_wizard_abort)

    # create_cmd should exit gracefully without raising exception
    out = create_cmd("-i", fail_on_error=False)
    assert "[ABORTED] Object creation cancelled" in out

# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

from ramble.error import RambleCommandError
from ramble.main import RambleCommand

repo_cmd = RambleCommand("repo")
create_cmd = RambleCommand("create")


def test_create_help():
    """Verify create --help options."""
    with pytest.raises(SystemExit):
        create_cmd("--help")
    assert create_cmd.returncode in (None, 0)


@pytest.mark.parametrize(
    "obj_type, obj_name, repo_namespace, repo_add_type, extra_args, expected_subpath, expected_contents, expected_exception, create_duplicate",
    [
        (
            "application",
            "my-test-app",
            "mockrepo",
            "applications",
            ["--repo", "{repo_path}", "--maintainers", "alice,bob", "--tags", "bio,gpu"],
            "applications/my-test-app/application.py",
            [
                "class MyTestApp(ExecutableApplication):",
                'name = "my-test-app"',
                "maintainers = ['alice', 'bob']",
                "tags = ['bio', 'gpu']",
            ],
            None,
            False,
        ),
        (
            "modifier",
            "my-custom-mod",
            "mockrepo",
            "modifiers",
            ["--repo", "{repo_path}", "--base", "BasicModifier"],
            "modifiers/my-custom-mod/modifier.py",
            [
                "class MyCustomMod(BasicModifier):",
                'name = "my-custom-mod"',
            ],
            None,
            False,
        ),
        (
            "application",
            "my-ns-app",
            "mockrepo",
            "applications",
            ["--repo", "mockrepo"],
            "applications/my-ns-app/application.py",
            [
                "class MyNsApp(ExecutableApplication):",
                'name = "my-ns-app"',
            ],
            None,
            False,
        ),
        (
            "application",
            "my-fallback-app",
            "builtin",
            "applications",
            [],
            "applications/my-fallback-app/application.py",
            [
                "class MyFallbackApp(ExecutableApplication):",
                'name = "my-fallback-app"',
            ],
            None,
            False,
        ),
        (
            "system",
            "my-test-system",
            "mockrepo",
            "systems",
            ["--repo", "{repo_path}"],
            "systems/my-test-system/system.py",
            [
                "class MyTestSystem:",
                'name = "my-test-system"',
            ],
            None,
            False,
        ),
        (
            "application",
            "test-app",
            "mockrepo",
            "applications",
            ["--repo", "nonexistent_repo"],
            None,
            [],
            RambleCommandError,
            False,
        ),
        (
            "application",
            "duplicate-app",
            "mockrepo",
            "applications",
            ["--repo", "{repo_path}"],
            None,
            [],
            RambleCommandError,
            True,
        ),
    ],
)
def test_create_parameterized(
    mutable_config,
    tmpdir,
    obj_type,
    obj_name,
    repo_namespace,
    repo_add_type,
    extra_args,
    expected_subpath,
    expected_contents,
    expected_exception,
    create_duplicate,
):

    repo_path = str(tmpdir.join("test_repo"))
    try:
        import ramble.repository

        for t in ramble.repository.ObjectTypes:
            try:
                ramble.repository.paths[t]._instance = None
            except Exception:
                pass

        repo_cmd("create", repo_path, repo_namespace)
        repo_cmd("add", "-t", repo_add_type, "--scope=site", repo_path)

        for t in ramble.repository.ObjectTypes:
            try:
                ramble.repository.paths[t]._instance = None
            except Exception:
                pass

        parsed_args = [obj_type, obj_name]
        for arg in extra_args:
            if arg == "{repo_path}":
                parsed_args.append(repo_path)
            else:
                parsed_args.append(arg)

        if create_duplicate:
            create_cmd(*parsed_args)
            with pytest.raises(expected_exception):
                create_cmd(*parsed_args)
        elif expected_exception:
            with pytest.raises(expected_exception):
                create_cmd(*parsed_args)
        else:
            create_cmd(*parsed_args)

            full_path = os.path.join(repo_path, expected_subpath)
            assert os.path.exists(full_path)

            with open(full_path) as f:
                content = f.read()
                for stub in expected_contents:
                    assert stub in content
    finally:
        import ramble.repository

        for t in ramble.repository.ObjectTypes:
            try:
                ramble.repository.paths[t]._instance = None
            except Exception:
                pass


def test_create_interactive_non_tty(mutable_config):
    """Verify that calling create in interactive mode or with missing args on non-tty aborts."""
    from ramble.error import RambleCommandError

    with pytest.raises(RambleCommandError):
        create_cmd()


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

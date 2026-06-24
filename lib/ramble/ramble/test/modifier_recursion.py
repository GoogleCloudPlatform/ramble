# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.language.application_language import executable, workload
from ramble.language.modifier_language import mode
from ramble.language.shared_language import modifier
from ramble.repository import get_base_class

ApplicationBase = get_base_class("application-base")
BasicModifier = get_base_class("basic-modifier")


def test_modifier_directive_registration():
    class TestApp(ApplicationBase):
        __module__ = "ramble.app"
        name = "test-app"
        modifier("mod1", mode="test")
        modifier("mod2", when=["workload=test"])

    app = TestApp("/tmp/path.py")
    assert hasattr(app, "object_modifiers")
    assert len(app.object_modifiers) == 2

    found = 0
    for when_key, mod_definitions in app.object_modifiers.items():
        for mod_def in mod_definitions:
            if mod_def["name"] == "mod1":
                assert when_key == frozenset()
                assert mod_def["mode"] == "test"
                found += 1
            elif mod_def["name"] == "mod2":
                assert when_key == frozenset(["workload=test"])
                found += 1
    assert found == 2


def test_modifier_recursion(
    mutable_config, mutable_mock_apps_repo, mutable_mock_mods_repo, tmpdir
):
    from ramble.language.shared_language import modifier
    from ramble.repository import get_base_class

    ApplicationBase = get_base_class("application-base")
    BasicModifier = get_base_class("basic-modifier")

    class Mod2(BasicModifier):
        __module__ = "ramble.mod"
        name = "mod2"
        mode("test", description="test mode")

    class Mod1(BasicModifier):
        __module__ = "ramble.mod"
        name = "mod1"
        mode("test", description="test mode")
        modifier("mod2", mode="test")

    class RecApp(ApplicationBase):
        __module__ = "ramble.app"
        name = "rec-app"
        executable("test", "test_cmd")
        workload("test", executables=["test"])
        modifier("mod1", mode="test")

    # Mock the repository to return our classes
    import ramble.repository

    orig_get = ramble.repository.get

    def mock_get(name, obj_type=ramble.repository.ObjectTypes.applications):
        if name == "mod2":
            return Mod2("/tmp/mod2.py")
        if name == "mod1":
            return Mod1("/tmp/mod1.py")
        return orig_get(name, obj_type)

    import unittest.mock

    with unittest.mock.patch("ramble.repository.get", side_effect=mock_get):
        app_inst = RecApp("/tmp/rec-app.py")

        # Mock workspace
        mock_workspace = unittest.mock.MagicMock()
        mock_workspace.experiment_dir = str(tmpdir)

        app_inst.set_variables_and_variants({"workload_name": "test"}, {}, mock_workspace, None)
        app_inst.set_active_workload()

        app_inst.build_modifier_instances()

        assert len(app_inst._modifier_instances) == 2
        mod_names = [m.name for m in app_inst._modifier_instances]
        assert "mod1" in mod_names
        assert "mod2" in mod_names


def test_modifier_disabled_recursion(
    mutable_config, mutable_mock_apps_repo, mutable_mock_mods_repo, tmpdir
):
    from ramble.language.shared_language import modifier
    from ramble.repository import get_base_class

    ApplicationBase = get_base_class("application-base")

    class RecApp(ApplicationBase):
        __module__ = "ramble.app"
        name = "rec-app"
        executable("test", "test_cmd")
        workload("test", executables=["test"])
        modifier("mod1", mode="test")

    app_inst = RecApp("/tmp/rec-app.py")

    # Mock workspace
    import unittest.mock

    mock_workspace = unittest.mock.MagicMock()
    mock_workspace.experiment_dir = str(tmpdir)

    app_inst.set_variables_and_variants({"workload_name": "test"}, {}, mock_workspace, None)

    # Disable modifiers
    app_inst.object_variants.experiment_variant("inject_modifiers_from_directives", False)

    app_inst.set_active_workload()

    app_inst.build_modifier_instances()

    assert len(app_inst._modifier_instances) == 0

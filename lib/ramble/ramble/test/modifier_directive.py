# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")


def test_modifier_directive_injection(
    mutable_mock_workspace_path, mutable_applications, mock_modifiers, workspace_name
):
    # Instead of writing files to mock repos directly, we can define a small Application class here
    # However Ramble requires applications to be in a repository.
    # Let's write an application definition dynamically to the mutable_applications repo

    app_dir = os.path.join(
        mutable_applications.first_repo().root, "applications", "modifier-directive-app"
    )
    os.makedirs(app_dir, exist_ok=True)
    with open(os.path.join(app_dir, "application.py"), "w", encoding="utf-8") as f:
        f.write(
            """# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
class ModifierDirectiveApp(ExecutableApplication):
    name = "modifier-directive-app"

    executable('run', 'echo "hello"', use_mpi=False)
    workload('test', executable='run')

    # Inject a mock modifier
    modifier('test-mod')

    # Conditionally inject a non-existent modifier (should not be injected)
    modifier('bad-modifier', when='@+some_fake_variant')

    # Conditionally inject another modifier when inject_modifiers_from_directives is false
    modifier('bad-modifier-2', when='~inject_modifiers_from_directives')
"""
        )

    # Write out the mock modifiers
    mod_dir1 = os.path.join(mock_modifiers.first_repo().root, "modifiers", "test-mod")
    os.makedirs(mod_dir1, exist_ok=True)
    with open(os.path.join(mod_dir1, "modifier.py"), "w", encoding="utf-8") as f:
        f.write(
            """# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *
class TestMod(BasicModifier):
    name = "test-mod"
    mode('standard', description='Standard mode')
"""
        )

    mod_dir2 = os.path.join(mock_modifiers.first_repo().root, "modifiers", "bad-modifier")
    os.makedirs(mod_dir2, exist_ok=True)
    with open(os.path.join(mod_dir2, "modifier.py"), "w", encoding="utf-8") as f:
        f.write(
            """# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *
class BadModifier(BasicModifier):
    name = "bad-modifier"
    mode('standard', description='Standard mode')
"""
        )

    mod_dir3 = os.path.join(mock_modifiers.first_repo().root, "modifiers", "bad-modifier-2")
    os.makedirs(mod_dir3, exist_ok=True)
    with open(os.path.join(mod_dir3, "modifier.py"), "w", encoding="utf-8") as f:
        f.write(
            """# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *
class BadModifier2(BasicModifier):
    name = "bad-modifier-2"
    mode('standard', description='Standard mode')
"""
        )

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        # Test 1: With inject_modifiers_from_directives enabled (default)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(
                """
ramble:
  variables:
    mpi_command: 'mpirun'
    batch_submit: 'batch_submit'
    processes_per_node: '1'
    n_ranks: '1'
  applications:
    modifier-directive-app:
      workloads:
        test:
          experiments:
            exp1:
              variables:
                env_name: 'test'
"""
            )

        ws._re_read()
        experiment_set = ws.build_experiment_set()
        # Find the experiment
        exp_name = "modifier-directive-app.test.exp1"
        app_inst = experiment_set.get_experiment(exp_name)
        assert app_inst is not None

        # We expect test-mod to be in the modifiers
        modifier_names = [m.name for m in app_inst._modifier_instances]
        assert "test-mod" in modifier_names
        assert "bad-modifier" not in modifier_names
        assert "bad-modifier-2" not in modifier_names

        with ramble.workspace.create(workspace_name + "_2") as ws2:
            ws2.write()
            config_path2 = os.path.join(ws2.config_dir, ramble.workspace.CONFIG_FILE_NAME)

            # Test 2: With inject_modifiers_from_directives disabled via variants
            with open(config_path2, "w", encoding="utf-8") as f:
                f.write(
                    """
ramble:
  variables:
    mpi_command: 'mpirun'
    batch_submit: 'batch_submit'
    processes_per_node: '1'
    n_ranks: '1'
  variants:
    package_manager: spack
  applications:
    modifier-directive-app:
      variants:
        inject_modifiers_from_directives: False
      workloads:
        test:
          experiments:
            exp2:
              variables:
                env_name: 'test'
"""
                )

            ws2._re_read()
            experiment_set = ws2.build_experiment_set()
            exp_name = "modifier-directive-app.test.exp2"
            app_inst = experiment_set.get_experiment(exp_name)
            assert app_inst is not None

            # We expect NO modifiers to be injected
            modifier_names = [m.name for m in app_inst._modifier_instances]
            assert "test-mod" not in modifier_names
            assert "bad-modifier" not in modifier_names
            assert "bad-modifier-2" not in modifier_names


def test_modifier_directive_from_package_manager(
    mutable_mock_workspace_path,
    mutable_applications,
    mutable_package_managers,
    mock_modifiers,
    workspace_name,
):
    app_dir = os.path.join(
        mutable_applications.first_repo().root, "applications", "pm-directive-app"
    )
    os.makedirs(app_dir, exist_ok=True)
    with open(os.path.join(app_dir, "application.py"), "w", encoding="utf-8") as f:
        f.write(
            """# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
class PmDirectiveApp(ExecutableApplication):
    name = "pm-directive-app"

    executable('run', 'echo "hello"', use_mpi=False)
    workload('test', executable='run')
"""
        )

    # Write out a mock package manager
    pm_dir = os.path.join(
        mutable_package_managers.first_repo().root, "package_managers", "directive-pm"
    )
    os.makedirs(pm_dir, exist_ok=True)
    with open(os.path.join(pm_dir, "package_manager.py"), "w", encoding="utf-8") as f:
        f.write(
            """# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.pkgmankit import *
class DirectivePm(PackageManagerBase):
    name = "directive-pm"
    modifier('directive-mod')

    def environment_load_commands(self, *args, **kwargs): pass
    def environment_unload_commands(self, *args, **kwargs): pass
    def get_package_list(self, *args, **kwargs): return []
    def package_name_from_spec(self, spec, *args, **kwargs): return spec
"""
        )

    # Write out the mock modifiers
    mod_dir1 = os.path.join(mock_modifiers.first_repo().root, "modifiers", "directive-mod")
    os.makedirs(mod_dir1, exist_ok=True)
    with open(os.path.join(mod_dir1, "modifier.py"), "w", encoding="utf-8") as f:
        f.write(
            """# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *
class DirectiveMod(BasicModifier):
    name = "directive-mod"
    mode('standard', description='Standard mode')
"""
        )

    with ramble.workspace.create(workspace_name) as ws:
        ws.write()

        config_path = os.path.join(ws.config_dir, ramble.workspace.CONFIG_FILE_NAME)

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(
                """
ramble:
  variables:
    mpi_command: 'mpirun'
    batch_submit: 'batch_submit'
    processes_per_node: '1'
    n_ranks: '1'
  variants:
    package_manager: directive-pm
  applications:
    pm-directive-app:
      workloads:
        test:
          experiments:
            exp1:
              variables:
                env_name: 'test'
"""
            )

        ws._re_read()
        experiment_set = ws.build_experiment_set()
        # Find the experiment
        exp_name = "pm-directive-app.test.exp1"
        app_inst = experiment_set.get_experiment(exp_name)
        assert app_inst is not None

        # We expect directive-mod to be in the modifiers because the package manager injected it
        modifier_names = [m.name for m in app_inst._modifier_instances]
        assert "directive-mod" in modifier_names

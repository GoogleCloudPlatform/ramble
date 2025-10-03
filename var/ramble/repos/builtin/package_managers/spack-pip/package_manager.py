# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.pkg_man.builtin.pip import Pip
from ramble.pkg_man.builtin.spack import Spack
from ramble.pkgmankit import *


class SpackPip(PackageManagerBase):
    """Chained spack + pip package manager

    This package manager uses spack to install a spack environment, then using the python that is installed within this environment (or whichever one is available in your path) will install pip packages into a python virtual environment. Experiments will load both environments, in the order of spack then pip.
    """

    name = "spack-pip"

    maintainers("douglasjacobsen")

    _allow_unprefixed_specs = False

    package_manager_family("spack")
    package_manager_family("pip")

    archive_pattern(os.path.join("{env_path}", "spack.yaml"))
    archive_pattern(os.path.join("{env_path}", "spack.lock"))
    archive_pattern(os.path.join("{env_path}", "requirements.txt"))
    archive_pattern(os.path.join("{env_path}", "requirements.lock"))

    def __init__(self, file_path):
        # Let parents run first; then we enforce our runner.
        super().__init__(file_path)

        self.spack_mgr = Spack(file_path)
        self.spack_mgr._allow_unprefixed_specs = False
        self.pip_mgr = Pip(file_path)
        self.pip_mgr._allow_unprefixed_specs = False

    def set_application(self, app_inst):
        self.spack_mgr.set_application(app_inst)
        self.pip_mgr.set_application(app_inst)

    def build_used_variables(self, workspace):
        self.spack_mgr.build_used_variables(workspace)
        self.pip_mgr.build_used_variables(workspace)

    def populate_inventory(
        self, workspace, force_compute=False, require_exist=False
    ):
        """Inject spack and pip software inventory information

        Args:
            workspace (ramble.workspace.Workspace): Reference to the workspace that is currently
                                   being acted on.
            force_compute (bool): Whether to force computation of hashes or not
            require_exist (bool): Whether to require environment hashes exist or not.
        """

        self.spack_mgr.populate_inventory(
            workspace, force_compute=force_compute, require_exist=require_exist
        )
        self.pip_mgr.populate_inventory(
            workspace, force_compute=force_compute, require_exist=require_exist
        )

    def _add_software_to_results(self, workspace, app_inst=None):
        self.spack_mgr._add_software_to_results(workspace, app_inst)
        self.pip_mgr._add_software_to_results(workspace, app_inst)

    # Spack phases
    register_phase("software_create_env_spack", pipeline="setup")
    register_phase("software_create_env_spack", pipeline="pushdeployment")
    register_phase(
        "software_create_env_spack",
        pipeline="mirror",
        run_before=["software_configure_spack"],
    )

    def _software_create_env_spack(self, workspace, app_inst=None):
        self.spack_mgr._software_create_env(workspace, app_inst)

    register_phase(
        "software_install_requested_compilers",
        pipeline="setup",
        run_after=["software_create_env_spack"],
    )

    def _software_install_requested_compilers(self, workspace, app_inst=None):
        self.spack_mgr._software_install_requested_compilers(
            workspace, app_inst
        )

    register_phase(
        "software_configure_spack",
        pipeline="setup",
        run_after=[
            "software_create_env_spack",
            "software_install_requested_compilers",
        ],
    )

    def _software_configure_spack(self, workspace, app_inst=None):
        self.spack_mgr._software_configure(workspace, app_inst)

    register_phase(
        "software_install_spack",
        pipeline="setup",
        run_after=["software_configure_spack"],
        run_before=["evaluate_requirements_spack"],
    )

    def _software_install_spack(self, workspace, app_inst=None):
        self.spack_mgr._software_install(workspace, app_inst)
        self.pip_mgr.runner.reset_bs_python(
            self.spack_mgr.runner.get_spack_python()
        )

    register_phase(
        "define_package_paths_spack",
        pipeline="setup",
        run_after=["software_install_spack", "evaluate_requirements_spack"],
        run_before=["make_experiments"],
    )

    def _define_package_paths_spack(self, workspace, app_inst=None):
        self.spack_mgr._define_package_paths(workspace, app_inst)

    register_phase(
        "evaluate_requirements_spack",
        pipeline="setup",
        run_before=["make_experiments"],
    )

    def _evaluate_requirements_spack(self, workspace, app_inst=None):
        self.spack_mgr._evaluate_requirements(workspace, app_inst)

    register_phase("mirror_software_spack", pipeline="mirror")

    def _mirror_software_spack(self, workspace, app_inst=None):
        self.spack_mgr._mirror_software(workspace, app_inst)

    register_phase("push_to_spack_cache", pipeline="pushtocache", run_after=[])

    def _push_to_spack_cache(self, workspace, app_inst=None):
        self.spack_mgr._push_to_spack_cache(workspace, app_inst)

    register_phase(
        "deploy_spack_artifacts",
        pipeline="pushdeployment",
        run_after=["software_create_env_spack", "deploy_artifacts"],
    )

    def _deploy_spack_artifacts(self, workspace, app_inst=None):
        self.spack_mgr._deploy_spack_artifacts(workspace, app_inst)

    register_phase(
        "software_configure_spack",
        pipeline="mirror",
        run_before=["mirror_software_spack"],
    )

    register_phase(
        "software_create_env_spack",
        pipeline="mirror",
        run_before=["software_configure_spack"],
    )

    register_builtin(
        "spack_source",
        required=True,
    )

    register_builtin(
        "spack_activate",
        required=True,
        depends_on=["spack_source"],
    )
    register_builtin(
        "spack_deactivate",
        required=False,
        depends_on=["spack_source"],
    )

    def spack_source(self):
        return self.spack_mgr.spack_source()

    def spack_activate(self):
        return self.spack_mgr.spack_activate()

    def spack_deactivate(self):
        return self.spack_mgr.spack_deactivate()

    # Pip Phases
    register_builtin(
        "pip_activate",
        required=True,
        depends_on=["builtin::env_vars", "spack_activate"],
    )

    def pip_activate(self):
        return self.pip_mgr.pip_activate()

    register_builtin(
        "pip_deactivate",
        required=False,
        depends_on=["pip_activate"],
    )

    def pip_deactivate(self):
        return self.pip_mgr.pip_deactivate()

    # TODO: This needs to happen after loading the spack environment in the environment pip is run in.
    register_phase(
        "software_create_env_pip",
        pipeline="setup",
        run_after=["software_install_spack"],
    )

    def _software_create_env_pip(self, workspace, app_inst=None):
        self.pip_mgr._software_create_env(workspace, app_inst)

    register_phase(
        "software_install_pip",
        pipeline="setup",
        run_after=["software_create_env_pip"],
    )

    def _software_install_pip(self, workspace, app_inst=None):
        self.pip_mgr._software_install(workspace, app_inst)

    register_phase(
        "define_package_paths_pip",
        pipeline="setup",
        run_after=["software_install_pip"],
        run_before=["make_experiments"],
    )

    def _define_package_paths_pip(self, workspace, app_inst=None):
        self.pip_mgr._define_package_paths(workspace, app_inst)

    register_phase("warn_mirror_support_pip", pipeline="mirror")

    def _warn_mirror_support_pip(self, workspace, app_inst=None):
        self.pip_mgr._warn_mirror_support_pip(workspace, app_inst)

    register_phase(
        "configure_for_analyze",
        pipeline="analyze",
        run_before=["analyze_experiments"],
    )

    def _configure_for_analyze(self, workspace, app_inst=None):
        self.spack_mgr._software_create_env(workspace, app_inst)
        self.pip_mgr.runner.reset_bs_python(
            self.spack_mgr.runner.get_spack_python()
        )
        self.pip_mgr._software_create_env(workspace, app_inst)

    def get_package_list(self, workspace):
        pkg_list = self.spack_mgr.get_package_list()
        pkg_list.extend(self.pip_mgr.get_package_list())

    def environment_load_commands(self):
        commands = self.spack_mgr.environment_load_commands()
        commands.extend(self.pip_mgr.environment_load_commands())
        return commands

    def environment_unload_commands(self):
        commands = self.spack_mgr.environment_unload_commands()
        commands.extend(self.pip_mgr.environment_unload_commands())
        return commands

    def get_experiment_specs(self, app_inst=None, prefixed=False):
        specs = self.spack_mgr.get_experiment_specs(
            app_inst=app_inst, prefixed=True
        )
        for name, definitions in self.pip_mgr.get_experiment_specs(
            app_inst=app_inst, prefixed=True
        ).items():
            if name not in specs:
                specs[name] = []
            specs[name].extend(definitions)
        return specs

    def get_experiment_compilers(self, app_inst=None, prefixed=False):
        specs = self.spack_mgr.get_experiment_compilers(
            app_inst=app_inst, prefixed=True
        )
        for name, definitions in self.pip_mgr.get_experiment_compilers(
            app_inst=app_inst, prefixed=True
        ).items():
            if name not in specs:
                specs[name] = []
            specs[name].extend(definitions)
        return specs

# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import deprecation

from ramble.pkgmankit import *  # noqa: F403

from ramble.pkg_man.builtin.spack_lightweight import (
    SpackLightweight,
    RunnerError,
)


class Spack(SpackLightweight):
    """Full Spack package manager class definition

    This inherits from the spack-lightweight package manager, and extends it by
    adding the software_install and define_package_paths phases.
    """

    name = "spack"

    register_phase(
        "software_install",
        pipeline="setup",
        run_after=["software_configure"],
        run_before=["evaluate_requirements"],
    )

    def _software_install(self, workspace, app_inst=None):
        """Install application's software using spack"""

        # See if we cached this already, and if so return
        env_path = self.app_inst.expander.env_path

        cache_tupl = ("spack-install", env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug("{} already in cache.".format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        if self.environment_required():
            try:
                self.runner.set_dry_run(workspace.dry_run)
                self.runner.set_env(env_path)

                logger.msg("Installing software")

                self.runner.activate()
                self.runner.install()
            except RunnerError as e:
                logger.die(e)

    register_phase(
        "define_package_paths",
        pipeline="setup",
        run_after=["software_install", "evaluate_requirements"],
        run_before=["make_experiments"],
    )

    def _define_package_paths(self, workspace, app_inst=None):
        """Define variables containing the path to all spack packages

        For every spack package defined within an application context, define
        a variable that refers to that packages installation location.

        As an example:
        <ramble.yaml>
        spack:
          applications:
            wrfv4:
              wrf:
                base: wrf
                version: 4.2.2

        Would define a variable `wrf` that contains the installation path of
        wrf@4.2.2
        """

        logger.msg("Defining Spack variables")

        cache = workspace.pkg_path_cache[self.name]
        app_context = self.app_inst.expander.expand_var_name(
            self.keywords.env_name
        )
        require_env = self.environment_required()
        software_environments = workspace.software_environments
        software_environment = software_environments.render_environment(
            app_context, self.app_inst.expander, self, require=require_env
        )
        if software_environment is not None:
            # Try to resolve using local cache first
            unresolved_specs = []
            for (
                pkg_spec
            ) in software_environments.package_specs_for_environment(
                software_environment
            ):
                if pkg_spec in cache:
                    spack_pkg_name, pkg_path = cache.get(pkg_spec)
                    if spack_pkg_name not in self.app_inst.variables:
                        self.app_inst.define_variable(spack_pkg_name, pkg_path)
                        self.app_inst.define_variable(
                            f"{spack_pkg_name}_path", pkg_path
                        )
                    else:
                        logger.msg(
                            f"Variable {spack_pkg_name} defined. "
                            + "Skipping extraction from spack"
                        )
                else:
                    unresolved_specs.append(pkg_spec)
            if not unresolved_specs:
                return

            try:
                logger.debug("Resolving package paths using Spack")
                self.runner.set_dry_run(workspace.dry_run)
                self.runner.set_env(self.app_inst.expander.env_path)

                self.runner.activate()

                for pkg_spec in unresolved_specs:
                    spack_pkg_name, pkg_path = self.runner.get_package_path(
                        pkg_spec
                    )
                    if f"{spack_pkg_name}_path" not in self.app_inst.variables:
                        self.app_inst.define_variable(spack_pkg_name, pkg_path)
                        self.app_inst.define_variable(
                            f"{spack_pkg_name}_path", pkg_path
                        )
                        cache[pkg_spec] = (spack_pkg_name, pkg_path)
                    else:
                        logger.msg(
                            f"Variable {spack_pkg_name} defined. "
                            + "Skipping extraction from spack"
                        )
                        logger.msg(
                            f"Variable {spack_pkg_name}_path defined. "
                            + "Skipping extraction from spack"
                        )

            except RunnerError as e:
                logger.die(e)

    @deprecation.deprecated(
        deprecated_in="0.5.0",
        removed_in="0.6.0",
        current_version=str(ramble.ramble_version),
        details="Package name variables are deprecated. Transition to the {package_name_path} syntax",
    )
    def __print_deprecated_warning(self, package_name):
        logger.warn(
            f'The package path variable "{package_name}" is deprecated'
        )
        logger.warn(f'Please transition to "{package_name}_path" instead.')

    register_phase(
        "warn_deprecated_variables",
        pipeline="setup",
        run_after=["make_experiments"],
    )

    def _warn_deprecated_variables(self, workspace, app_inst=None):
        cache = workspace.pkg_path_cache[self.name]

        app_context = self.app_inst.expander.expand_var_name(
            self.keywords.env_name
        )

        require_env = self.environment_required()
        software_environments = workspace.software_environments
        software_environment = software_environments.render_environment(
            app_context, self.app_inst.expander, self, require=require_env
        )

        if software_environment is not None:
            for (
                pkg_spec
            ) in software_environments.package_specs_for_environment(
                software_environment
            ):
                if pkg_spec in cache:
                    spack_pkg_name, pkg_path = cache.get(pkg_spec)
                    if (
                        spack_pkg_name
                        in self.app_inst.expander._used_variables
                    ):
                        self.__print_deprecated_warning(spack_pkg_name)

    register_builtin(
        "spack_activate",
        required=True,
        depends_on=["package_manager_builtin::spack::spack_source"],
    )
    register_builtin(
        "spack_deactivate",
        required=False,
        depends_on=["package_manager_builtin::spack::spack_source"],
    )

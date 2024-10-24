# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.pkgmankit import *  # noqa: F403

import os
import re
import shutil
import shlex
import fnmatch

import llnl.util.filesystem as fs
from spack.util.executable import ProcessError
import spack.util.spack_yaml as syaml

import ramble.config
import ramble.error
import ramble.util.hashing
import ramble.util.command_runner
from ramble.util.logger import logger


class SpackLightweight(PackageManagerBase):
    """Lightweight version of Spack package manager class definition

    This implements most of the logic for the spack package manager. The
    primary difference is the software_install and define_package_paths are not
    executed during setup, as they should be deferred to installation time.

    The installation portion is not defined in this class, as applications that
    require this should add this on separately.
    """

    name = "spack-lightweight"

    _spec_prefix = "spack"

    def __init__(self, file_path):
        super().__init__(file_path)

        self.runner = SpackRunner()

    register_phase(
        "software_install_requested_compilers",
        pipeline="setup",
        run_after=["software_create_env"],
    )

    def _software_install_requested_compilers(self, workspace, app_inst=None):
        """Install compilers an application uses"""

        # See if we cached this already, and if so return
        env_path = self.app_inst.expander.env_path
        if not env_path:
            raise ApplicationError("Ramble env_path is set to None.")
        logger.msg("Installing compilers")

        cache_tupl = ("spack-compilers", env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug("{} already in cache.".format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            self.runner.set_compiler_config_dir(
                workspace.auxiliary_software_dir
            )
            self.runner.set_dry_run(workspace.dry_run)

            app_context = self.app_inst.expander.expand_var_name(
                self.keywords.env_name
            )

            require_env = self.environment_required()
            software_envs = workspace.software_environments
            software_env = software_envs.render_environment(
                app_context, self.app_inst.expander, self, require=require_env
            )

            if software_env is not None:
                for (
                    compiler_spec
                ) in software_envs.compiler_specs_for_environment(
                    software_env
                ):
                    logger.debug(f"Installing compiler: {compiler_spec}")
                    self.runner.install_compiler(compiler_spec)

        except ramble.util.command_runner.RunnerError as e:
            logger.die(e)

    register_phase("software_create_env", pipeline="mirror")
    register_phase("software_create_env", pipeline="setup")
    register_phase("software_create_env", pipeline="pushdeployment")

    def _software_create_env(self, workspace, app_inst=None):
        """Create the spack environment for this experiment

        Extract all specs this experiment uses, and write the spack environment
        file for it.
        """

        logger.msg("Creating Spack environment")

        # See if we cached this already, and if so return
        env_path = self.app_inst.expander.env_path
        if not env_path:
            raise ApplicationError("Ramble env_path is set to None.")

        cache_tupl = ("spack-env", env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug("{} already in cache.".format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        package_manager_config_dicts = [self.app_inst.package_manager_configs]
        for mod_inst in self.app_inst._modifier_instances:
            package_manager_config_dicts.append(
                mod_inst.package_manager_configs
            )

        for config_dict in package_manager_config_dicts:
            for _, config in config_dict.items():
                if fnmatch.fnmatch(self.name, config["package_manager"]):
                    self.runner.add_config(config["config"])

        try:
            self.runner.set_dry_run(workspace.dry_run)
            self.runner.create_env(
                self.app_inst.expander.expand_var_name(self.keywords.env_path)
            )
            self.runner.activate()

            # Write auxiliary software files into created spack env.
            for name, contents in workspace.all_auxiliary_software_files():
                aux_file_path = self.app_inst.expander.expand_var(
                    os.path.join(
                        self.app_inst.expander.expansion_str(
                            self.keywords.env_path
                        ),
                        f"{name}",
                    )
                )
                self.runner.add_include_file(aux_file_path)
                with open(aux_file_path, "w+") as f:
                    f.write(self.app_inst.expander.expand_var(contents))

            env_context = self.app_inst.expander.expand_var_name(
                self.keywords.env_name
            )
            require_env = self.environment_required()
            software_envs = workspace.software_environments
            software_env = software_envs.render_environment(
                env_context, self.app_inst.expander, self, require=require_env
            )
            if software_env is not None:
                if isinstance(software_env, ExternalEnvironment):
                    self.runner.copy_from_external_env(
                        software_env.external_env
                    )
                else:
                    for (
                        pkg_spec
                    ) in software_envs.package_specs_for_environment(
                        software_env
                    ):
                        self.runner.add_spec(pkg_spec)

                    self.runner.generate_env_file()

                added_packages = set(self.runner.added_packages())
                for pkg in self.app_inst.required_packages.keys():
                    if pkg not in added_packages:
                        logger.die(
                            f"Software spec {pkg} is not defined "
                            f"in environment {env_context}, but is "
                            f"required by the {self.name} application "
                            "definition"
                        )

                for mod_inst in self.app_inst._modifier_instances:
                    for pkg in mod_inst.required_packages.keys():
                        if pkg not in added_packages:
                            logger.die(
                                f"Software spec {pkg} is not defined "
                                f"in environment {env_context}, but is "
                                f"required by the {mod_inst.name} modifier "
                                "definition"
                            )

                self.runner.deactivate()

        except ramble.util.command_runner.RunnerError as e:
            logger.die(e)

    register_phase(
        "software_configure",
        pipeline="setup",
        run_after=[
            "software_create_env",
            "software_install_requested_compilers",
        ],
    )

    def _software_configure(self, workspace, app_inst=None):
        """Concretize the spack environment for this experiment

        Perform spack's concretize step on the software environment generated
        for  this experiment.
        """

        logger.msg("Concretizing Spack environment")

        # See if we cached this already, and if so return
        env_path = self.app_inst.expander.env_path

        cache_tupl = ("concretize-env", env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug("{} already in cache.".format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            self.runner.set_dry_run(workspace.dry_run)

            self.runner.activate()

            env_concretized = self.runner.concretized

            if not env_concretized:
                self.runner.concretize()

        except ramble.util.command_runner.RunnerError as e:
            logger.die(e)

    register_phase(
        "evaluate_requirements",
        pipeline="setup",
        run_before=["make_experiments"],
    )

    def _evaluate_requirements(self, workspace, app_inst=None):
        """Evaluate all requirements for this experiment"""

        for mod_inst in self.app_inst._modifier_instances:
            for req in mod_inst.all_package_manager_requirements():
                expanded_req = {}
                for key, val in req.items():
                    expanded_req[key] = self.app_inst.expander.expand_var(val)
                self.runner.validate_command(**expanded_req)

    register_phase(
        "mirror_software", pipeline="mirror", run_after=["software_create_env"]
    )

    def _mirror_software(self, workspace, app_inst=None):
        """Mirror software source for this experiment using spack"""
        import re

        logger.msg("Mirroring software")

        # See if we cached this already, and if so return
        env_path = self.app_inst.expander.env_path
        if not env_path:
            raise ApplicationError("Ramble env_path is set to None.")

        cache_tupl = ("spack-mirror", env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug("{} already in cache.".format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            self.runner.set_dry_run(workspace.dry_run)
            self.runner.set_env(env_path)

            self.runner.activate()

            mirror_output = self.runner.mirror_environment(
                workspace.software_mirror_path
            )

            present = 0
            added = 0
            failed = 0

            present_regex = re.compile(r"\s+(?P<num>[0-9]+)\s+already present")
            present_match = present_regex.search(mirror_output)
            if present_match:
                present = int(present_match.group("num"))

            added_regex = re.compile(r"\s+(?P<num>[0-9]+)\s+added")
            added_match = added_regex.search(mirror_output)
            if added_match:
                added = int(added_match.group("num"))

            failed_regex = re.compile(r"\s+(?P<num>[0-9]+)\s+failed to fetch.")
            failed_match = failed_regex.search(mirror_output)
            if failed_match:
                failed = int(failed_match.group("num"))

            added_start = len(workspace.software_mirror_stats.new)
            for i in range(added_start, added_start + added):
                workspace.software_mirror_stats.new[i] = i

            present_start = len(workspace.software_mirror_stats.present)
            for i in range(present_start, present_start + present):
                workspace.software_mirror_stats.present[i] = i

            error_start = len(workspace.software_mirror_stats.errors)
            for i in range(error_start, error_start + failed):
                workspace.software_mirror_stats.errors.add(i)

        except ramble.util.command_runner.RunnerError as e:
            if self.environment_required():
                logger.die(e)
            pass

    register_phase("push_to_spack_cache", pipeline="pushtocache", run_after=[])

    def _push_to_spack_cache(self, workspace, app_inst=None):

        # Test if experiment requires an environment
        env_required = self.environment_required()

        env_path = self.app_inst.expander.env_path
        cache_tupl = ("push-to-cache", env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug("{} already pushed, skipping".format(cache_tupl))
            return
        else:
            workspace.add_to_cache(cache_tupl)

        try:
            self.runner.set_dry_run(workspace.dry_run)
            self.runner.set_env(env_path, require_exists=env_required)
            self.runner.activate()

            self.runner.push_to_spack_cache(workspace.spack_cache_path)

            self.runner.deactivate()
        except ramble.util.command_runner.RunnerError as e:
            if self.environment_required():
                logger.die(e)
            pass

    def populate_inventory(
        self, workspace, force_compute=False, require_exist=False
    ):
        """Add software environment information to hash inventory"""

        env_path = self.app_inst.expander.env_path
        self.runner.set_dry_run(workspace.dry_run)
        self.runner.set_env(env_path, require_exists=False)
        self.runner.activate()

        try:
            pkgman_version = self.runner.get_version()
        except ramble.util.command_runner.RunnerError:
            pkgman_version = "unknown"

        self.app_inst.hash_inventory["package_manager"].append(
            {
                "name": self.name,
                "version": pkgman_version,
                "digest": ramble.util.hashing.hash_string(pkgman_version),
            }
        )
        self.app_inst.hash_inventory["software"].append(
            {
                "name": self.runner.env_path.replace(
                    workspace.root + os.path.sep, ""
                ),
                "digest": self.runner.inventory_hash(),
            }
        )
        self.runner.deactivate()

    def _clean_hash_variables(self, workspace, variables):
        """Perform spack specific cleanup of variables before hashing"""

        self.runner.configure_env(
            self.app_inst.expander.expand_var_name(self.keywords.env_path)
        )
        self.runner.activate()

        for var in variables:
            if isinstance(variables[var], str):
                variables[var] = variables[var].replace(
                    "\n".join(self.runner.generate_source_command()),
                    "spack_source",
                )
                variables[var] = variables[var].replace(
                    "\n".join(self.runner.generate_activate_command()),
                    "spack_activate",
                )

        self.runner.deactivate()

        super()._clean_hash_variables(workspace, variables)

    register_phase(
        "deploy_artifacts",
        pipeline="pushdeployment",
        run_after=["software_create_env"],
    )

    def _deploy_artifacts(self, workspace, app_inst=None):
        super()._deploy_artifacts(workspace, app_inst=app_inst)
        env_path = self.app_inst.expander.env_path

        try:
            self.runner.set_dry_run(workspace.dry_run)
            self.runner.set_env(env_path)
            self.runner.activate()

            repo_path = os.path.join(workspace.named_deployment, "object_repo")

            for pkg, pkg_def in self.runner.package_definitions():
                pkg_dir_name = os.path.basename(os.path.dirname(pkg_def))
                pkg_dir = os.path.join(repo_path, "packages", pkg_dir_name)
                fs.mkdirp(pkg_dir)
                shutil.copyfile(pkg_def, os.path.join(pkg_dir, "package.py"))

            self.runner.deactivate()

        except ramble.util.command_runner.RunnerError as e:
            if self.environment_required():
                logger.die(e)
            pass

    register_builtin(
        "spack_source", required=True, depends_on=["builtin::env_vars"]
    )
    register_builtin(
        "spack_activate",
        required=True,
        depends_on=[
            "package_manager_builtin::spack-lightweight::spack_source"
        ],
    )
    register_builtin(
        "spack_deactivate",
        required=False,
        depends_on=[
            "package_manager_builtin::spack-lightweight::spack_source"
        ],
    )

    def spack_source(self):
        return self.runner.generate_source_command()

    def spack_activate(self):
        self.runner.configure_env(
            self.app_inst.expander.expand_var_name(self.keywords.env_path)
        )
        self.runner.activate()
        cmds = self.runner.generate_activate_command()
        self.runner.deactivate()
        return cmds

    def spack_deactivate(self):
        return self.runner.generate_deactivate_command()

    def get_spec_str(self, pkg, all_pkgs, compiler):
        """Return a spec string for the given pkg

        Args:
            pkg (RenderedPackage): Reference to a rendered package
            all_pkgs (dict): All related packages
            compiler (boolean): True if this pkg is used as a compiler
        """
        if compiler and pkg.compiler_spec:
            out_str = pkg.compiler_spec
        else:
            out_str = pkg.spec

        if compiler:
            return out_str

        if pkg.compiler in all_pkgs[self.name]:
            out_str += " %" + all_pkgs[self.name][pkg.compiler].spec_str(
                all_pkgs, compiler=True
            )
        elif pkg.compiler:
            out_str += f" (built with {pkg.compiler})"
        return out_str

    def _add_software_to_results(self, workspace, app_inst=None):
        """Augment the owning experiment's results with software stack information

        This is a registered phase by the base package manager class, so here
        we only override its base definition.

        Args:
            workspace (Workspace): A reference to the workspace that owns the
                                   current pipeline
            app_inst (Application): A reference to the application instance for
                                    the current experiment
        """
        if self._spec_prefix not in app_inst.result.software:
            app_inst.result.software[self._spec_prefix] = []

        package_list = app_inst.result.software[self._spec_prefix]

        self.runner.activate()
        for info in self.runner.package_provenance():
            package_list.append(info)
        self.runner.deactivate()


spack_namespace = "spack"

package_name_regex = re.compile(r"[\s-]*(?P<package_name>[\w][\w-]+).*")


class SpackRunner(ramble.util.command_runner.CommandRunner):
    """Runner for executing several spack commands

    The SpackRunner class is primarily used to manage spack environments
    for executing experiments under.

    This class provides methods for creating and manaving spack environments,
    and for ensuring required compilers are installed. It also provides a
    method for generating variables that can be used to ensure a spack env
    is loaded within an execution script.
    """

    env_key = "SPACK_ENV"

    global_config_name = "config:spack:global"
    install_config_name = "config:spack:install"
    compiler_find_config_name = "config:spack:compiler_find"
    buildcache_config_name = "config:spack:buildcache"
    concretize_config_name = "config:spack:concretize"
    env_create_config_name = "config:spack:env_create"

    env_create_args = ["env", "create", "-d", "."]

    compiler_find_args = ["compiler", "find"]

    _allowed_config_files = [
        "compilers.yaml",
        "concretizer.yaml",
        "mirrors.yaml",
        "repos.yaml",
        "packages.yaml",
        "modules.yaml",
        "config.yaml",
        "upstreams.yaml",
        "bootstrap.yaml",
        "spack.yaml",
        "spack_includes.yaml",
    ]

    def __init__(self, shell="bash", dry_run=False):
        """
        Ensure spack is found in the path, and setup some default variables.
        """

        super().__init__(
            name="spack", command="spack", shell=shell, dry_run=dry_run
        )
        self.spack = self.command

        # Add default arguments to spack command.
        # This allows us to inject custom config scope dirs
        # primarily for unit testing.
        global_args = ramble.config.get(f"{self.global_config_name}:flags")
        if global_args is not None:
            for arg in shlex.split(global_args):
                self.spack.add_default_arg(arg)

        self.spack_dir = os.path.dirname(os.path.dirname(self.spack.exe[0]))

        if self.shell == "bash":
            script = "setup-env.sh"
        elif self.shell == "csh":
            script = "setup-env.csh"
        elif self.shell == "fish":
            script = "setup-env.fish"
        self.source_script = os.path.join(
            self.spack_dir, "share", "spack", script
        )

        self.concretized = False
        self.hash = None
        self.env_path = None
        self.active = False
        self.compilers = []
        self.includes = []
        self.dry_run = dry_run
        self.compiler_config_dir = None
        self.configs = []
        self.configs_applied = False
        self.env_contents = []

        self.installer = self.spack.copy()
        self.installer.add_default_prefix(
            ramble.config.get(f"{self.install_config_name}:prefix")
        )
        self.installer.add_default_arg("install")

        self.concretizer = self.spack.copy()
        self.concretizer.add_default_prefix(
            ramble.config.get(f"{self.concretize_config_name}:prefix")
        )
        self.concretizer.add_default_arg("concretize")

    def get_version(self):
        """Get spack's version"""
        from ramble.main import get_git_hash
        import importlib.util

        version_spec = importlib.util.spec_from_file_location(
            "spack_version",
            os.path.join(
                self.spack_dir, "lib", "spack", "spack", "__init__.py"
            ),
        )
        version_mod = importlib.util.module_from_spec(version_spec)
        version_spec.loader.exec_module(version_mod)

        spack_version = version_mod.spack_version
        spack_hash = get_git_hash(path=self.spack_dir)

        if spack_hash:
            spack_version += f" ({spack_hash})"

        return spack_version

    def set_dry_run(self, dry_run=False):
        """
        Set the dry_run state of this spack runner
        """
        self.dry_run = dry_run

    def set_compiler_config_dir(self, path=None):
        """
        Set the config path to use when installing compilers
        """
        self.compiler_config_dir = path

    def set_env(self, env_path, require_exists=True):
        if require_exists:
            if not os.path.isdir(env_path) or not os.path.exists(
                os.path.join(env_path, "spack.yaml")
            ):
                logger.die(f"Path {env_path} is not a spack environment")

        self.env_path = env_path

    def generate_source_command(self, shell="bash"):
        """
        Generate a string to source spack into an environment
        """

        commands = [". %s" % self.source_script]

        return commands

    def generate_activate_command(self, shell="bash"):
        """
        Generate a string to activate a spack environment
        """

        commands = []
        if self.active:
            commands.append("spack env activate %s" % self.env_path)

        return commands

    def generate_deactivate_command(self, shell="bash"):
        """
        Generate a string to deactivate a spack environment
        """

        commands = []

        if self.active:
            commands.append("spack env deactivate")

        return commands

    def configure_env(self, path):
        """
        Configured the spack environment path for subsequent spack commands
        """

        # Ensure subsequent commands use the created env now.
        self.env_path = path

    def add_config(self, config):
        """
        Add a config option to this spack environment.
        """
        self.configs.append(config)

    def create_env(self, path, output=None, error=None):
        """
        Ensure a spack environment is created, and set the path to it within
        this runner.
        """
        if os.path.exists(path) and not os.path.isdir(path):
            raise ramble.util.command_runner.RunnerError(
                "Unable to create environment %s" % path
            )

        if not os.path.exists(path):
            fs.mkdirp(path)

        # Create a spack env
        if not os.path.exists(os.path.join(path, "spack.yaml")):
            env_create_flags = ramble.config.get(
                f"{self.env_create_config_name}:flags"
            )
            env_create_args = self.env_create_args.copy()
            if env_create_flags:
                for flag in shlex.split(env_create_flags):
                    env_create_args.append(flag)
            with fs.working_dir(path):
                self._run_command(self.spack, env_create_args)

        # Ensure subsequent commands use the created env now.
        self.env_path = path

    def load_compiler(self, spec):
        """
        Add commands to load a package to the executable
        """
        if self.shell == "bash":
            regex = re.compile(
                r"\A.*export (?P<var>[\S^=]+)=(?P<val>[\S]+);\Z"
            )
            shell_flag = "--sh"
        elif self.shell == "csh":
            regex = re.compile(
                r"\A.*setenv (?P<var>[\S^=]+) (?P<val>[\S]+);\Z"
            )
            shell_flag = "--csh"
        elif self.shell == "fish":
            regex = re.compile(
                r"\A.*set -gx (?P<var>[\S^=]+) (?P<val>[\S]+);\Z"
            )
            shell_flag = "--fish"
        else:
            raise ramble.util.command_runner.RunnerError(
                "Shell %s not supported" % self.shell
            )

        self._load_compiler_shell(spec, shell_flag, regex)

    def _load_compiler_shell(self, spec, shell_flag, regex):
        args = ["load", shell_flag, spec]

        load_cmds = self.execute(self.spack, args, return_output=True)

        if load_cmds is not None:
            for cmd in load_cmds.split("\n"):
                env_var = regex.match(cmd)
                if env_var:
                    self.spack.add_default_env(
                        env_var.group("var"), env_var.group("val")
                    )
                    self.installer.add_default_env(
                        env_var.group("var"), env_var.group("val")
                    )
                    self.concretizer.add_default_env(
                        env_var.group("var"), env_var.group("val")
                    )

    def install_compiler(self, spec):
        """
        Ensure a compiler is installed, before using it to install packages
        within an environment.

        This command always executes outside of an environment.

        If it is executed within an environment, then it adds the compiler to
        the list of environment specs. This can cause conflicts if an
        incompatible package is explicitly added to the environment later.

        Also, if it is added to an environment, sometimes it will cause a
        compiler to be installed multiple times with different base compilers.
        """
        active_env = None
        if self.active:
            active_env = self.spack.default_env[self.env_key]
            if self.env_key in self.spack.default_env:
                del self.spack.default_env[self.env_key]
                del self.installer.default_env[self.env_key]
                del self.concretizer.default_env[self.env_key]

        comp_info_args = []
        if self.compiler_config_dir:
            comp_info_args.extend(["-C", self.env_path])
        comp_info_args.extend(["compiler", "info", spec])

        compiler_find_flags = ramble.config.get(
            f"{self.compiler_find_config_name}:flags"
        )
        compiler_find_args = self.compiler_find_args.copy()
        if compiler_find_flags:
            for flag in shlex.split(compiler_find_flags):
                compiler_find_args.append(flag)
        if not self.dry_run:
            self._run_command(self.spack, compiler_find_args)

        try:
            self._cmd_start(self.spack, comp_info_args)
            self.spack(*comp_info_args, output=os.devnull, error=os.devnull)
            self._cmd_end(self.spack, comp_info_args)
            logger.msg(f"{spec} is already an available compiler")
            return
        except ProcessError:

            args = []

            install_flags = ramble.config.get(
                f"{self.install_config_name}:flags"
            )
            if install_flags is not None:
                for flag in shlex.split(install_flags):
                    args.append(flag)

            args.append(spec)

            self.execute(self.installer, args)

            self.load_compiler(spec)

            self.execute(self.spack, compiler_find_args)

            if not self.dry_run:
                self.compilers.append(spec)

                if self.active:
                    self.spack.add_default_env(self.env_key, active_env)
                    self.installer.add_default_env(self.env_key, active_env)
                    self.concretizer.add_default_env(self.env_key, active_env)

    def activate(self):
        """
        Ensure the spack environment is active in subsequent commands.
        """
        if not self.env_path:
            raise ramble.util.command_runner.NoPathRunnerError(
                "Environment runner has no path configured"
            )

        self.spack.add_default_env(self.env_key, self.env_path)
        self.installer.add_default_env(self.env_key, self.env_path)
        self.concretizer.add_default_env(self.env_key, self.env_path)

        self.active = True

    def deactivate(self):
        """
        Ensure the spack environment is not active in subsequent commands.
        """
        if not self.env_path:
            raise ramble.util.command_runner.NoPathRunnerError(
                "Environment runner has no path configured"
            )

        if self.active and self.env_key in self.spack.default_env.keys():
            del self.spack.default_env[self.env_key]
            del self.installer.default_env[self.env_key]
            del self.concretizer.default_env[self.env_key]
            self.active = False

    def _check_active(self):
        if not self.env_path:
            raise ramble.util.command_runner.NoPathRunnerError(
                "Environment runner has no path configured"
            )

        if not self.active:
            raise NoActiveEnvironmentError(
                "Runner has no active " + "environment to work with."
            )

    def add_spec(self, spec):
        """
        Add a spec to the spack environment.

        This command requires an active spack environment.
        """
        self._check_active()

        if spec not in self.env_contents:
            self.env_contents.append(spec)

    def added_packages(self):
        """
        Return a list of base package names that are added to an environment
        """
        self._check_active()

        args = ["find"]

        pkg_names = []

        all_packages = self._run_command(
            self.spack, args, return_output=True
        ).split("\n")
        for pkg in all_packages:
            match = package_name_regex.match(pkg)
            if match:
                pkg_names.append(match.group("package_name"))

        return pkg_names

    def add_include_file(self, include_file):
        """
        Add an include file to this spack environment.

        This file needs to be a config section supported by spack, otherwise
        spack will error. So, we validate against a list of supported sections.
        """

        file_name = os.path.basename(include_file)
        if file_name in self._allowed_config_files:
            self.includes.append(include_file)

    def apply_configs(self):
        """
        Add all defined configs to the environment
        """

        if self.configs_applied:
            return

        self._check_active()

        config_args = ["config", "add"]

        for config in self.configs:
            args = config_args.copy()
            args.append(config)

            self._run_command(self.spack, args)

        self.configs_applied = True

    def copy_from_external_env(self, env_name_or_path):
        """
        Copy an external spack environment file into the generated environment.

        env_name_or_path can be either:
         - Name of a named spack environment
         - Path to an external spack environment

         Sets self.concretized if a spack.lock file is found in the env

         Args:
         - env_name_or_path: Name or path to existing spack environment
        """

        self._check_active()

        named_location_args = ["location", "-e", env_name_or_path]

        # If the path doesn't exist, check if it's a named environment
        path = env_name_or_path
        if not os.path.exists(path):
            try:
                path = self._run_command(
                    self.spack, named_location_args, return_output=True
                )
            # If a named environment fails, copy directly from the path
            except ProcessError:
                raise InvalidExternalEnvironment(
                    f"{path} is not a spack environment."
                )

        found_lock = False

        lock_file = os.path.join(path, "spack.lock")
        if os.path.exists(lock_file):
            found_lock = True
            shutil.copyfile(
                lock_file, os.path.join(self.env_path, "spack.lock")
            )

        conf_file = os.path.join(path, "spack.yaml")
        if not os.path.exists(conf_file):
            raise InvalidExternalEnvironment(
                f"{path} is not a spack environment."
            )

        shutil.copyfile(conf_file, os.path.join(self.env_path, "spack.yaml"))

        if self.configs:
            self.apply_configs()

        self.concretized = found_lock

    def _env_file_dict(self):
        """Construct a dictionary with the env file contents in it"""
        env_file = syaml.syaml_dict()
        env_file[spack_namespace] = syaml.syaml_dict()
        env_file[spack_namespace]["concretizer"] = syaml.syaml_dict()
        env_file[spack_namespace]["concretizer"]["unify"] = True

        env_file[spack_namespace]["specs"] = syaml.syaml_list()
        # Ensure the specs content are consistently sorted.
        # Otherwise the hash checking may artificially miss due to ordering.
        env_file[spack_namespace]["specs"].extend(sorted(self.env_contents))

        env_file[spack_namespace]["include"] = self.includes

        return env_file

    def generate_env_file(self):
        """
        Generate a spack environment file
        """
        self._check_active()

        env_file = self._env_file_dict()

        spack_env_file = os.path.join(self.env_path, "spack.yaml")
        spack_lock_file = os.path.join(self.env_path, "spack.lock")

        # Check that a spack.yaml and spack.lock file exist already
        if os.path.exists(spack_env_file) and os.path.exists(spack_lock_file):
            existing_env_mtime = os.path.getmtime(spack_env_file)
            existing_lock_mtime = os.path.getmtime(spack_lock_file)

            # If the lock file was last modified after the yaml file...
            if existing_lock_mtime > existing_env_mtime:
                env_data = syaml.load_config(
                    syaml.dump_config(env_file, default_flow_style=False)
                )
                with open(spack_env_file, "r") as f:
                    existing_data = syaml.load_config(f)
                gen_env_hash = ramble.util.hashing.hash_json(env_data)
                existing_env_hash = ramble.util.hashing.hash_json(
                    existing_data
                )

                # If the yaml hash matches the new generated data hash...
                if gen_env_hash == existing_env_hash:
                    self.concretized = True
                    logger.msg(
                        f"Environment {self.env_path} will not be regenerated."
                    )
                    return

            if not self.concretized:
                logger.verbose(
                    f"Removing invalid spack lock file {spack_lock_file}"
                )
                fs.force_remove(spack_lock_file)

        spack_hash = self.inventory_hash()

        # Write spack.yaml to environment before concretizing, and its hash
        with open(os.path.join(self.env_path, "spack.yaml"), "w+") as f:
            syaml.dump_config(env_file, f, default_flow_style=False)

        with open(os.path.join(self.env_path, "ramble.hash"), "w+") as f:
            f.write(spack_hash)

        if self.configs:
            self.apply_configs()

    def concretize(self):
        """
        Concretize a spack environment.

        This command requires an active spack environment.
        """
        self._check_active()

        if self.concretized:
            logger.msg(
                f"Environment {self.env_path} is already concretized. Skipping concretize..."
            )
            return

        concretize_flags = ramble.config.get(
            f"{self.concretize_config_name}:flags"
        )

        args = []
        if concretize_flags is not None:
            args.extend(shlex.split(concretize_flags))

        self.execute(self.concretizer, args)

        self.concretized = True

    def inventory_hash(self):
        """
        Create a hash of the spack.lock file for ramble inventory purposes

        This command requires an active spack environment.
        """
        self._check_active()

        env_data = syaml.load_config(
            syaml.dump_config(self._env_file_dict(), default_flow_style=False)
        )
        self.hash = ramble.util.hashing.hash_json(env_data)

        return self.hash

    def install(self):
        """
        Install spack packages that have been added to an environment.

        This command requires an active spack environment.
        """
        self._check_active()

        install_flags = ramble.config.get(f"{self.install_config_name}:flags")

        args = []

        if install_flags is not None:
            args.extend(shlex.split(install_flags))

        self.execute(self.installer, args)

    def get_package_path(self, package_spec):
        """Return the installation directory for a package"""
        name_regex = re.compile(r"(?P<name>[a-zA-Z0-9\-_]+).*")
        loc_args = ["location", "-i"]
        loc_args.extend(shlex.split(package_spec))

        name_args = ["find", "--format={name}"]
        name_args.extend(shlex.split(package_spec))

        name = self.execute(self.spack, name_args, return_output=True)
        location = self.execute(self.spack, loc_args, return_output=True)

        if name is None:
            name = shlex.split(package_spec)[0]
            name_match = name_regex.match(name)
            if name_match:
                name = name_match.group("name")
        else:
            # Remove newlines and whitespace from name
            name = name.replace("\n", "").strip()

        if location is None:
            location = os.path.join(
                "dry-run", "path", "to", shlex.split(package_spec)[0]
            )
        else:
            # Remove newlines and whitespace from location
            location = location.replace("\n", "").strip()

        return (name, location)

    def mirror_environment(self, mirror_path):
        """Create a spack mirror from the activated environment"""
        self._check_active()

        args = [
            "mirror",
            "create",
            "--all",  # All packages in the environment
            "-D",  # Include dependencies
            "-d",
            mirror_path,
        ]

        out_str = self.execute(self.spack, args, return_output=True)

        if out_str is None:
            return """
  %-4d already present
  %-4d added
  %-4d failed to fetch.""" % (
                0,
                0,
                0,
            )

        return out_str.strip()

    def get_env_hash_list(self):
        self._check_active()
        args = ["find", "--format", "/{hash}"]
        output = (
            self._run_command(self.spack, args, return_output=True)
            .strip()
            .replace("\n", " ")
        )
        return output

    def push_to_spack_cache(self, spack_cache_path):
        """Push packages for a given env to the spack cache"""
        self._check_active()

        hash_list = self.get_env_hash_list()

        args = ["buildcache", "push"]
        user_flags = ramble.config.get(f"{self.buildcache_config_name}:flags")

        logger.debug(f"Running with user flags: {user_flags}")

        if user_flags is not None:
            args.extend(shlex.split(user_flags))

        args.extend([spack_cache_path, hash_list])

        out_str = self.execute(self.spack, args, return_output=True)

        if out_str is None:
            out_str = "None"

        return out_str.strip()

    def validate_command(
        self,
        command="",
        validation_type="not_empty",
        package_manager="spack",
        regex=None,
    ):
        regex_validations = ["contains_regex", "does_not_contain_regex"]

        args = command.split()

        compiled_regex = None
        if validation_type in regex_validations and regex:
            compiled_regex = re.compile(regex)

        output = self.execute(self.spack, args, return_output=True)

        if output is not None:
            logger.debug(" Validation output:")
            logger.debug(output)
            if validation_type == "empty":
                if output != "":
                    self._raise_validation_error(command, validation_type)
            elif validation_type == "not_empty":
                if output == "":
                    self._raise_validation_error(command, validation_type)
            elif validation_type == "contains_regex":
                found = False
                for line in output.split("\n"):
                    if compiled_regex.match(line):
                        found = True
                if not found:
                    self._raise_validation_error(command, validation_type)
            elif validation_type == "does_not_contain_regex":
                for line in output.split("\n"):
                    if compiled_regex.match(line):
                        self._raise_validation_error(command, validation_type)

    def package_definitions(self):
        """For each package in this environment, yield the path to its application.py file"""
        package_def_name = "package.py"
        location_args = ["location", "-p"]

        self._check_active()

        for pkg in self.env_contents:
            args = location_args.copy()
            args.append(pkg)
            path = self.execute(self.spack, args, return_output=True)
            if path is not None:
                yield pkg, os.path.join(path, package_def_name)

    def _package_dict_from_str(self, in_str):
        """Construct a package dictionary from a comma delimited spec string

        Args:
            in_str (str): Comma delimited string from spack about a package spec.
                          It is assumed to be of the format:
                          {name},{version},{compiler_name},{compiler_version},{variants}

        Returns:
            (dict): Dictionary representing the package information
        """
        parts = in_str.split(",")

        info_dict = {
            "name": "",
            "version": "",
            "compiler": "",
            "compiler_version": "",
            "variants": "",
        }

        if len(parts) >= 1:
            # Remove status markers
            name = (
                parts[0]
                .replace("[+]", "")
                .replace(" - ", "")
                .replace("[e]", "")
                .strip()
            )

            info_dict["name"] = name

        if len(parts) >= 2:
            info_dict["version"] = parts[1]

        if len(parts) >= 3:
            info_dict["compiler"] = parts[2]

        if len(parts) >= 4:
            info_dict["compiler_version"] = parts[3]

        if len(parts) >= 5:
            info_dict["variants"] = ",".join(parts[4:]).strip()

        if info_dict["name"]:
            return info_dict
        return None

    def package_provenance(self):
        """Iterator over package information dictionaries

        Call spack to determine the package information in the current
        environment. Yield each valid package dictionary.

        Yields:
            (dict): Package information dictionary
        """
        find_args = [
            "find",
            '--format="{name},{version},{compiler.name},{compiler.version},{variants}"',
            "-c",
        ]

        lock_file = os.path.join(self.env_path, "spack.lock")
        if os.path.exists(lock_file):
            all_info = self.execute(
                self.spack, find_args, return_output=True
            ).replace('"', "")

            if all_info:
                for info in all_info.split("\n"):
                    info_dict = self._package_dict_from_str(info)

                    if info_dict:
                        yield info_dict


class NoActiveEnvironmentError(ramble.util.command_runner.RunnerError):
    """Raised when an environment command is executed without an active
    environment."""


class InvalidExternalEnvironment(ramble.util.command_runner.RunnerError):
    """Raised when an invalid external spack environment is passed in"""

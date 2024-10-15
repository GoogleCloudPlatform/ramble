# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import re
import shutil
import sys

from ramble.application import ApplicationError
from ramble.pkgmankit import *

import ramble.config
from ramble.error import RambleError
from ramble.util.executable import which
from ramble.util.hashing import hash_file, hash_string
from ramble.util.logger import logger
from ramble.util.shell_utils import source_str

from spack.util.executable import Executable
import llnl.util.filesystem as fs


class Pip(PackageManagerBase):
    """Pip package manager class definition"""

    name = "pip"

    _spec_prefix = "pip"

    def __init__(self, file_path):
        super().__init__(file_path)

        self.runner = PipRunner()

    register_builtin(
        "pip_activate", required=True, depends_on=["builtin::env_vars"]
    )

    def pip_activate(self):
        self.runner.configure_env(self.app_inst.expander.env_path)
        return self.runner.generate_activate_command()

    register_builtin(
        "pip_deactivate",
        required=False,
        depends_on=["pip_activate"],
    )

    def pip_deactivate(self):
        return self.runner.generate_deactivate_command()

    register_phase("software_create_env", pipeline="setup")

    def _software_create_env(self, workspace, app_inst=None):
        """Create the virtual env for the experiment"""

        logger.msg("Creating venv + pip environment")

        env_path = self.app_inst.expander.env_path
        if not env_path:
            raise ApplicationError("Ramble env_path is set to None")

        cache_tupl = ("pip-env", env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug("{cache_tupl} already in cache")
            return
        else:
            workspace.add_to_cache(cache_tupl)

        self.runner.set_dry_run(workspace.dry_run)
        self.runner.create_env(env_path)

        env_context = self.app_inst.expander.expand_var_name(
            self.keywords.env_name
        )
        require_env = self.environment_required()
        software_envs = workspace.software_environments
        software_env = software_envs.render_environment(
            env_context, self.app_inst.expander, self, require=require_env
        )
        if software_env:
            if isinstance(software_env, ExternalEnvironment):
                self.runner.copy_from_external_env(software_env.external_env)
            else:
                for pkg_spec in software_envs.package_specs_for_environment(
                    software_env
                ):
                    self.runner.add_spec(pkg_spec)
                self.runner.generate_requirement_file()

    register_phase(
        "software_install", pipeline="setup", run_after=["software_create_env"]
    )

    def _software_install(self, workspace, app_inst=None):
        """Install packages using pip"""
        logger.msg("Installing packages")

        env_path = self.app_inst.expander.env_path
        if not env_path:
            raise ApplicationError("Ramble env_path is set to None")

        cache_tupl = ("pip-install", env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug("{cache_tupl} already in cache")
            return
        else:
            workspace.add_to_cache(cache_tupl)

        env_context = self.app_inst.expander.expand_var_name(
            self.keywords.env_name
        )
        if self.environment_required():
            self.runner.set_dry_run(workspace.dry_run)
            self.runner.configure_env(env_path)
            self.runner.install()

            installed_pkgs = self.runner.installed_packages()
            for pkg in self.app_inst.required_packages.keys():
                if pkg not in installed_pkgs:
                    logger.die(
                        f"Package {pkg} is not installed "
                        f"in environment {env_context}, but is "
                        f"required by the {self.name} application "
                        "definition"
                    )

            for mod_inst in self.app_inst._modifier_instances:
                for pkg in mod_inst.required_packages.keys():
                    if pkg not in installed_pkgs:
                        logger.die(
                            f"Package {pkg} is not installed "
                            f"in environment {env_context}, but is "
                            f"required by the {mod_inst.name} modifier "
                            "definition"
                        )

    register_phase(
        "define_package_paths",
        pipeline="setup",
        run_after=["software_install"],
        run_before=["make_experiments"],
    )

    def _define_package_paths(self, workspace, app_inst=None):
        """Define variables containing the path to pip packages"""

        logger.msg("Defining pip package path variables")

        env_path = self.app_inst.expander.env_path
        if not env_path:
            raise ApplicationError("Ramble env_path is set to None")

        if self.environment_required():
            self.runner.set_dry_run(workspace.dry_run)
            self.runner.configure_env(env_path)
            self.runner.define_path_vars(
                self.app_inst, workspace.pkg_path_cache[self.name]
            )

    def get_spec_str(self, pkg, all_pkgs, compiler):
        """Return a spec string for the given pkg

        Args:
            pkg (RenderedPackage): Reference to a rendered package
            all_pkgs (dict): All related packages
            compiler (boolean): True if this pkg is used as a compiler
        """
        return pkg.spec

    def populate_inventory(
        self, workspace, force_compute=False, require_exist=False
    ):
        """Add software environment information to hash inventory"""

        env_path = self.app_inst.expander.env_path
        self.runner.set_dry_run(workspace.dry_run)
        self.runner.configure_env(env_path)

        pkgman_version = self.runner.get_version()

        self.app_inst.hash_inventory["package_manager"].append(
            {
                "name": self.name,
                "version": pkgman_version,
                "digest": hash_string(pkgman_version),
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

    register_phase("warn_mirror_support", pipeline="mirror")

    def _warn_mirror_support(self, workspace, app_inst=None):
        del workspace, app_inst  # unused arguments
        logger.warn(
            f"Mirroring software using {self.name} is not currently supported. "
            "If a software mirror is required, it needs to be set up outside of Ramble"
        )

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

        env_path = self.app_inst.expander.env_path
        self.runner.set_dry_run(workspace.dry_run)
        self.runner.configure_env(env_path)

        if self._spec_prefix not in app_inst.result.software:
            app_inst.result.software[self._spec_prefix] = []

        package_list = app_inst.result.software[self._spec_prefix]

        for info in self.runner.package_provenance():
            package_list.append(info)


package_name_regex = re.compile(
    r"\s*(?P<pkg_name>[A-Z0-9][A-Z0-9._-]*[A-Z0-9]|[A-Z0-9]).*", re.IGNORECASE
)


def _extract_pkg_name(pkg_spec):
    """Best-effort to extract pkg name from spec

    This is only used by the runner for dry-run cases.
    It only handles name-based specifier.
    """

    match = package_name_regex.match(pkg_spec)
    return match.group("pkg_name") if match else None


class PipRunner:
    """Runner for executing pip+venv commands."""

    _venv_name = ".venv"
    _requirement_file_name = "requirements.txt"
    _lock_file_name = "requirements.lock"

    install_config_name = "config:pip:install"

    def __init__(self, dry_run=False):
        self.bs_python = None
        self.env_path = None
        self.configs = []
        self.dry_run = dry_run
        self.specs = set()
        self.installed = False

    def configure_env(self, path):
        """Configure the venv path for subsequent commands"""
        self.env_path = path

    def set_dry_run(self, dry_run=False):
        """Set the dry_run state of this pip runner"""
        self.dry_run = dry_run

    def create_env(self, env_path):
        """Ensure a venv environment is created"""
        if os.path.exists(env_path) and not os.path.isdir(env_path):
            raise RunnerError(f"Unable to create environment {env_path}")

        if not os.path.exists(env_path):
            fs.mkdirp(env_path)

        if not self.dry_run:
            if not os.path.exists(os.path.join(env_path, self._venv_name)):
                bs_python = self.get_bootstrap_python()
                bs_python(
                    "-m", "venv", os.path.join(env_path, self._venv_name)
                )

        # Ensure subsequent commands use the created env now.
        self.env_path = env_path

    def _get_venv_python(self):
        if self.dry_run:
            return self.get_bootstrap_python().copy()
        return Executable(
            os.path.join(self.env_path, self._venv_name, "bin", "python")
        )

    def install(self):
        """Invoke pip install"""
        self._check_env_configured()
        if self.installed:
            logger.debug("Installation already done, skipping")
            return
        req_file = os.path.join(self.env_path, self._requirement_file_name)
        if not os.path.exists(req_file):
            raise RunnerError(f"{req_file} does not exist")
        installer = self._get_venv_python()
        installer.add_default_arg("-m")
        installer.add_default_arg("pip")
        installer_flags = ramble.config.get(
            f"{self.install_config_name}:flags"
        )
        install_args = ["install", "-r", req_file, *installer_flags]
        freeze_args = ["freeze", "-r", req_file]
        if self.dry_run:
            self._dry_run_print(installer, install_args)
            self._dry_run_print(installer, freeze_args)
        else:
            installer(*install_args)
            lock_file = os.path.join(self.env_path, self._lock_file_name)
            with open(lock_file, "w") as f:
                installer(*freeze_args, output=f)
        self.installed = True

    def get_bootstrap_python(self):
        if not self.bs_python:
            # Set up python for bootstrapping.
            # Simply use the same interpreter as the current Ramble.
            self.bs_python = which(sys.executable, required=True)
        return self.bs_python

    def _get_activate_script_path(self):
        return os.path.join(self.env_path, self._venv_name, "bin", "activate")

    def _check_env_configured(self):
        """Check if virtual env is configured"""
        if not self.env_path:
            raise RunnerError("env_path is not configured")
        if self.dry_run:
            return
        script_path = self._get_activate_script_path()
        if not os.path.exists(script_path):
            raise RunnerError("virtual env is not configured")

    def generate_activate_command(self):
        """Generate a command to activate a virtual env"""
        shell = ramble.config.get("config:shell")
        return [f"{source_str(shell)} {self._get_activate_script_path()}"]

    def generate_deactivate_command(self):
        """Generate a command to deactivate a virtual env"""
        return ["deactivate"]

    def _generate_requirement_content(self):
        contents = os.linesep.join(sorted(self.specs))
        contents += os.linesep
        return contents

    def generate_requirement_file(self):
        """Generate a requirements.txt file"""
        self._check_env_configured()
        contents = self._generate_requirement_content()
        req_file = os.path.join(self.env_path, self._requirement_file_name)
        lock_file = os.path.join(self.env_path, self._lock_file_name)
        if os.path.exists(req_file) and os.path.exists(lock_file):
            existing_req_mtime = os.path.getmtime(req_file)
            existing_lock_mtime = os.path.getmtime(lock_file)
            if existing_lock_mtime >= existing_req_mtime:
                with open(req_file, "r") as f:
                    if f.read() == contents:
                        self.installed = True
                        logger.debug("requirement file already up-to-date")
                        return
        with open(req_file, "w") as f:
            f.write(contents)

    def copy_from_external_env(self, external_env_path):
        """Copy requirements from an external env

        This will attempt `pip freeze` from the given external env_path
        and writes the output requirements.txt to the current env_path.
        """
        self._check_env_configured()
        dest = os.path.join(self.env_path, self._requirement_file_name)
        # When a file is given, assume it's a requirements.txt.
        if os.path.isfile(external_env_path):
            logger.msg(
                f"Treat {external_env_path} as an externally defined requirements.txt file"
            )
            shutil.copyfile(external_env_path, dest)
            return
        # Assume the given external_env_path already points to a venv path,
        # If not, also attempt path/.venv/.
        maybe_paths = ["", self._venv_name]
        ext_python_path = None
        for p in maybe_paths:
            exe_path = os.path.join(external_env_path, p, "bin", "python")
            if os.path.exists(exe_path):
                ext_python_path = exe_path
                break
        if not ext_python_path:
            raise RunnerError(
                f"The given external env path {external_env_path} does not point to a valid venv "
                "or requirements.txt file"
            )
        ext_python = Executable(ext_python_path)
        with open(dest, "w") as f:
            ext_python("-m", "pip", "freeze", output=f)

    def define_path_vars(self, app_inst, cache):
        """Define path variables"""
        self._check_env_configured()
        if self.dry_run:
            return
        lock_file = os.path.join(self.env_path, self._lock_file_name)
        if not lock_file:
            raise RunnerError(f"Lock file {lock_file} is missing")
        pkgs = []
        with open(lock_file, "r") as f:
            for line in f.readlines():
                # pip freeze generates such a comment, which serves as a divider
                # for packages that are added as deps of the ones defined directly.
                # This is a crude way to avoid defining path vars for
                # packages that are not defined in ramble config.
                if "added by pip freeze" in line:
                    break
                if "==" in line:
                    pkgs.append(line.split("==")[0].strip())
        unresolved_pkgs = []
        for pkg in pkgs:
            if pkg in cache:
                pkg_path = cache.get(pkg)
                if f"{pkg}_path" not in app_inst.variables:
                    # Intentionally not define the deprecated `pkg` variable
                    app_inst.define_variable(f"{pkg}_path", pkg_path)
                else:
                    logger.msg(
                        f"Variable {pkg}_path defined. "
                        + "Skipping extraction from pip"
                    )
            else:
                unresolved_pkgs.append(pkg)
        if not unresolved_pkgs:
            return

        logger.debug("Resolving package paths using pip")
        exe = self._get_venv_python()
        exe.add_default_arg("-m")
        exe.add_default_arg("pip")
        exe.add_default_arg("show")
        for pkg in unresolved_pkgs:
            pkg_info_raw = exe(pkg, output=str)
            pkg_path = None
            for line in pkg_info_raw.split(os.linesep):
                info = line.split(":")
                if info[0].strip() == "Location":
                    pkg_path = info[1].strip()
            if not pkg_path:
                raise RunnerError(
                    f"Failed to find installed path for package {pkg}"
                )
            cache[pkg] = pkg_path
            if f"{pkg}_path" not in app_inst.variables:
                app_inst.define_variable(f"{pkg}_path", pkg_path)
            else:
                logger.msg(
                    f"Variable {pkg}_path defined. "
                    + "Skipping extraction from pip"
                )

    def add_spec(self, spec):
        """Add a package spec to the pip environment"""
        self._check_env_configured()
        self.specs.add(spec)

    def get_version(self):
        if self.dry_run:
            return "unknown"
        exe = self._get_venv_python()
        out = exe("-m", "pip", "--version", output=str)
        match = re.search(r"pip (?P<version>[\d.]+) from", out).group(
            "version"
        )
        return match

    def inventory_hash(self):
        """Create a hash for ramble inventory purposes"""
        self._check_env_configured()
        if self.dry_run:
            return hash_string(self._generate_requirement_content())
        else:
            return hash_file(os.path.join(self.env_path, self._lock_file_name))

    def installed_packages(self):
        """Return a set of installed packages based on the lock file"""
        self._check_env_configured()
        pkgs = set()
        if self.dry_run:
            for spec in self.specs:
                pkg_name = _extract_pkg_name(spec)
                if pkg_name:
                    pkgs.add(pkg_name)
        else:
            with open(os.path.join(self.env_path, self._lock_file_name)) as f:
                reqs = f.readlines()
                for req in reqs:
                    if "==" in req:
                        pkgs.add(req.split("==")[0].strip())
        return pkgs

    def _package_dict_from_str(self, in_str):
        """Construct a package dictionary from a package string

        Args:
            in_str (str): String representing a package, as output from `pip freeze`

        Returns:
            (dict): Dictionary representing the package information
        """

        if not in_str:
            return None

        parts = in_str.replace("\n", "").split("==")

        if len(parts) <= 1:
            return None

        version = parts[1]

        if "[" in parts[0]:
            name_parts = parts[0].replace("]", "").split("[")
            name = name_parts[0]
            variants = name_parts[1]
        else:
            name = parts[0]
            variants = ""

        info_dict = {"name": name, "version": version, "variants": variants}

        return info_dict

    def package_provenance(self):
        """Iterator over package information dictionaries

        Examine the package definitions in the environment lock file. Yield
        each valid package dictionary created from lines in the lock file.

        Yields:
            (dict): Package information dictionary
        """

        lock_file = os.path.join(self.env_path, self._lock_file_name)

        if os.path.exists(lock_file):
            with open(lock_file) as f:
                for line in f.readlines():
                    info_dict = self._package_dict_from_str(
                        line.replace("\n", "")
                    )

                    if info_dict:
                        yield info_dict

    def _dry_run_print(self, executable, args):
        logger.msg(f"DRY-RUN: would run {executable}")
        logger.msg(f"         with args: {args}")


class RunnerError(RambleError):
    """Raised when a problem occurs with a pip+venv environment"""

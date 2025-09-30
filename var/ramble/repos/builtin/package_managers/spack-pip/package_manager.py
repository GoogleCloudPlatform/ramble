# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.util.hashing import hash_string
from ramble.util.logger import logger
from ramble.pkgmankit import *
from ramble.pkg_man.builtin.spack import Spack
from ramble.pkg_man.builtin.spack_lightweight import SpackRunner
from ramble.pkg_man.builtin.pip import Pip, PipRunner
from ramble.util.command_runner import CommandRunner
from spack.util.executable import Executable


class SpackPip(Spack, Pip):

    name = "spack-pip"

    archive_pattern("{env_path}/spack.yaml")
    archive_pattern("{env_path}/spack.lock")
    archive_pattern(os.path.join("{env_path}", "requirements.txt"))
    archive_pattern(os.path.join("{env_path}", "requirements.lock"))

    def __init__(self, file_path):
        # Let parents run first; then we enforce our runner.
        super().__init__(file_path)
        # Force-correct whatever parents may have put in _runner:
        if not isinstance(getattr(self, "_runner", None), SpackPipRunner):
            self._runner = SpackPipRunner()

    @property
    def runner(self):
        r = getattr(self, "_runner", None)
        if not isinstance(r, SpackPipRunner):
            r = SpackPipRunner()
            self._runner = r
        return r

    @runner.setter
    def runner(self, value):
        # Base classes may set runner=None; accept and ignore that.
        if value is None:
            return
        # Only allow our combined runner type; otherwise replace.
        if isinstance(value, SpackPipRunner):
            self._runner = value
        else:
            logger.debug(f"Replacing non-combined runner {type(value)} with SpackPipRunner")
            self._runner = SpackPipRunner()

    register_phase(
        "software_create_env",
        pipeline="mirror",
        run_before=["software_configure"],
    )

    def _software_create_env_pip(self, workspace, app_inst=None):
        """Create the virtual env for the experiment"""

        logger.msg("Creating venv + pip environment")

        env_path = app_inst.expander.env_path
        if not env_path:
            raise ApplicationError("Ramble env_path is set to None")

        cache_tupl = ("pip-env", env_path)
        if workspace.check_cache(cache_tupl):
            logger.debug("{cache_tupl} already in cache")
            return
        else:
            workspace.add_to_cache(cache_tupl)

        self.runner.set_dry_run(workspace.dry_run)

        env_context = app_inst.expander.expand_var_name(self.keywords.env_name)
        require_env = self.environment_required
        software_envs = workspace.software_environments
        software_env = software_envs.render_environment(
            env_context, app_inst.expander, self, require=require_env
        )
        if software_env:
            if isinstance(software_env, ExternalEnvironment):
                self.runner.copy_from_external_env(software_env.external_env)
            else:
                for pkg_spec in software_envs.package_specs_for_environment(
                    software_env
                ):
                    self.runner.pip_add_spec(pkg_spec)
                self.runner.generate_requirement_file()

    def _software_create_env(self, workspace, app_inst=None):
        """Create both the Spack environment and the Pip venv."""
        Spack._software_create_env(self, workspace, app_inst)
        self._software_create_env_pip(workspace, app_inst)

    register_phase(
        "software_configure", pipeline="mirror", run_before=["mirror_software"]
    )

    register_phase(
        "software_install",
        pipeline="setup",
        run_after=["software_configure"],
        run_before=["evaluate_requirements"],
    )

    def _software_install(self, workspace, app_inst=None):
        """Install packages from spack package and install pip_spec"""
        Spack._software_install(self, workspace, app_inst)
        Pip._software_install(self, workspace, app_inst)

    register_phase(
        "define_package_paths",
        pipeline="setup",
        run_after=["software_install", "evaluate_requirements"],
        run_before=["make_experiments"],
    )

    def _define_package_paths(self, workspace, app_inst=None):
        Spack._define_package_paths(self, workspace, app_inst)
        Pip._define_package_paths(self, workspace, app_inst)
        
    register_builtin(
        "spack_activate",
        required=True,
    )
    register_builtin(
        "spack_deactivate",
        required=False,
    )

    # Shadow parent's builtin so it doesn't emit `. setup-env.sh`
    def spack_source(self):
        return []

class _CRShim(CommandRunner):
    def __init__(self, name=None, command=None, shell=None, dry_run=False, **kwargs):
        CommandRunner.__init__(self, name=name,
                               command=command,
                               shell=shell,
                               dry_run=dry_run)

class SpackPipRunner(SpackRunner, _CRShim, PipRunner):
    """
    A combined runner that manages BOTH a Spack environment and a Pip venv
    under the same env_path.

    Notes:
      - Use create_env() to create both the Spack env and the Pip venv.
      - install() installs Spack packages first, then Pip requirements (if present).
      - generate_activate_command() returns a list of shell commands to activate both.
      - add_spec() tries to auto-route to Spack or Pip; you can force with
        spack_add_spec() / pip_add_spec() for full control.
    """

    def __init__(self, shell="bash", dry_run=False):
        SpackRunner.__init__(self, shell=shell, dry_run=dry_run)
        PipRunner.__init__(self, dry_run=dry_run)
        self._spack_specs = []
        self._pip_specs = set()
        self._generated_cmds = False
        self.name = "spack-pip"

    # --- helpers for Spack view python ---
    def _spack_view_bin(self):
        return os.path.join(self.env_path or "", "ramble", "bin")

    def _spack_view_python_path(self):
        return os.path.join(self._spack_view_bin(), "python")

    def _spack_view_exists(self):
        p = self._spack_view_python_path()
        return bool(self.env_path) and os.path.exists(p)

    def _get_venv_python(self):
        # Spack view must exist
        return Executable(self._spack_view_python_path())

    def create_env(self, path):
        SpackRunner.create_env(self, path)

    # Activation: if Spack view exists, we DO NOT source .venv; we just ensure Spack is active
    def generate_activate_command(self, shell="bash"):
        if self._generated_cmds:
            return []
        self._generated_cmds = True
        cmds = []
        # Source Spack and activate the Spack env first
        cmds.extend(self.generate_source_command(shell=shell))
        cmds.extend(SpackRunner.generate_activate_command(self, shell=shell))
        return cmds

    # Deactivation: nothing for Spack view; fall back to pip deactivate if we used a venv
    def generate_deactivate_command(self, shell="bash"):
        cmds = []
        if not self._spack_view_exists():
            cmds.extend(PipRunner.generate_deactivate_command(self))
        cmds.extend(SpackRunner.generate_deactivate_command(self, shell=shell))
        return cmds

    # TODO: This overrides the pip check which will fail, because we want spack to create the venv, otherwise spack will complain if venv already exists if pip makes it.
    def _check_env_configured(self):
        logger.warn("Not checking if env configured")
        return

    def configure_env(self, path):
        """Point BOTH runners at the same env_path directory."""
        SpackRunner.configure_env(self, path)
        PipRunner.configure_env(self, path)

    def set_env(self, env_path, require_exists=True):
        """Spack-side set_env; Pip doesn't need a 'require_exists' check."""
        SpackRunner.set_env(self, env_path, require_exists=require_exists)
        PipRunner.configure_env(self, env_path)

    def generate_source_command(self, shell="bash"):
        """Source Spack setup-env script (Pip has nothing analogous)."""
        return SpackRunner.generate_source_command(self, shell=shell)

    def activate(self):
        """Mark Spack env active (for spack CLI)."""
        SpackRunner.activate(self)

    def deactivate(self):
        """Undo Spack activation marker."""
        SpackRunner.deactivate(self)

    def spack_add_spec(self, spec):
        """Force-add a Spack spec (requires active Spack env)."""
        SpackRunner.add_spec(self, spec)
        self._spack_specs.append(spec)

    def pip_add_spec(self, spec):
        """Force-add a Pip spec (writes to requirements.txt later)."""
        PipRunner.add_spec(self, spec)
        self._pip_specs.add(spec)

    # TODO: replace with explicit calls to either pip_add_spec or spack_add_spec
    def add_spec(self, spec):
        """
        Heuristically route to Pip or Spack:
          - Pip if '==', '://', or '.whl' is present (typical pip forms)
          - Otherwise Spack
        If you need total control, call spack_add_spec() / pip_add_spec() instead.
        """
        s = str(spec)
        is_pipish = ("==" in s) or ("://" in s) or s.strip().endswith(".whl")
        if is_pipish:
            return self.pip_add_spec(spec)
        else:
            return self.spack_add_spec(spec)

    def concretize(self):
        """Concretize Spack environment only."""
        SpackRunner.concretize(self)

    def apply_configs(self):
        """Apply Spack env configs only (no-op if already applied)."""
        SpackRunner.apply_configs(self)

    def generate_env_file(self):
        """Generate spack.yaml (Spack side)."""
        SpackRunner.generate_env_file(self)

    def pip_install_via_parent(self):
        saved = getattr(self, "install_config_name", None)
        try:
            # make sure PipRunner.install() sees pip's namespace
            self.install_config_name = PipRunner.install_config_name
            PipRunner.install(self)
        finally:
            # restore so SpackRunner methods still see spack's namespace
            if saved is not None:
                self.install_config_name = saved

    def install(self):
        """
        Install Spack packages first (so toolchains/libs are present),
        then install Pip requirements if requirements.txt exists.
        """
        SpackRunner.install(self)
        self.pip_install_via_parent()

    def get_version(self):
        """Return a combined version string for diagnostics."""
        try:
            spv = SpackRunner.get_version(self)
        except Exception:
            spv = "unknown"
        try:
            piv = PipRunner.get_version(self)
        except Exception:
            piv = "unknown"
        return f"spack={spv}; pip={piv}"

    def inventory_hash(self):
        """Combine Spack and Pip hashes for inventory."""
        try:
            spack_hash = SpackRunner.inventory_hash(self)
        except Exception:
            spack_hash = ""
        try:
            pip_hash = PipRunner.inventory_hash(self)
        except Exception:
            pip_hash = ""
        return hash_string(spack_hash + "|" + pip_hash)

    # Keep Pip's installed_packages() contract (used by Pip manager code).
    def installed_packages(self):
        """Return Pip-installed package names (Spack has different semantics)."""
        return PipRunner.installed_packages(self)

    # Provenance: yield both Spack and Pip entries.
    def package_provenance(self):
        """Yield software info from BOTH ecosystems."""
        # Spack first (if lock exists)
        for info in SpackRunner.package_provenance(self):
            yield info
        # Then Pip (if lock exists)
        for info in PipRunner.package_provenance(self):
            yield info
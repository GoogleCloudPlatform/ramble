# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for package manager definitions"""

import os
from typing import List

import ramble.definitions.families
import ramble.util.class_attributes
import ramble.util.directives
import ramble.variants
from ramble.language.package_manager_language import PackageManagerMeta
from ramble.language.shared_language import SharedMeta, register_phase
from ramble.util import format
from ramble.util.naming import NS_SEPARATOR

import spack.util.naming


class PackageManagerBase(metaclass=PackageManagerMeta):
    name = None
    origin_type = "package_manager"
    _builtin_name = NS_SEPARATOR.join(
        ("package_manager_builtin", "{obj_name}", "{name}")
    )
    _language_classes = [PackageManagerMeta, SharedMeta]
    _pipelines = [
        "analyze",
        "archive",
        "mirror",
        "setup",
        "pushdeployment",
        "pushtocache",
        "execute",
        "logs",
    ]

    _spec_groups = [
        ("compilers", "Compilers"),
        ("software_specs", "Software Specs"),
    ]

    _spec_prefix = ""

    package_manager_class = "PackageManagerBase"
    requires_software_environment = True

    #: Lists of strings which contains GitHub usernames of attributes.
    #: Do not include @ here in order not to unnecessarily ping the users.
    maintainers: List[str] = []
    tags: List[str] = []

    def __init__(self, file_path):
        super().__init__()

        self.object_variants = ramble.variants.VariantSet()
        for var_args in self.class_variants.values():
            self.object_variants.default_variant(**var_args)

        if getattr(self, "families", None) is None:
            self.families = ramble.definitions.families.Families(
                self.origin_type, list(self.class_families.keys())
            )

        ramble.util.class_attributes.convert_class_attributes(self)

        self._file_path = file_path

        self._verbosity = "short"

        self.app_inst = None
        self.keywords = None

        ramble.util.directives.define_directive_methods(self)

        self.object_variants.default_variant(
            self.origin_type,
            default=self.name,
            description="Name of package manager for an experiment",
        )

        for family in self.families:
            self.object_variants.multi_value_variant(
                self.families.family_type,
                value=family,
            )

        self.output_prefix = self.name

    @property
    def runner(self):
        # Turn `runner` into a property for delayed init
        return None

    def copy(self):
        """Deep copy a package manager instance"""
        new_copy = type(self)(self._file_path)
        new_copy._verbosity = self._verbosity

        return new_copy

    def package_manager_dir(self, workspace):
        """Get the path to the package manager's software environment directory

        Args:
            workspace (ramble.workspace.Workspace): Reference to workspace that
                owns a software directory

        Returns:
            (str) Path to package manager directory within workspace's software directory

        """
        return os.path.join(workspace.software_dir, self.name)

    def environment_required(self):
        app_inst = self.app_inst
        if hasattr(app_inst, "software_specs"):
            for definitions in app_inst.software_specs.values():
                for info in definitions:
                    if self.app_inst.expander.satisfies(
                        info.when, variant_set=self.object_variants
                    ):
                        return True

        return False

    def selected_variables(self):
        """Extract all variables which would be included based
        on the current variants.

        Returns:
            (dict) Keys are variable names, values are variable instances
        """
        all_vars = {}
        for when_key, var_list in self.object_variables.items():
            if not self.app_inst.expander.satisfies(
                when_key, self.app_inst.object_variants
            ):
                continue

            for var in var_list:
                all_vars[var.name] = var
        return all_vars

    def selected_environment_variables(self):
        """Extract all environment variables which would be included based
        on the current variants.

        Returns:
            (dict) Keys are environment variable names, values are environment
            variable instances
        """
        all_env_vars = {}
        for (
            when_key,
            env_var_list,
        ) in self.object_environment_variables.items():
            if not self.app_inst.expander.satisfies(
                when_key, self.app_inst.object_variants
            ):
                continue

            for env_var in env_var_list:
                all_env_vars[env_var.name] = env_var
        return all_env_vars

    def get_spec_str(self, pkg, all_pkgs, compiler):
        """Return a spec string for the given pkg

        Can be overridden by individual package managers to provide a more
        specific package spec string. Default is to just return the detected
        package spec.

        Args:
            pkg (ramble.software_environments.RenderedPackage): Reference to a rendered package
            all_pkgs (dict): All related packages
            compiler (bool): True if this pkg is used as a compiler
        """
        return pkg.spec

    def spec_prefix(self):
        """Return this package manager's spec prefix

        Returns:
            (str): Prefix for this package manager's specs
        """
        prefix = self._spec_prefix or self.name
        return spack.util.naming.spack_module_to_python_module(prefix)

    def __str__(self):
        return self.name

    def format_doc(self, **kwargs):
        return format.format_doc(self.__doc__, **kwargs)

    def all_pipeline_phases(self, pipeline):
        """Iterator over all phases within a specified pipeline

        Iterate over all phases (and their graph nodes) within a pipeline.

        Args:
            pipeline (str): Name of pipeline to extract phases for

        Yields:
            phase_name (str): Name of phase
            phase_note (ramble.util.graph.GraphNode): Object representing a
                node in the phase graph
        """
        if pipeline in self.phase_definitions:
            yield from self.phase_definitions[pipeline].items()

    def set_application(self, app_inst):
        """Add an internal reference to the application instance this package
        manager instance is attached to.

        Args:
            app_inst: The experiment this package manager will act on.
        """
        self.app_inst = app_inst
        self.keywords = app_inst.keywords

    def build_used_variables(self, workspace):
        """Build a set of all used variables

        By expanding all necessary portions of this experiment (required /
        reserved keywords, templates, commands, etc...), determine which
        variables are used throughout the experiment definition.

        Variables can have list definitions. These are iterated over to ensure
        variables referenced by any of them are tracked properly.

        Args:
            workspace (ramble.workspace.Workspace): Workspace to extract
                templates from

        Returns:
            (set): All variable names used by this experiment.
        """
        app_context = self.app_inst.expander.expand_var_name(
            self.keywords.env_name
        )

        software_environments = workspace.software_environments
        software_environments.render_environment(
            app_context, self.app_inst.expander, self, require=False
        )

        return self.app_inst.expander._used_variables

    def get_required_variables(self):
        """Get all the required variables based on the mode and when conditions."""
        required_vars = self.required_vars
        filtered_vars = {}
        if required_vars:
            for var_name, var_props in required_vars.items():
                if self.app_inst.expander.satisfies(
                    var_props["when"], self.app_inst.object_variants
                ):
                    filtered_vars[var_name] = {
                        # Exclude the extra when prop
                        k: var_props[k]
                        for k in var_props.keys() - {"when"}
                    }
        return filtered_vars

    def populate_inventory(
        self, workspace, force_compute=False, require_exist=False
    ):
        """Stub class method for populating an experiment inventory.
        Specific package managers should implement this to convey inventory
        information to the workspace / experiment.

        Args:
            workspace (ramble.workspace.Workspace): Reference to the workspace that is currently
                                   being acted on.
            force_compute (bool): Whether to force computation of hashes or not
            require_exist (bool): Whether to require environment hashes exist or not.
        """

        pass

    register_phase(
        "add_software_to_results",
        pipeline="analyze",
        run_after=["analyze_experiments"],
        run_before=["append_results_to_workspace"],
    )

    def _add_software_to_results(self, workspace, app_inst=None):
        """Stub class method for injecting software information into results

        Args:
            workspace (ramble.workspace.Workspace): Reference to the workspace
                that is currently being acted on.
            app_inst: Reference to the application instance that owns the results.

        """
        if app_inst.result is None:
            return
        prov_cache = workspace.pkg_prov_cache
        env_name = self.app_inst.expander.expand_var_name(
            self.keywords.env_name
        )
        if env_name in prov_cache[self.name]:
            # No copy done as this shouldn't be modified once written
            pkg_list = prov_cache[self.name][env_name]
        else:
            pkg_list = self.get_package_list(workspace)
            prov_cache[self.name][env_name] = pkg_list
        self.app_inst.result.software[self.output_prefix] = pkg_list

    def get_package_list(self, workspace):
        """Method used by add_software_to_results phase to get software provenance info"""
        del workspace
        return []

    def environment_load_commands(self) -> List[str]:
        """Stub method for acquiring the commands to load
        an experiment's execution environment"""
        return []

    def environment_unload_commands(self) -> List[str]:
        """Stub method for acquiring the commands to unload an
        experiment's execution environment"""
        return []

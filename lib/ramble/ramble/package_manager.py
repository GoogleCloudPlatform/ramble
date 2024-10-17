# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for package manager definitions"""

import os
import re
import six
import fnmatch
import textwrap
from typing import List

from ramble.language.package_manager_language import PackageManagerMeta
from ramble.language.shared_language import SharedMeta
from ramble.error import RambleError
import ramble.util.directives
import ramble.util.class_attributes
from ramble.util.naming import NS_SEPARATOR

import spack.util.naming


class PackageManagerBase(metaclass=PackageManagerMeta):
    name = None
    _builtin_name = NS_SEPARATOR.join(("package_manager_builtin", "{obj_name}", "{name}"))
    _language_classes = [PackageManagerMeta, SharedMeta]
    _pipelines = [
        "analyze",
        "archive",
        "mirror",
        "setup",
        "pushdeployment",
        "pushtocache",
        "execute",
    ]

    _spec_groups = [
        ("compilers", "Compilers"),
        ("software_specs", "Software Specs"),
    ]

    _spec_prefix = ""

    package_manager_class = "PackageManagerBase"

    #: Lists of strings which contains GitHub usernames of attributes.
    #: Do not include @ here in order not to unnecessarily ping the users.
    maintainers: List[str] = []
    tags: List[str] = []

    def __init__(self, file_path):
        super().__init__()

        ramble.util.class_attributes.convert_class_attributes(self)

        self._file_path = file_path

        self._verbosity = "short"

        self.runner = None
        self.app_inst = None
        self.keywords = None

        ramble.util.directives.define_directive_methods(self)

    def copy(self):
        """Deep copy a package manager instance"""
        new_copy = type(self)(self._file_path)
        new_copy._verbosity = self._verbosity

        return new_copy

    def package_manager_dir(self, workspace):
        """Get the path to the package manager's software environment directory

        Args:
            workspace (Workspace): Reference to workspace that owns a software directory

        Returns:
            (str) Path to package manager directory within workspace's software directory

        """
        return os.path.join(workspace.software_dir, self.name)

    def environment_required(self):
        app_inst = self.app_inst
        if hasattr(app_inst, "software_specs"):
            for pkg, info in app_inst.software_specs.items():
                if fnmatch.fnmatch(self.name, info["package_manager"]):
                    return True

        return False

    def get_spec_str(self, pkg, all_pkgs, compiler):
        """Return a spec string for the given pkg

        Can be overridden by individual package managers to provide a more
        specific package spec string. Default is to just return the detected
        package spec.

        Args:
            pkg (RenderedPackage): Reference to a rendered package
            all_pkgs (dict): All related packages
            compiler (boolean): True if this pkg is used as a compiler
        """
        return pkg.spec

    def spec_prefix(self):
        """Return this package manager's spec prefix

        Returns:
            self._spec_prefix (str): Prefix for this package manager's specs
        """
        prefix = self._spec_prefix or self.name
        return spack.util.naming.spack_module_to_python_module(prefix)

    def __str__(self):
        return self.name

    def format_doc(self, **kwargs):
        """Wrap doc string at 72 characters and format nicely"""
        indent = kwargs.get("indent", 0)

        if not self.__doc__:
            return ""

        doc = re.sub(r"\s+", " ", self.__doc__)
        lines = textwrap.wrap(doc, 72)
        results = six.StringIO()
        for line in lines:
            results.write((" " * indent) + line + "\n")
        return results.getvalue()

    def all_pipeline_phases(self, pipeline):
        """Iterator over all phases wtihin a specified pipeline

        Iterate over all phases (and their graph nodes) within a pipeline.

        Args:
            pipeline (str): Name of pipeline to extract phases for

        Yields:
            phase_name (str): Name of phase
            phase_note (GraphNode): Object representing a node in the phase graph
        """
        if pipeline in self.phase_definitions:
            yield from self.phase_definitions[pipeline].items()

    def set_application(self, app_inst):
        """Add an internal reference to the application instance this package
        manager instance is attached to.

        Args:
            app_inst (ApplicationBase): The experiment this package
                                        manager will act on.
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
            workspace (Workspace): Workspace to extract templates from

        Returns:
            (set): All variable names used by this experiment.
        """
        app_context = self.app_inst.expander.expand_var_name(self.keywords.env_name)

        software_environments = workspace.software_environments
        software_environments.render_environment(
            app_context, self.app_inst.expander, self, require=False
        )

        return self.app_inst.expander._used_variables

    def populate_inventory(self, workspace, force_compute=False, require_exist=False):
        """Stub class method for populating an experiment inventory.
        Specific package managers should implement this to convey inventory
        information to the workspace / experiment.

        Args:
            workspace (Workspace): Reference to the workspace that is currently
                                   being acted on.
            force_compute (boolean): Whether to force computation of hashes or not
            require_exist (boolean): Whether to require environment hashes exist or not.
        """

        pass


class PackageManagerError(RambleError):
    """
    Exception that is raised by package managers
    """

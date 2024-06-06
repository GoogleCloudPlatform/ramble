# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for package manager definitions"""

import re
import six
import textwrap
from typing import List

from llnl.util.tty.colify import colified

from ramble.language.package_manager_language import PackageManagerMeta
from ramble.language.shared_language import SharedMeta, register_builtin  # noqa: F401
from ramble.error import RambleError
import ramble.util.colors as rucolor
import ramble.util.directives
import ramble.util.class_attributes

import spack.util.naming


class PackageManagerBase(object, metaclass=PackageManagerMeta):
    name = None
    _builtin_name = "package_manager_builtin::{obj_name}::{name}"
    _pkgman_prefix_builtin = r"package_manager_builtin::"
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

    def get_spec_str(self, pkg, all_pkgs, compiler):
        """Return a spec string for the given pkg

        Args:
            pkg (RenderedPackage): Reference to a rendered package
            all_pkgs (dict): All related packages
            compiler (boolean): True if this pkg is used as a compiler
        """
        return ""

    def _long_print(self):
        out_str = []
        out_str.append(rucolor.section_title("Package Manager: ") + f"{self.name}\n")
        out_str.append("\n")

        simplified_name = spack.util.naming.spack_module_to_python_module(self.name)
        out_str.append(rucolor.section_title("Spec prefix: ") + f"{simplified_name}\n")
        out_str.append("\n")

        out_str.append(rucolor.section_title("Description:\n"))
        if self.__doc__:
            out_str.append(f"\t{self.__doc__}\n")
        else:
            out_str.append("\tNone\n")

        if hasattr(self, "tags"):
            out_str.append("\n")
            out_str.append(rucolor.section_title("Tags:\n"))
            out_str.append(colified(self.tags, tty=True))
            out_str.append("\n")

        if hasattr(self, "builtins"):
            out_str.append(rucolor.section_title("Builtin Executables:\n"))
            out_str.append("\t" + colified(self.builtins.keys(), tty=True) + "\n")

        if hasattr(self, "package_manager_configs"):
            out_str.append("\n")
            out_str.append(rucolor.section_title("Package Manager Configs:\n"))
            for name, config in self.package_manager_configs.items():
                out_str.append(f"\t{name} = {config}\n")

        for group in self._spec_groups:
            if hasattr(self, group[0]):
                out_str.append("\n")
                out_str.append(rucolor.section_title("%s:\n" % group[1]))
                for name, info in getattr(self, group[0]).items():
                    out_str.append(rucolor.nested_1("  %s:\n" % name))
                    for key in self._spec_keys:
                        if key in info and info[key]:
                            out_str.append("    %s = %s\n" % (key, info[key].replace("@", "@@")))

        return out_str

    def _short_print(self):
        return [self.name]

    def __str__(self):
        if self._verbosity == "long":
            return "".join(self._long_print())
        elif self._verbosity == "short":
            return "".join(self._short_print())
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
            for phase_name, phase_node in self.phase_definitions[pipeline].items():
                yield phase_name, phase_node

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
            app_context, self.app_inst.expander, self.app_inst.package_manager, require=False
        )

        return self.app_inst.expander._used_variables


class PackageManagerError(RambleError):
    """
    Exception that is raised by package managers
    """

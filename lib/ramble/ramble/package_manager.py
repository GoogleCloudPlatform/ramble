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

        self.runner_class = None

        ramble.util.directives.define_directive_methods(self)

    def copy(self):
        """Deep copy a package manager instance"""
        new_copy = type(self)(self._file_path)
        new_copy._verbosity = self._verbosity

        return new_copy

    def _long_print(self):
        out_str = []
        out_str.append(rucolor.section_title("Package Manager: ") + f"{self.name}\n")
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


class PackageManagerError(RambleError):
    """
    Exception that is raised by package managers
    """

# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import sys
from typing import Dict, List

import llnl.util.tty.color as color
from llnl.util.tty.colify import colify

import ramble.repository
from ramble.util.logger import logger

description = "inspect software definitions in object definitions"
section = "developer"
level = "long"

unused_compilers = {}
definitions = {}
conflicts = {}
used_by = {}
specs: Dict[str, Dict[str, List[str]]] = {"pkg_spec": {}, "compiler_spec": {}}
spec_headers = {
    "pkg_spec": "Software Packages",
    "compiler_spec": "Compiler Definitions",
}

header_color = "@*b"
level1_color = "@*g"
level2_color = "@*r"
plain_format = "@."


def section_title(s):
    return header_color + s + plain_format


def nested_1(s):
    return level1_color + s + plain_format


def nested_2(s):
    return level2_color + s + plain_format


def collect_definitions():
    """Build software definition data structures

    Iterate over all defined objects and extract their software definitions.
    Built maps representing which objects use a given software definition, and
    where detected conflicts have occurred.

    The maps are global to this module, and reused in other internal methods.
    """
    top_level_attrs = ["compilers", "software_specs"]

    types_to_print = [
        ramble.repository.ObjectTypes.applications,
        ramble.repository.ObjectTypes.modifiers,
        ramble.repository.ObjectTypes.workflow_managers,
        ramble.repository.ObjectTypes.package_managers,
    ]

    for object_type in types_to_print:
        obj_path = ramble.repository.paths[object_type]
        for obj_inst in obj_path.all_objects():
            obj_repo = obj_path.repo_for_obj(obj_inst.name)

            obj_namespace = f"{obj_repo.full_namespace}.{obj_inst.name}"

            for compiler_name in obj_inst.compilers:
                used = False
                for pkg_defs in obj_inst.software_specs.values():
                    for pkg_def in pkg_defs:
                        if (
                            getattr(pkg_def, "compiler", "__rmb_no_compiler_attr__")
                            == compiler_name
                        ):
                            used = True
                if not used:
                    if compiler_name not in unused_compilers:
                        unused_compilers[compiler_name] = []
                    unused_compilers[compiler_name].append(obj_namespace)

            for top_level_attr in top_level_attrs:
                if hasattr(obj_inst, top_level_attr):
                    for pkg_name, pkg_defs in getattr(obj_inst, top_level_attr).items():
                        for pkg_def in pkg_defs:
                            if pkg_name not in definitions:
                                definitions[pkg_name] = pkg_def.copy()
                                used_by[pkg_name] = [obj_namespace]
                            else:
                                logger.debug(f" Checking package: {pkg_name}")
                                if pkg_def.conflict_spec(
                                    definitions[pkg_name], skip_conflicting_when=True
                                ):
                                    if pkg_name not in conflicts:
                                        conflicts[pkg_name] = []
                                    conflicts[pkg_name].append(obj_namespace)
                                else:
                                    used_by[pkg_name].append(obj_namespace)

                            for spec_name in specs:
                                if hasattr(pkg_def, spec_name):
                                    spec_def = getattr(pkg_def, spec_name)
                                    if spec_def:
                                        if spec_def not in specs[spec_name]:
                                            specs[spec_name][spec_def] = []
                                        specs[spec_name][spec_def].append(obj_namespace)


def print_summary():
    """Print a summary of all software definitions"""
    color.cprint(section_title("Software Summary:"))
    color.cprint("\n")
    for spec_name in specs:
        color.cprint(nested_1(spec_headers[spec_name]) + ":")
        for spec_def in specs[spec_name]:
            color.cprint(f'\t{nested_2("Spec:")} {spec_def.replace("@", "@@")}')
            color.cprint("\tIn object:")
            colify(specs[spec_name][spec_def], indent=16, output=sys.stdout)
        color.cprint("\n")


def count_conflicts():
    """Iterate over conflicts and count how many were detected"""
    num_conflicts = 0
    for pkg_name in conflicts:
        num_conflicts += len(conflicts[pkg_name])
    for object_names in unused_compilers.values():
        num_conflicts += len(object_names)
    return num_conflicts


def print_conflicts():
    """Print conflict information, if any exist"""
    if len(conflicts) > 0 or len(unused_compilers) > 0:
        if len(conflicts) > 0:
            color.cprint(section_title("Software Definition Conflicts:"))
            for pkg_name in conflicts:

                color.cprint(f'{nested_1("Package")}: {pkg_name}:')
                color.cprint("\tDefined as:")
                for attr in ["pkg_spec", "compiler_spec", "compiler"]:
                    if hasattr(definitions[pkg_name], attr):
                        attr_def = getattr(definitions[pkg_name], attr)
                        if attr_def:
                            color.cprint(f'\t\t{attr} = {attr_def.replace("@", "@@")}')
                color.cprint("\tIn objects:")
                colify(used_by[pkg_name], indent=24, output=sys.stdout)
                color.cprint("\tConflicts with objects:")
                colify(conflicts[pkg_name], indent=24, output=sys.stdout)

        if len(unused_compilers) > 0:
            color.cprint(section_title("Unused Compilers:"))
            for compiler_name, object_names in unused_compilers.items():
                color.cprint(nested_1(f"    Compiler {compiler_name} is not used in packages:"))
                colify(object_names, indent=8, output=sys.stdout)
                color.cprint("\n")
    else:
        color.cprint(section_title("No Conflicts Detected"))


def setup_parser(subparser):
    """Setup the parser for software-definitions"""
    subparser.add_argument(
        "-s", "--summary", action="store_true", help="print summary of software definitions"
    )

    subparser.add_argument(
        "-c", "--conflicts", action="store_true", help="print summary of conflicting definitions"
    )

    subparser.add_argument(
        "-e",
        "--error-on-conflict",
        action="store_true",
        help="if conflicts are found, exit code is number of conflicts",
    )


def software_definitions(parser, args, unknown_args):
    """Perform software-definitions actions"""
    collect_definitions()

    if args.summary:
        print_summary()

    if args.conflicts:
        print_conflicts()

    if args.error_on_conflict:
        num_conflicts = count_conflicts()
        if num_conflicts == 1:
            color.cprint(f"{num_conflicts} conflict detected.")
        else:
            color.cprint(f"{num_conflicts} conflicts detected.")
        sys.exit(num_conflicts)

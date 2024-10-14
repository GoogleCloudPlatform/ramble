# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import fnmatch

import llnl.util.tty.color as color
from llnl.util.tty.colify import colified

import ramble.util.colors
import ramble.cmd.common.arguments as arguments
import ramble.repository

from ramble.util.logger import logger

import enum

supported_formats = enum.Enum("formats", ["text", "lists"])

obj_attribute_map = {
    "maintainers": None,
    "tags": None,
    "pipelines": "_pipelines",
    "figure_of_merit_contexts": None,
    "figures_of_merit": None,
    "builtins": None,
    "package_manager_configs": None,
    "required_packages": None,
    "compilers": None,
    "software_specs": None,
    "archive_patterns": None,
    "success_criteria": None,
    "target_shells": "shell_support_pattern",
    # Application specific:
    "workloads": None,
    "workload_groups": None,
    "executables": None,
    "inputs": None,
    "workload_variables": None,
    "registered_phases": "phase_definitions",
    # Modifier specific:
    "modes": None,
    "default_mode": "_default_usage_mode",
    "variable_modifications": None,
    "executable_modifiers": None,
    "env_var_modifications": None,
    "required_vars": None,
    "modifier_variables": None,
    "package_manager_requirements": None,
    # Package manager specific:
    "package_manager_variables": None,
}


def _map_attr_name(attr):
    """Given an attribute display name, map to the internal attribute name"""
    return obj_attribute_map[attr] if obj_attribute_map[attr] is not None else attr


def setup_info_parser(subparser):
    """Create the info parser"""

    subparser.add_argument("object", help="Name of object to print info for")

    arguments.add_common_arguments(subparser, ["obj_type"])

    available_formats = []
    for format in supported_formats:
        available_formats.append(format.name)

    subparser.add_argument(
        "--format",
        default="text",
        help=f"list of output format to write. Available options are {available_formats}",
    )

    subparser.add_argument(
        "--pattern",
        "-p",
        default="*",
        metavar="PATTERN",
        help="filter the attributes using this pattern",
    )

    level = subparser.add_mutually_exclusive_group()
    level.add_argument(
        "--overview",
        "-o",
        action="store_true",
        help="print overview of what attributes an object has",
    )
    level.add_argument(
        "--verbose", "-v", action="store_true", help="print full information about attributes"
    )

    attributes = subparser.add_mutually_exclusive_group()
    attributes.add_argument(
        "--all", action="store_true", default=True, help="print all object attributes"
    )
    attributes.add_argument(
        "--attributes",
        "--attrs",
        dest="attributes",
        default="",
        help="comma separated list of attributes to inspect for object",
    )


def all_object_attributes(obj):
    """Return a list of all attributes on the object

    Determine which of the available attributes a given object has (and has
    definitions in) and return a list of such attributes.

    Returns:
        (list) all_attrs: List of all attributes the object contains
    """
    all_attrs = []
    for name in obj_attribute_map:
        attr = _map_attr_name(name)
        if hasattr(obj, attr) and getattr(obj, attr):
            all_attrs.append(name)
    return all_attrs


def print_object_header(obj_type, obj):
    """Print an object header"""
    singular = ramble.repository.type_definitions[obj_type]["singular"]
    parts = [part[0].upper() + part[1:] for part in singular.split()]
    type_name = ramble.util.colors.section_title(" ".join(parts))
    color.cprint(f"{type_name}: {obj.name}\n")

    color.cprint(ramble.util.colors.section_title("Description:"))
    if obj.__doc__:
        doc_str = ""
        for part in obj.__doc__.split("\n"):
            doc_str += f"    {part}\n"

        color.cprint(doc_str)


def print_object_overview(obj):
    """Print object overview

    Print the available attributes within a given object.
    """
    color.cprint("Available attributes:")
    for name in all_object_attributes(obj):
        color.cprint(f"\t{name}")


# Attributes that need special print functions
def _print_phases(obj, attr, verbose=False, pattern="*", format=supported_formats.text):
    """Print registered phases

    Registered phases are stored in a nested dictionary. Here, we print them by
    extracting and filtering phases within a pipeline and printing them.
    """
    internal_attr_name = _map_attr_name(attr)
    internal_attr = getattr(obj, internal_attr_name)
    print_attribute_header(attr, verbose)

    if not verbose:
        color_func = ramble.util.colors.level_func(1)
        base_indent = 4
    else:
        color_func = ramble.util.colors.level_func(0)
        base_indent = 0

    indentation = " " * base_indent
    # For phases, this is a dict where the pipelines are keys, and the values
    # are the pipeline phases.
    # Iterate over all items in the dict, filter based on phases, and print
    # using the provided format specification.
    for pipeline, phases in internal_attr.items():
        to_print = fnmatch.filter(phases, pattern)
        if not to_print:
            continue

        color_pipeline = color_func(pipeline)
        if format == supported_formats.lists:
            color.cprint(f"{indentation}{color_pipeline}:")
            color.cprint(f"{indentation}    {str(list(to_print))}")
        elif format == supported_formats.text:
            color.cprint(f"{indentation}{color_pipeline}:")
            color.cprint(colified(to_print, tty=True, indent=base_indent + 4))


def print_single_attribute(obj, attr, verbose=False, pattern="*", format=supported_formats.text):
    """Handle printing a single attribute

    For a given object, print a single attribute of this based on the given
    format specification and filter pattern.
    """
    internal_attr_name = _map_attr_name(attr)
    internal_attr = getattr(obj, internal_attr_name, None)
    if attr == "registered_phases":
        _print_phases(obj, attr, verbose, pattern, format=format)
        return

    print_attribute_header(attr, verbose)

    indentation = " " * 4

    # If we are not printing verbose output, we suppress most of the output.
    if not verbose:
        # If the attribute is a dictionary, convert the keys to a list, and
        # print them
        # Otherwise, we print the attribute's value directly.
        if isinstance(internal_attr, dict):
            to_print = list(internal_attr.keys())
        else:
            to_print = internal_attr

        # If we are trying to print a list, filter it and print using the
        # format specification
        # Otherwise, print it as a raw string.
        if isinstance(to_print, list):
            to_print = fnmatch.filter(to_print, pattern)
            if format == supported_formats.lists:
                color.cprint("    " + str(list(to_print)))
            elif format == supported_formats.text:
                color.cprint(colified(to_print, tty=True, indent=4))
        else:
            color.cprint(f"    {str(to_print)}\n")
    else:
        # With verbose output, and a dict attribute, we try to print all of the
        # sub items. These need to be iterated over, and we need to escape
        # existing characters that would normally be used to color strings.
        if isinstance(internal_attr, dict):
            for name, val in internal_attr.items():
                if pattern and not fnmatch.fnmatch(name, pattern):
                    continue

                if isinstance(val, dict):
                    color_name = ramble.util.colors.section_title(name)
                    color.cprint(f"{color_name}:")
                    for sub_name, sub_val in val.items():
                        color_sub_name = ramble.util.colors.nested_1(sub_name)
                        try:
                            color.cprint(f"{indentation}{color_sub_name}: {sub_val}")
                        except color.ColorParseError:
                            escaped_sub_val = sub_val.replace("@", "@@")
                            color.cprint(f"{indentation}{color_sub_name}: {escaped_sub_val}")
                    color.cprint("")
                else:
                    color.cprint(f"{str(val)}")
        # If the attribute is not a dict, print using the existing format rules.
        elif isinstance(internal_attr, list):
            to_print = fnmatch.filter(internal_attr, pattern)
            if format == supported_formats.lists:
                color.cprint("    " + str(list(to_print)))
            elif format == supported_formats.text:
                color.cprint(colified(to_print, tty=True, indent=4))
            color.cprint("")
        else:
            color.cprint(f"{indentation}" + str(internal_attr))


def print_attribute_header(attr, verbose=False):
    """Print the attribute header

    The attribute header is a separator between different attributes in the
    output.
    """
    banner_char = "#"

    if verbose:
        num = len(attr) + 4
        banner = f"{banner_char}" * num
        color.cprint(banner)
        color.cprint(f"{banner_char} {attr} {banner_char}")
        color.cprint(banner)
    else:
        attr_name = ramble.util.colors.section_title(attr)
        color.cprint(f"{attr_name}:")


def print_all_attributes(obj, verbose=False, pattern="*", format=supported_formats.text):
    """Print every attribute on an object

    Iterate over all attributes for a given object, and print each one individually.
    """
    for name in all_object_attributes(obj):
        print_single_attribute(obj, name, verbose, pattern=pattern, format=format)


def print_info(args):
    """Primary entrypoint for the `info` command"""
    if not hasattr(supported_formats, args.format):
        logger.die("Invalid format specified. See help for supported formats")

    format_type = getattr(supported_formats, args.format)
    args.format = format_type

    object_type = ramble.repository.ObjectTypes[args.type]
    obj_name = args.object
    obj = ramble.repository.get(obj_name, object_type=object_type)

    print_object_header(object_type, obj)

    if args.overview:
        print_object_overview(obj)
    elif args.attributes:
        for attr in args.attributes.split(","):
            print_single_attribute(obj, attr, args.verbose, args.pattern, args.format)
    elif args.all:
        print_all_attributes(obj, args.verbose, args.pattern, args.format)

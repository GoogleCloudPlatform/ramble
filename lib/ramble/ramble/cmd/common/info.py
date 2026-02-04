# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import enum
import fnmatch

import llnl.util.tty.color as color
from llnl.util.tty.colify import colified

import ramble.cmd.common.arguments as arguments
import ramble.repository
import ramble.util.colors
from ramble.definitions.variables import Variable
from ramble.util.logger import logger

supported_formats = enum.Enum("supported_formats", ["text", "lists"])

obj_attribute_map = {
    "maintainers": None,
    "tags": None,
    "pipelines": "_pipelines",
    "figure_of_merit_contexts": None,
    "figures_of_merit": None,
    "builtins": None,
    "cleanups": None,
    "package_manager_configs": None,
    "required_packages": None,
    "object_variants": None,
    "compilers": None,
    "known_versions": None,
    "software_specs": None,
    "archive_patterns": None,
    "success_criteria": None,
    "target_shells": "shell_support_pattern",
    "templates": None,
    "validators": None,
    "object_variables": None,
    "object_environment_variables": None,
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
    "package_manager_requirements": None,
    # Package / workflow manager specific:
    "families": None,
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
        (list): List of all attributes the object contains
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


def _unpack_when_set_if_needed(internal_attr: dict):
    """If the attribute has a frozenset key, assume the attribute is nested in
    a set of 'when' conditions and unpack the innner values to print.
    """
    first_key = next(iter(internal_attr))
    first_val = internal_attr[first_key]
    if isinstance(first_key, frozenset):
        if isinstance(first_val, dict):
            # unpack to a list of dicts so dicts with same keys don't overwrite
            unpacked_dict = []
            for inner_dict in internal_attr.values():
                unpacked_dict.append(inner_dict)
            return unpacked_dict
        elif isinstance(first_val, list):
            unpacked_list = []
            for inner_list in internal_attr.values():
                unpacked_list.extend(inner_list)
            return unpacked_list
        else:
            return internal_attr[first_key]
    else:
        return internal_attr


def _print_nonverbose_list_attr(internal_attr, pattern="*", format=supported_formats.text):
    to_print = fnmatch.filter(map(str, internal_attr), pattern)
    if format == supported_formats.lists:
        color.cprint("    " + str(list(to_print)))
    elif format == supported_formats.text:
        color.cprint(colified(to_print, tty=True, indent=4))


def _print_verbose_dict_attr(internal_attr, pattern="*", indentation=(" " * 4)):
    """With verbose output, and a dict attribute, we try to print all of the
    sub items. These need to be iterated over, and we need to escape existing
    characters that would normally be used to color strings.
    """
    i = 0
    for name, vals in internal_attr.items():
        i += 1
        if pattern and not fnmatch.fnmatch(name, pattern):
            continue
        if isinstance(vals, dict):
            color_name = ramble.util.colors.section_title(name)
            color.cprint(f"{color_name}:")
            for sub_name, sub_val in vals.items():
                # Avoid showing duplicate names for variables
                if isinstance(sub_val, Variable) and sub_name == sub_val.name:
                    to_print = f"{indentation}{sub_val}"
                else:
                    color_sub_name = ramble.util.colors.nested_1(sub_name)
                    to_print = f"{indentation}{color_sub_name}: {sub_val}"
                try:
                    color.cprint(to_print)
                except color.ColorParseError:
                    if hasattr(sub_val, "__iter__"):
                        escaped_sub_val = [item.replace("@", "@@") for item in sub_val]
                    else:
                        escaped_sub_val = sub_val.replace("@", "@@")
                    color.cprint(f"{indentation}{color_sub_name}: {escaped_sub_val}")
            color.cprint("")
        elif isinstance(vals, set):
            color_name = ramble.util.colors.section_title(name)
            color.cprint(f"{color_name}:")
            for sub_name in vals:
                # Avoid showing duplicate names for variables
                color_sub_name = ramble.util.colors.nested_1(sub_name)
                to_print = f"{indentation}{color_sub_name}"
                try:
                    color.cprint(to_print)
                except color.ColorParseError:
                    escaped_sub_name = ramble.util.colors.nested_1(sub_name.replace("@", "@@"))
                    color.cprint(f"{indentation}{escaped_sub_name}")
            color.cprint("")
        elif isinstance(vals, list):
            for val in vals:
                if hasattr(val, "as_str"):
                    color.cprint(f"{val.as_str(verbose=True)}")
                else:
                    color.cprint(f"{str(val)}")
        else:
            if hasattr(vals, "as_str"):
                color.cprint(f"{vals.as_str(verbose=True)}")
            else:
                color.cprint(f"{str(vals)}")
                #  Necessary to add a line break after unformmated sections
                if i == len(internal_attr.keys()):
                    color.cprint("")


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


def _print_figures_of_merit(obj, attr, verbose=False, pattern="*", format=supported_formats.text):
    """Print figures of merit

    Figures of merit are stored in a nested dictionary.
    """
    internal_attr_name = _map_attr_name(attr)
    internal_attr = getattr(obj, internal_attr_name)
    print_attribute_header(attr, verbose)

    indentation = " " * 4

    for context_dict in internal_attr.values():
        for fom_dict in context_dict.values():
            if not verbose:
                to_print = list(fom_dict.keys())

                # If we are trying to print a list, filter it and print using the
                # format specification
                # Otherwise, print it as a raw string.
                if isinstance(to_print, list):
                    _print_nonverbose_list_attr(to_print, pattern=pattern, format=format)
                else:
                    color.cprint(f"    {str(to_print)}\n")
            else:
                _print_verbose_dict_attr(fom_dict, pattern=pattern, indentation=indentation)


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
    elif attr == "figures_of_merit":
        _print_figures_of_merit(obj, attr, verbose, pattern, format=format)
        return
    elif isinstance(internal_attr, dict):
        internal_attr = _unpack_when_set_if_needed(internal_attr)

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

        # If we are trying to print a list:
        #     if it's a list of dicts, convert the keys like above and print
        #     otherwise filter it and print using the format specification
        # Otherwise, print it as a raw string.
        if isinstance(to_print, list):
            if internal_attr and isinstance(next(iter(internal_attr)), dict):
                to_print = [key for attr_dict in internal_attr for key in attr_dict]
            _print_nonverbose_list_attr(to_print, pattern=pattern, format=format)
        else:
            color.cprint(f"    {str(to_print)}\n")
    else:
        if isinstance(internal_attr, dict):
            _print_verbose_dict_attr(internal_attr, pattern=pattern, indentation=indentation)
        elif isinstance(internal_attr, list):
            # If it's a list of dicts, print each
            if isinstance(next(iter(internal_attr)), dict):
                for attr_dict in internal_attr:
                    _print_verbose_dict_attr(attr_dict, pattern=pattern, indentation=indentation)
            # If the attribute is not a dict or list of dict, print using the existing format rules
            else:
                if hasattr(next(iter(internal_attr)), "as_str"):
                    for obj in internal_attr:
                        if pattern and not fnmatch.fnmatch(obj.name, pattern):
                            continue

                        color.cprint(f"{obj.as_str(verbose=True)}")
                else:
                    to_print = fnmatch.filter(map(str, internal_attr), pattern)
                    if format == supported_formats.lists:
                        color.cprint("    " + str(list(to_print)))
                    elif format == supported_formats.text:
                        color.cprint(colified(to_print, tty=True, indent=4))
                    color.cprint("")
        else:
            if hasattr(internal_attr, "as_str"):
                color.cprint(f"{internal_attr.as_str(verbose=True)}")
            else:
                color.cprint(f"{indentation}" + str(internal_attr) + "\n")


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
    obj = ramble.repository.get(obj_name.partition("@")[0], object_type=object_type)

    print_object_header(object_type, obj)

    if args.overview:
        print_object_overview(obj)
    elif args.attributes:
        for attr in args.attributes.split(","):
            print_single_attribute(obj, attr, args.verbose, args.pattern, args.format)
    elif args.all:
        print_all_attributes(obj, args.verbose, args.pattern, args.format)

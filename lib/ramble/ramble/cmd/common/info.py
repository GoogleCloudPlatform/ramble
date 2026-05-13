# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import enum
import fnmatch

from llnl.util.tty.colify import colified

import ramble.cmd.common.arguments as arguments
import ramble.repository
import ramble.util.colors as color
from ramble.definitions.variables import Variable
from ramble.util.logger import logger

supported_formats = enum.Enum("supported_formats", ["text", "lists"])

obj_attribute_map = {
    "maintainers": None,
    "tags": None,
    "pipelines": None,
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
    type_name = color.section_title(" ".join(parts))
    color.cprint(f"{type_name}: {obj.name}\n")

    color.cprint(color.section_title("Description:"))
    if obj.__doc__:
        doc_str = ""
        for part in obj.__doc__.split("\n"):
            doc_str += f"    {part}\n"

        color.cprint(f"{doc_str}")


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
        color.cprint(f"    {list(to_print)}")
    elif format == supported_formats.text:
        color.cprint(f"{colified(to_print, tty=True, indent=4)}")


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
            color_name = color.section_title(name)
            color.cprint(f"{color_name}:")
            for sub_name, sub_val in vals.items():
                # Avoid showing duplicate names for variables
                if isinstance(sub_val, Variable) and sub_name == sub_val.name:
                    color.cprint(f"{indentation}{sub_val}")
                else:
                    color_sub_name = color.nested_1(sub_name)
                    color.cprint(f"{indentation}{color_sub_name}: {sub_val}")
            color.cprint("")
        elif isinstance(vals, set):
            color_name = color.section_title(name)
            color.cprint(f"{color_name}:")
            for sub_name in vals:
                # Avoid showing duplicate names for variables
                color_sub_name = color.nested_1(sub_name)
                to_print = f"{indentation}{color_sub_name}"
                color.cprint(to_print)
            color.cprint("")
        elif isinstance(vals, list):
            for val in vals:
                if hasattr(val, "as_str"):
                    color.cprint(val.as_str(verbose=True))
                else:
                    color.cprint(f"{val}")
        else:
            if hasattr(vals, "as_str"):
                color.cprint(vals.as_str(verbose=True))
            else:
                color.cprint(f"{vals}")
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
        color_func = color.level_func(1)
        base_indent = 4
    else:
        color_func = color.level_func(0)
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
            color.cprint(f"{indentation}    {list(to_print)}")
        elif format == supported_formats.text:
            color.cprint(f"{indentation}{color_pipeline}:")
            color.cprint(f"{colified(to_print, tty=True, indent=base_indent + 4)}")


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
                    color.cprint(f"    {to_print}\n")
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
        elif hasattr(internal_attr, "default_variants"):
            to_print = []
            for variant in internal_attr.default_variants.values():
                to_print.append(variant)
            for variant_set in internal_attr.multi_value_variants.values():
                for variant in variant_set:
                    to_print.append(variant)
            for variant in internal_attr.experiment_variants.values():
                to_print.append(variant)
            for variant in internal_attr.version_variants.values():
                to_print.append(variant)
        elif hasattr(internal_attr, "family_type"):
            to_print = [f"{internal_attr.family_type}={family}" for family in internal_attr]
        else:
            to_print = internal_attr

        # If we are trying to print a list:
        #     if it's a list of dicts, convert the keys like above and print
        #     otherwise filter it and print using the format specification
        # Otherwise, print it as a raw string.
        if isinstance(to_print, (list, set, tuple)) or (
            hasattr(to_print, "__iter__") and not isinstance(to_print, str)
        ):
            to_print = list(to_print)
            if (
                internal_attr
                and isinstance(internal_attr, list)
                and isinstance(next(iter(internal_attr), None), dict)
            ):
                to_print = [key for attr_dict in internal_attr for key in attr_dict]
            _print_nonverbose_list_attr(to_print, pattern=pattern, format=format)
        else:
            color.cprint(f"    {to_print}\n")
    else:
        if isinstance(internal_attr, dict):
            _print_verbose_dict_attr(internal_attr, pattern=pattern, indentation=indentation)
        elif isinstance(internal_attr, (list, set, tuple)):
            internal_list = list(internal_attr)
            # If it's a list of dicts, print each
            if internal_list and isinstance(internal_list[0], dict):
                for attr_dict in internal_list:
                    _print_verbose_dict_attr(attr_dict, pattern=pattern, indentation=indentation)
            # If the attribute is not a dict or list of dict, print using the existing format rules
            elif internal_list:
                if hasattr(internal_list[0], "as_str"):
                    for obj in internal_list:
                        name_str = getattr(obj, "name", str(obj))
                        if pattern and not fnmatch.fnmatch(name_str, pattern):
                            continue

                        color.cprint(obj.as_str(verbose=True))
                else:
                    to_print = fnmatch.filter(map(str, internal_list), pattern)
                    if format == supported_formats.lists:
                        color.cprint(f"    {list(to_print)}")
                    elif format == supported_formats.text:
                        color.cprint(f"{colified(to_print, tty=True, indent=4)}")
                    color.cprint("")
        else:
            if hasattr(internal_attr, "as_str"):
                color.cprint(internal_attr.as_str(verbose=True))
            else:
                color.cprint(f"{indentation}{internal_attr}\n")


def print_attribute_header(attr, verbose=False):
    """Print the attribute header

    The attribute header is a separator between different attributes in the
    output.
    """
    banner_char = "#"

    if verbose:
        num = len(attr) + 4
        banner = f"{banner_char}" * num
        color.cprint(f"{banner}")
        color.cprint(f"{banner_char} {attr} {banner_char}")
        color.cprint(f"{banner}")
    else:
        attr_name = color.section_title(attr)
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

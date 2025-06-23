# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import fnmatch
from collections import OrderedDict
from typing import Any, List, Union

from ramble.language.language_base import DirectiveError


def check_definition(
    single_type, multiple_type, single_arg_name, multiple_arg_name, directive_name
):
    """
    Sanity check definitions before merging or require

    Args:
        single_type: Single string for type name
        multiple_type: List of strings for type names, may contain wildcards
        multiple_pattern_match: List of strings to match against patterns in multiple_type
        single_arg_name: String name of the single_type argument in the directive
        multiple_arg_name: String name of the multiple_type argument in the directive
        directive_name: Name of the directive requiring a type

    Returns:
        List of all type names (Merged if both single_type and multiple_type definitions are valid)
    """
    if single_type and not isinstance(single_type, str):
        raise DirectiveError(
            f"Directive {directive_name} was given an invalid type "
            f"for the {single_arg_name} argument. "
            f"Type was {type(single_type)}"
        )

    if multiple_type and not isinstance(multiple_type, list):
        raise DirectiveError(
            f"Directive {directive_name} was given an invalid type "
            f"for the {multiple_arg_name} argument. "
            f"Type was {type(multiple_type)}"
        )


def merge_definitions(
    single_type,
    multiple_type,
    multiple_pattern_match,
    single_arg_name,
    multiple_arg_name,
    directive_name,
):
    """Merge definitions of a type

    This method will merge two optional definitions of single_type and
    multiple_type.

    Args:
        single_type: Single string for type name
        multiple_type: List of strings for type names, may contain wildcards
        multiple_pattern_match: List of strings to match against patterns in multiple_type
        single_arg_name: String name of the single_type argument in the directive
        multiple_arg_name: String name of the multiple_type argument in the directive
        directive_name: Name of the directive requiring a type

    Returns:
        List of all type names (Merged if both single_type and multiple_type definitions are valid)
    """

    check_definition(
        single_type, multiple_type, single_arg_name, multiple_arg_name, directive_name
    )

    merged_types = []

    if single_type:
        merged_types.append(single_type)

    if multiple_type:
        merged_types.extend(multiple_type)

    merged_types_expanded = expand_patterns(merged_types, multiple_pattern_match)

    return merged_types_expanded


def require_definition(
    single_type,
    multiple_type,
    multiple_pattern_match,
    single_arg_name,
    multiple_arg_name,
    directive_name,
):
    """Require at least one definition for a type in a directive

    This method will validate that single_type / multiple_type are properly defined.

    It will raise an error if at least one type is not defined, or if
    either are the incorrect type.

    Args:
        single_type: Single string for type name
        multiple_type: List of strings for type names, may contain wildcards
        multiple_pattern_match: List of strings to match against patterns in multiple_type
        single_arg_name: String name of the single_type argument in the directive
        multiple_arg_name: String name of the multiple_type argument in the directive
        directive_name: Name of the directive requiring a type

    Returns:
        List of all type names (Merged if both single_type and multiple_type definitions are valid)
    """

    if not (single_type or multiple_type):
        raise DirectiveError(
            f"Directive {directive_name} requires at least one of "
            f"{single_arg_name} or {multiple_arg_name} to be defined."
        )

    return merge_definitions(
        single_type,
        multiple_type,
        multiple_pattern_match,
        single_arg_name,
        multiple_arg_name,
        directive_name,
    )


def require_when_or_mode(
    mode,
    modes,
    mod,
    when,
    directive_name,
):
    """Require at least one definition for a type in a modifier directive, either in mode/modes or
    in when

    If mode/modes are provided, this method will validate that single_type / multiple_type are
    properly defined, and will merge them into a when list.

    It will raise an error if at least one type is not defined, or if any are the incorrect type.

    Args:
        mode: Single string for mode name
        modes: List of strings for mode names, may contain wildcards
        mod: Modifier instance
        when: List of when conditions
        directive_name: Name of the calling directive

    Returns:
        List of all when conditions (including mode/modes merged)
    """

    if not (mode or modes or when):
        raise DirectiveError(
            f"Directive {directive_name} requires at least one of mode, modesm or when to be "
            "defined."
        )

    all_modes = merge_definitions(
        mode,
        modes,
        mod.modes,
        "mode",
        "modes",
        directive_name,
    )

    when_list = build_when_list(when, mod, mod.name, directive_name)

    if all_modes:
        for mode_name in all_modes:
            when_list.append(f"{mod.name}_mode={mode_name}")

    return when_list


def expand_patterns(merged_types: list, multiple_pattern_match: Union[list, dict]):
    """Expand wildcard patterns within a list of names

    This method takes an input list containing wildcard patterns and expands the
    wildcard with values matching a list of names. Returns a list containing
    matching names and any inputs with zero matches.

    If multiple_pattern_match is a dict keyed on 'when', it checks the input
    against patterns in all 'when' conditions, without evaluating them, and
    returns a list containing names that match under any when condition, and
    any inputs with zero matches.

    Args:
        merged_types: List of strings for type names, may contain wildcards
        multiple_pattern_match: List of strings (optional: nested in when_set
            dict) to match against patterns in merged_types

    Returns:
        List of expanded patterns matching the names list plus patterns
            not found in the names list.
    """
    expanded_patterns = OrderedDict()
    for input in merged_types:
        expanded = False
        if (
            multiple_pattern_match
            and isinstance(multiple_pattern_match, dict)
            and isinstance(next(iter(multiple_pattern_match)), frozenset)
        ):
            for _, pattern_list in multiple_pattern_match.items():
                matched_inputs = fnmatch.filter(pattern_list, input)
                if matched_inputs:
                    expanded = True
                    for match in matched_inputs:
                        expanded_patterns[match] = ""
        else:
            matched_inputs = fnmatch.filter(multiple_pattern_match, input)
            if matched_inputs:
                expanded = True
                for match in matched_inputs:
                    expanded_patterns[match] = ""

        if not expanded:
            expanded_patterns[input] = ""

    return list(expanded_patterns.keys())


def build_when_list(
    when_arg: Union[str, List[str]], obj: Any, directive_id: str, directive_name: str
) -> List[str]:
    """Construct list of when conditions based on a directives input argument
    Also, validate that when is passed in with the right type.

    Args:
        when_arg (str | list(str)): Single or list of string conditions that were input into
                                    the calling directive.
        obj: A ramble object (i.e. application, modifier, etc..)
        directive_id (str): Directive identifier. The calling directive can
                            define what is used here, but it should be
                            something that can help users identify where errors
                            from this method originate from.
        directive_name (str): Name of the calling directive

    Returns:
        List of strings, for all of the when conditions.
    """
    when_list = []
    if when_arg is not None:
        if isinstance(when_arg, str):
            when_arg = [when_arg]
        elif not isinstance(when_arg, list):
            if obj == "DirectiveMeta":
                raise DirectiveError(
                    "DirectiveMeta is unable to process an invalid `when` argument from directive "
                    f"{directive_name} {directive_id}. The `when` argument must be input as a "
                    "string or list."
                )

            else:
                raise DirectiveError(
                    f"Object {obj.name} calls directive {directive_name} {directive_id} "
                    f"with an invalid `when` argument. The `when` argument must be input as a "
                    "string or list."
                )
        when_list.extend(when_arg)
    return when_list

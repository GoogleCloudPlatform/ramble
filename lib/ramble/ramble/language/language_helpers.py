# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import fnmatch

from typing import List, Any

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

    all_types = []

    if single_type:
        all_types.append(single_type)

    if multiple_type:
        expanded_multiple_type = expand_patterns(multiple_type, multiple_pattern_match)
        all_types.extend(expanded_multiple_type)

    return all_types


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


def expand_patterns(multiple_type: list, multiple_pattern_match: list):
    """Expand wildcard patterns within a list of names

    This method takes an input list containing wildcard patterns and expands the
    wildcard with values matching a list of names. Returns a list containing
    matching names and any inputs with zero matches.

    Args:
        multiple_types: List of strings for type names, may contain wildcards
        multiple_pattern_match: List of strings to match against patterns in multiple_type

    Returns:
        List of expanded patterns matching the names list plus patterns
        not found in the names list.
    """

    expanded_patterns = []
    for input in multiple_type:
        matched_inputs = fnmatch.filter(multiple_pattern_match, input)
        if matched_inputs:
            for matching_name in matched_inputs:
                expanded_patterns.append(matching_name)
        else:
            expanded_patterns.append(input)

    return expanded_patterns


def build_when_list(
    when_arg: List[str], obj: Any, directive_id: str, directive_name: str
) -> List[str]:
    """Construct list of when conditions based on a directives input argument
    Also, validate that when is passed in with the right type.

    Args:
        when_arg (list(str)): List of string conditions that were input into
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
        if not isinstance(when_arg, list):
            raise DirectiveError(
                f"Object {obj.name} calls directive {directive_name} {directive_id} "
                f"with an invalid `when` argument. The `when` argument must be input as a list."
            )
        when_list.extend(when_arg)
    return when_list

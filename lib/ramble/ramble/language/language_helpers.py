# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import six

from ramble.language.language_base import DirectiveError


def merge_definitions(single_type, multiple_type):
    """Merge definitions of a type

    This method will merge two optional definitions of single_type and
    multiple_type.

    Args:
        single_type: Single string for type name
        multiple_type: List of strings for type names

    Returns:
        List of all type names (Merged if both single_type and multiple_type definitions are valid)
    """

    all_types = []

    if single_type:
        all_types.append(single_type)

    if multiple_type:
        all_types.extend(multiple_type)

    return all_types


def require_definition(single_type, multiple_type,
                       single_arg_name, multiple_arg_name,
                       directive_name):
    """Require at least one definition for a type in a directive

    This method will validate that single_type / multiple_type are properly defined.

    It will raise an error if at least one type is not defined, or if
    either are the incorrect type.

    Args:
        single_type: Single string for type name
        multiple_type: List of strings for type names
        single_arg_name: String name of the single_type argument in the directive
        multiple_arg_name: String name of the multiple_type argument in the directive
        directive_name: Name of the directive requiring a type

    Returns:
        List of all type names (Merged if both single_type and multiple_type definitions are valid)
    """

    if not (single_type or multiple_type):
        raise DirectiveError(f'Directive {directive_name} requires at least one of '
                             f'{single_arg_name} or {multiple_arg_name} to be defined.')

    if single_type and not isinstance(single_type, six.string_types):
        raise DirectiveError(f'Directive {directive_name} was given an invalid type '
                             f'for the {single_arg_name} argument. '
                             f'Type was {type(single_type)}')

    if multiple_type and not isinstance(multiple_type, list):
        raise DirectiveError(f'Directive {directive_name} was given an invalid type '
                             f'for the {multiple_arg_name} argument. '
                             f'Type was {type(multiple_type)}')

    return merge_definitions(single_type, multiple_type)

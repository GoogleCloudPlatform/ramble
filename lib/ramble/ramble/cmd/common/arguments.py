# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import argparse

from spack.util.pattern import Args

__all__ = ["add_common_arguments"]

#: dictionary of argument-generating functions, keyed by name
_arguments = {}


def arg(fn):
    """Decorator for a function that generates a common argument.

    This ensures that argument bunches are created lazily. Decorate
    argument-generating functions below with @arg so that
    ``add_common_arguments()`` can find them.

    """
    _arguments[fn.__name__] = fn
    return fn


def add_common_arguments(parser, list_of_arguments):
    """Extend a parser with extra arguments

    Args:
        parser: parser to be extended
        list_of_arguments: arguments to be added to the parser
    """
    for argument in list_of_arguments:
        if argument not in _arguments:
            message = 'Trying to add non existing argument "{0}" to a command'
            raise KeyError(message.format(argument))

        x = _arguments[argument]()
        parser.add_argument(*x.flags, **x.kwargs)


@arg
def yes_to_all():
    return Args(
        "-y",
        "--yes-to-all",
        action="store_true",
        dest="yes_to_all",
        help='assume "yes" is the answer to every confirmation request',
    )


@arg
def tags():
    return Args("-t", "--tags", action="append", help="filter a package query by tags")


@arg
def application():
    return Args("application", help="application name")


@arg
def workspace():
    return Args("workspace", help="workspace name")


@arg
def specs():
    return Args("specs", nargs=argparse.REMAINDER, help="one or more workload specs")


@arg
def obj_type():
    from ramble.repository import default_type, OBJECT_NAMES

    return Args(
        "--type",
        default=f"{default_type.name}",
        help=f"type of objects. Defaults to '{default_type.name}'. "
        f"Allowed types are {', '.join(OBJECT_NAMES)}",
    )


@arg
def repo_type():
    from ramble.repository import default_type, OBJECT_NAMES

    return Args(
        "-t",
        "--type",
        default="any",
        help=f"type of repositories to manage. Defaults to '{default_type.name}'. "
        f"Allowed types are {', '.join(OBJECT_NAMES)}, or any",
    )


@arg
def phases():
    return Args(
        "--phases",
        dest="phases",
        nargs="+",
        default=["*"],
        help="select phases to execute when performing setup. " + "Phase names support globbing",
        required=False,
    )


@arg
def include_phase_dependencies():
    return Args(
        "--include-phase-dependencies",
        dest="include_phase_dependencies",
        action="store_true",
        help="if set, phase dependencies are automatically added to "
        "the list of executed phases",
        required=False,
    )


@arg
def where():
    return Args(
        "--where",
        dest="where",
        nargs="+",
        action="append",
        help="inclusive filter on experiments where the provided logical statement is True",
        required=False,
    )


@arg
def exclude_where():
    return Args(
        "--exclude-where",
        dest="exclude_where",
        nargs="+",
        action="append",
        help="exclusive filter experiments where the provided logical statement is True",
        required=False,
    )


@arg
def filter_tags():
    return Args(
        "--filter-tags",
        action="append",
        nargs="+",
        help="filter experiments to only those that include the provided tags",
        required=False,
    )


@arg
def no_checksum():
    return Args(
        "-n",
        "--no-checksum",
        action="store_true",
        default=False,
        help="do not use checksums to verify downloaded files (unsafe)",
    )

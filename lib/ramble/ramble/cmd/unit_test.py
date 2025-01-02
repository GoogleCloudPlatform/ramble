# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import collections
import io
import sys
import re
import argparse

import llnl.util.tty.color as color
from llnl.util.filesystem import working_dir
from llnl.util.tty.colify import colify

import ramble.paths
import ramble.workspace
from ramble.util.logger import logger

description = "run ramble's unit tests (wrapper around pytest)"
section = "developer"
level = "long"


def setup_parser(subparser):
    subparser.add_argument(
        "-H",
        "--pytest-help",
        action="store_true",
        default=False,
        help="show full pytest help, with advanced options",
    )

    # extra ramble arguments to list tests
    list_group = subparser.add_argument_group("listing tests")
    list_mutex = list_group.add_mutually_exclusive_group()
    list_mutex.add_argument(
        "-l",
        "--list",
        action="store_const",
        default=None,
        dest="list",
        const="list",
        help="list test filenames",
    )
    list_mutex.add_argument(
        "-L",
        "--list-long",
        action="store_const",
        default=None,
        dest="list",
        const="long",
        help="list all test functions",
    )
    list_mutex.add_argument(
        "-N",
        "--list-names",
        action="store_const",
        default=None,
        dest="list",
        const="names",
        help="list full names of all tests",
    )

    # use tests for extension
    subparser.add_argument(
        "--extension", default=None, help="run test for a given ramble extension"
    )

    # spell out some common pytest arguments, so they'll show up in help
    pytest_group = subparser.add_argument_group(
        "common pytest arguments (ramble unit-test --pytest-help for more)"
    )
    pytest_group.add_argument(
        "-s",
        action="append_const",
        dest="parsed_args",
        const="-s",
        help="print output while tests run (disable capture)",
    )
    pytest_group.add_argument(
        "-k",
        action="store",
        metavar="EXPRESSION",
        dest="expression",
        help="filter tests by keyword (can also use w/list options)",
    )
    pytest_group.add_argument(
        "--showlocals",
        action="append_const",
        dest="parsed_args",
        const="--showlocals",
        help="show local variable values in tracebacks",
    )

    # remainder is just passed to pytest
    subparser.add_argument("pytest_args", nargs=argparse.REMAINDER, help="arguments for pytest")


def do_list(args, extra_args):
    """Print a lists of tests than what pytest offers."""
    # Run test collection and get the tree out.
    old_output = sys.stdout
    try:
        sys.stdout = output = io.StringIO()
        try:
            import pytest

            pytest.main(["--collect-only"] + extra_args)
        except ImportError:
            logger.die("Pytest python module not found. Ensure requirements.txt are installed.")
    finally:
        sys.stdout = old_output

    lines = output.getvalue().split("\n")
    tests = collections.defaultdict(set)
    prefix = []

    print("All lines =")
    print(lines)

    # collect tests into sections
    for line in lines:
        match = re.match(r"(\s*)<([^ ]*) '([^']*)'", line)
        if not match:
            continue
        indent, nodetype, name = match.groups()

        # strip parametrized tests
        if "[" in name:
            name = name[: name.index("[")]

        depth = len(indent) // 2

        if nodetype.endswith("Function"):
            key = tuple(prefix)
            tests[key].add(name)
            print(f"added test {key}={name} from {nodetype}")
        else:
            prefix = prefix[:depth]
            prefix.append(name)
            print(f"added prefix {name}")

    def colorize(c, prefix):
        if isinstance(prefix, tuple):
            return "::".join(color.colorize(f"@{c}{{{p}}}") for p in prefix if p != "()")
        return color.colorize(f"@{c}{{{prefix}}}")

    if args.list == "list":
        files = {prefix[0] for prefix in tests}
        color_files = [colorize("B", file) for file in sorted(files)]
        colify(color_files)

    elif args.list == "long":
        for prefix, functions in sorted(tests.items()):
            path = colorize("*B", prefix) + "::"
            functions = [colorize("c", f) for f in sorted(functions)]
            color.cprint(path)
            colify(functions, indent=4)
            print()

    else:  # args.list == "names"
        all_functions = [
            colorize("*B", prefix) + "::" + colorize("c", f)
            for prefix, functions in sorted(tests.items())
            for f in sorted(functions)
        ]
        colify(all_functions)


def add_back_pytest_args(args, unknown_args):
    """Add parsed pytest args, unknown args, and remainder together.

    We add some basic pytest arguments to the Ramble parser to ensure that
    they show up in the short help, so we have to reassemble things here.
    """
    result = args.parsed_args or []
    result += unknown_args or []
    result += args.pytest_args or []
    if args.expression:
        result += ["-k", args.expression]
    return result


def unit_test(parser, args, unknown_args):
    if args.pytest_help:
        # make the pytest.main help output more accurate
        sys.argv[0] = "ramble test"
        try:
            import pytest

            return pytest.main(["-h"])
        except ImportError:
            logger.die("Pytest python module not found. Ensure requirements.txt are installed.")

    # add back any parsed pytest args we need to pass to pytest
    pytest_args = add_back_pytest_args(args, unknown_args)

    # The default is to test the core of Ramble. If the option `--extension`
    # has been used, then test that extension.
    pytest_root = ramble.paths.ramble_root
    if args.extension:
        target = args.extension
        extensions = ramble.config.get("config:extensions")
        pytest_root = ramble.extensions.path_for_extension(target, *extensions)

    # pytest.ini lives in the root of the ramble repository.
    with working_dir(pytest_root):
        if args.list:
            do_list(args, pytest_args)
            return

        with ramble.workspace.no_active_workspace():
            try:
                import pytest

                return pytest.main(pytest_args)
            except ImportError:
                logger.die(
                    "Pytest python module not found. Ensure requirements.txt are installed."
                )

# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import argparse
import os
import re
import shutil
import sys
import tempfile

from llnl.util.filesystem import working_dir, mkdirp

import ramble.paths
from spack.util.executable import which, ProcessError


description = "runs source code style checks on Ramble."
section = "developer"
level = "long"


def is_object(f):
    """Whether flake8 should consider a file as a core file or an object (application or modifier).

    We run flake8 with different exceptions for the core and for
    applications, since we allow `from ramble import *` and poking globals
    into applications.
    """
    return f.startswith("var/ramble/repos/") or "docs/tutorial/examples" in f


#: List of directories to exclude from checks.
exclude_directories = [ramble.paths.external_path]

#: max line length we're enforcing (note: this duplicates what's in .flake8)
max_line_length = 99

common_object_exemptions = {
    # Exempt lines with urls and descriptions from overlong line errors.
    "E501": [
        r"^\s*homepage\s*=",
        r"^\s*url\s*=",
        r"^\s*git\s*=",
        r"^\s*svn\s*=",
        r"^\s*hg\s*=",
        r"^\s*list_url\s*=",
        r"^\s*version\(",
        r"^\s*variant\(",
        r"^\s*provides\(",
        r"^\s*extends\(",
        r"^\s*depends_on\(",
        r"^\s*conflicts\(",
        r"^\s*resource\(",
        r"^\s*patch\(",
    ],
    # Exempt '@when' decorated functions from redefinition errors.
    "F811": [
        r"^\s*@when\(.*\)",
    ],
}

#: This is a dict that maps:
#:  filename pattern ->
#:     flake8 exemption code ->
#:        list of patterns, for which matching lines should have codes applied.
#:
#: For each file, if the filename pattern matches, we'll add per-line
#: exemptions if any patterns in the sub-dict match.
pattern_exemptions = {
    # exemptions applied only to application.py files.
    r"application.py$": {
        # Allow 'from ramble.appkit import *' in applications,
        # but no other wildcards
        "F403": [r"^from ramble.appkit import \*$"],
        **common_object_exemptions,
    },
    # exemptions applied only to modifier.py files.
    r"modifier.py$": {
        # Allow 'from ramble.modkit import *' in applications,
        # but no other wildcards
        "F403": [r"^from ramble.modkit import \*$"],
        **common_object_exemptions,
    },
    # exemptions applied only to package_manager.py files.
    r"package_manager.py$": {
        # Allow 'from ramble.modkit import *' in applications,
        # but no other wildcards
        "F403": [r"^from ramble.pkgmankit import \*$"],
        **common_object_exemptions,
    },
    # exemptions applied to all files.
    r".py$": {
        "E501": [
            r"(https?|ftp|file)\:",  # URLs
            r'([\'"])[0-9a-fA-F]{32,}\1',  # long hex checksums
        ]
    },
}

# compile all regular expressions.
pattern_exemptions = {
    re.compile(file_pattern): {
        code: [re.compile(p) for p in patterns] for code, patterns in error_dict.items()
    }
    for file_pattern, error_dict in pattern_exemptions.items()
}

# Tools run in the given order, with flake8 as the last check.
tool_names = ["black", "flake8"]

tools = {}


#: decorator for adding tools to the list
class tool:
    def __init__(self, name):
        self.name = name

    def __call__(self, fun):
        tools[self.name] = fun
        return fun


def changed_files(base=None, untracked=True, all_files=False):
    """Get list of changed files in the Ramble repository."""

    git = which("git", required=True)

    if base is None:
        base = os.environ.get("GITHUB_BASE_REF", "develop")

    range = f"{base}..."

    git_args = [
        # Add changed files committed since branching off of develop
        ["diff", "--name-only", "--diff-filter=ACMR", range],
        # Add changed files that have been staged but not yet committed
        ["diff", "--name-only", "--diff-filter=ACMR", "--cached"],
        # Add changed files that are unstaged
        ["diff", "--name-only", "--diff-filter=ACMR"],
    ]

    # Add new files that are untracked
    if untracked:
        git_args.append(["ls-files", "--exclude-standard", "--other"])

    # add everything if the user asked for it
    if all_files:
        git_args.append(["ls-files", "--exclude-standard"])
    excludes = [os.path.realpath(f) for f in exclude_directories]
    changed = set()

    for arg_list in git_args:
        files = git(*arg_list, output=str, error=str).split("\n")

        for f in files:
            # Ignore non-Python files
            if not (f.endswith(".py") or f == "bin/ramble"):
                continue

            # Ignore files in the exclude locations
            if any(os.path.realpath(f).startswith(e) for e in excludes):
                continue

            # Exclude non-existent files
            if not os.path.exists(f):
                continue

            changed.add(f)

    return sorted(changed)


def setup_parser(subparser):
    subparser.add_argument(
        "-b",
        "--base",
        action="store",
        default=None,
        help="select base branch for collecting list of modified files",
    )
    subparser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="check all files, not just changed files",
    )
    subparser.add_argument(
        "-o",
        "--output",
        action="store_true",
        help="send filtered files to stdout as well as temp files",
    )
    subparser.add_argument(
        "-r",
        "--root-relative",
        action="store_true",
        default=False,
        help="print root-relative paths (default: cwd-relative)",
    )
    subparser.add_argument(
        "-U",
        "--no-untracked",
        dest="untracked",
        action="store_false",
        default=True,
        help="exclude untracked files from checks",
    )
    subparser.add_argument(
        "-f",
        "--fix",
        action="store_true",
        default=False,
        help="format automatically if possible with black",
    )
    subparser.add_argument(
        "-k",
        "--keep-temp",
        action="store_true",
        help="do not delete temporary directory where flake8 runs. "
        "use for debugging, to see filtered files",
    )
    tool_group = subparser.add_mutually_exclusive_group()
    tool_group.add_argument(
        "-t",
        "--tool",
        action="append",
        help="specify which tools to run (default: %s)" % ",".join(tool_names),
    )
    tool_group.add_argument(
        "-s",
        "--skip",
        action="append",
        help="specify tools to skip (choose from %s)" % ",".join(tool_names),
    )
    subparser.add_argument("files", nargs=argparse.REMAINDER, help="specific files to check")


def print_tool_header(tool, file_list):
    print("=======================================================")
    print(f"{tool}: running {tool} checks on ramble.")
    print()
    print("Modified files:")
    for filename in file_list:
        print(f"  {filename.strip()}")
    print("=======================================================")


def print_tool_result(tool, returncode):
    if returncode == 0:
        print(f"  {tool} checks were clean")
    else:
        print(f"  {tool} found errors")


def print_output(output, args):
    if args.root_relative:
        # print results relative to repo root.
        print(output)
    else:
        # print results relative to current working directory
        def cwd_relative(path):
            return "{}: [".format(
                os.path.relpath(os.path.join(ramble.paths.prefix, path.group(1)), os.getcwd())
            )

        for line in output.split("\n"):
            print(re.sub(r"^(.*): \[", cwd_relative, line))


def add_pattern_exemptions(line, codes):
    """Add a flake8 exemption to a line."""
    if line.startswith("#"):
        return line

    line = line.rstrip("\n")

    # Line is already ignored
    if line.endswith("# noqa"):
        return line + "\n"

    orig_len = len(line)
    codes = set(codes)

    # don't add E501 unless the line is actually too long, as it can mask
    # other errors like trailing whitespace
    if orig_len <= max_line_length and "E501" in codes:
        codes.remove("E501")
        if not codes:
            return line + "\n"

    exemptions = ",".join(sorted(codes))

    # append exemption to line
    if "# noqa: " in line:
        line += f",{exemptions}"
    elif line:  # ignore noqa on empty lines
        line += f"  # noqa: {exemptions}"

    # if THIS made the line too long, add an exemption for that
    if len(line) > max_line_length and orig_len <= max_line_length:
        line += ",E501"

    return line + "\n"


def filter_file(source, dest, output=False):
    """Filter a single file through all the patterns in pattern_exemptions."""

    # Prior to Python 3.8, `noqa: F811` needed to be placed on the `@when` line
    # Starting with Python 3.8, it must be placed on the `def` line
    # https://gitlab.com/pycqa/flake8/issues/583
    ignore_f811_on_previous_line = False

    if not os.path.isfile(source):
        return

    with open(source) as infile:
        parent = os.path.dirname(dest)
        mkdirp(parent)

        with open(dest, "w") as outfile:
            for line in infile:
                line_errors = []

                # pattern exemptions
                for file_pattern, errors in pattern_exemptions.items():
                    if not file_pattern.search(source):
                        continue

                    for code, patterns in errors.items():
                        for pattern in patterns:
                            if pattern.search(line):
                                line_errors.append(code)
                                break

                if "F811" in line_errors:
                    ignore_f811_on_previous_line = True
                elif ignore_f811_on_previous_line:
                    line_errors.append("F811")
                    ignore_f811_on_previous_line = False

                if line_errors:
                    line = add_pattern_exemptions(line, line_errors)

                outfile.write(line)
                if output:
                    sys.stdout.write(line)


def _split_file_list(file_list):
    """Return a tuple of (primary_files, obj_files)"""
    return [f for f in file_list if not is_object(f)], [f for f in file_list if is_object(f)]


@tool("flake8")
def run_flake8(flake8_cmd, file_list, args):
    temp = tempfile.mkdtemp()
    returncode = 1
    try:
        print_tool_header("flake8", file_list)

        # run flake8 on the temporary tree, once for core, once for apps
        primary_file_list, application_file_list = _split_file_list(file_list)

        # filter files into a temporary directory with exemptions added.
        # TODO: DRY this duplication
        primary_dest_dir = os.path.join(temp, "primary")
        mkdirp(primary_dest_dir)
        for filename in primary_file_list:
            src_path = os.path.join(ramble.paths.prefix, filename)
            dest_path = os.path.join(primary_dest_dir, filename)
            filter_file(src_path, dest_path, args.output)

        application_dest_dir = os.path.join(temp, "application")
        mkdirp(application_dest_dir)
        for filename in application_file_list:
            src_path = os.path.join(ramble.paths.prefix, filename)
            dest_path = os.path.join(application_dest_dir, filename)
            filter_file(src_path, dest_path, args.output)

        returncode = 0
        output = ""

        # TODO: make these repeated blocks a function?
        if primary_file_list:
            # Copy flake8 file so the paths will be relative to the new location
            f = ".flake8"
            shutil.copy(f, primary_dest_dir)
            qa_dir = os.path.join(primary_dest_dir, "share", "ramble", "qa")
            os.makedirs(qa_dir, exist_ok=True)
            shutil.copy("share/ramble/qa/flake8_formatter.py", qa_dir)

            with working_dir(primary_dest_dir):
                output += flake8_cmd(
                    "--format",
                    "pylint",
                    f"--config={f}",
                    ".",
                    fail_on_error=False,
                    output=str,
                )
                returncode |= flake8_cmd.returncode

        if application_file_list:
            f = ".flake8_applications"
            shutil.copy(f, application_dest_dir)

            with working_dir(application_dest_dir):
                output += flake8_cmd(
                    "--format",
                    "pylint",
                    f"--config={f}",
                    ".",
                    fail_on_error=False,
                    output=str,
                )
                returncode |= flake8_cmd.returncode

        print_output(output, args)

    finally:
        if args.keep_temp:
            print("Temporary files are in: ", temp)
        else:
            shutil.rmtree(temp, ignore_errors=True)

    print_tool_result("flake8", returncode)
    return returncode


@tool("black")
def run_black(black_cmd, file_list, args):
    print_tool_header("black", file_list)
    common_args = ("--config", os.path.join(ramble.paths.prefix, "pyproject.toml"))
    if not args.fix:
        common_args += ("--check", "--diff")
    primary_files, obj_files = _split_file_list(file_list)
    output = ""
    returncode = 0

    # Operate on primary and object (apps and mods) files spearately with varying configs.
    if primary_files:
        output += black_cmd(
            *(common_args + tuple(primary_files)), fail_on_error=False, output=str, error=str
        )
        returncode |= black_cmd.returncode

    if obj_files:
        output += black_cmd(
            *(common_args + ("--config", "pyproject_objects.toml") + tuple(obj_files)),
            fail_on_error=False,
            output=str,
            error=str,
        )
        returncode |= black_cmd.returncode

    print_output(output, args)
    print_tool_result("black", returncode)
    return returncode


def validate_toolset(arg_value):
    """Validate --tool and --skip arguments (sets of optionally comma-separated tools)."""
    tools = set(",".join(arg_value).split(","))  # allow args like 'black,flake8'
    for tool in tools:
        if tool not in tool_names:
            print(f"Invalid tool: {tool}, choose from: {', '.join(tool_names)}")
    return tools


def style(parser, args):
    file_list = args.files
    if file_list:

        def prefix_relative(path):
            return os.path.relpath(os.path.abspath(os.path.realpath(path)), ramble.paths.prefix)

        file_list = [prefix_relative(p) for p in file_list]

    # process --tool and --skip arguments
    selected = set(tool_names)
    if args.tool is not None:
        selected = validate_toolset(args.tool)
    if args.skip is not None:
        selected -= validate_toolset(args.skip)

    if not selected:
        print("Nothing to run.")
        return

    tools_to_run = [t for t in tool_names if t in selected]

    returncode = 0

    with working_dir(ramble.paths.prefix):
        arg_flags = []
        # First, try with the original flags
        arg_flags.append([args.base, args.untracked, args.all])
        # Next, try with the a base of `origin/develop`
        arg_flags.append(["origin/develop", args.untracked, args.all])
        # Next, try with the a base of `origin/main`
        arg_flags.append(["origin/main", args.untracked, args.all])
        # Next, force listing all files
        arg_flags.append(["HEAD", args.untracked, True])
        while not file_list:
            try:
                base, untracked, list_all = arg_flags.pop(0)
                file_list = changed_files(base, untracked, list_all)
                break
            except ProcessError as e:
                file_list = None
                if not arg_flags:
                    raise e

        for tool_name in tools_to_run:
            print(f"Running {tool_name} check")
            returncode |= tools[tool_name](which(tool_name, required=True), file_list, args)

    if returncode != 0:
        print("style checks found errors.")
        sys.exit(1)
    else:
        print("style checks were clean.")

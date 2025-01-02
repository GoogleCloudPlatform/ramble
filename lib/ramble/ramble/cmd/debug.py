# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import os
import platform
import re
from datetime import datetime

from llnl.util.filesystem import working_dir

import ramble.config
import ramble.paths
from ramble.main import get_version

import spack.platforms
from spack.util.executable import which

description = "debugging commands for troubleshooting Ramble"
section = "developer"
level = "long"


def setup_parser(subparser):
    sp = subparser.add_subparsers(metavar="SUBCOMMAND", dest="debug_command")
    sp.add_parser("report", help="print information useful for bug reports")


def _debug_tarball_suffix():
    now = datetime.now()
    suffix = now.strftime("%Y-%m-%d-%H%M%S")

    git = which("git")
    if not git:
        return "nobranch-nogit-%s" % suffix

    with working_dir(ramble.paths.prefix):
        if not os.path.isdir(".git"):
            return "nobranch.nogit.%s" % suffix

        # Get symbolic branch name and strip any special chars (mainly '/')
        symbolic = git("rev-parse", "--abbrev-ref", "--short", "HEAD", output=str).strip()
        symbolic = re.sub(r"[^\w.-]", "-", symbolic)

        # Get the commit hash too.
        commit = git("rev-parse", "--short", "HEAD", output=str).strip()

        if symbolic == commit:
            return f"nobranch.{commit}.{suffix}"
        else:
            return f"{symbolic}.{commit}.{suffix}"


def report(args):
    host_platform = spack.platforms.host()
    host_os = host_platform.operating_system("frontend")
    host_target = host_platform.target("frontend")
    architecture = spack.spec.ArchSpec((str(host_platform), str(host_os), str(host_target)))
    print("* **Ramble:**", get_version())
    print("* **Python:**", platform.python_version())
    print("* **Platform:**", architecture)


def debug(parser, args):
    action = {
        "report": report,
    }
    action[args.debug_command](args)

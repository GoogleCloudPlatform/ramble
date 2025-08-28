# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# flake8: noqa: F401
"""pkgmankit is a set of useful modules to import when writing package managers"""

import os

import llnl.util.filesystem
from llnl.util.filesystem import *

import ramble.language.package_manager_language
import ramble.repository
from ramble.error import PackageManagerError
from ramble.language.package_manager_language import *
from ramble.language.shared_language import *
from ramble.software_environments import ExternalEnvironment
from ramble.software_info import SoftwareInfo
from ramble.spec import Spec
from ramble.util.command_runner import (
    CommandRunner,
    NoPathRunnerError,
    RunnerError,
    ValidationFailedError,
)

# Rename logger to tty to preserve old behavior
from ramble.util.logger import logger
from ramble.util.logger import logger as tty
from ramble.util.output_capture import OUTPUT_CAPTURE

PackageManagerBase = ramble.repository.get_base_class("package-manager-base")

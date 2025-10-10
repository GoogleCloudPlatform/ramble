# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# flake8: noqa: F401
"""appkit is a set of useful build tools and directives for applications.

Everything in this module is automatically imported into Ramble application files.
"""

import llnl.util.filesystem
from llnl.util.filesystem import *

import ramble.language.application_language
from ramble.repository import get_base_class

ExecutableApplication = get_base_class("executable-application")
ApplicationBase = get_base_class("application-base")

from ramble.language.application_language import *
from ramble.language.shared_language import *
from ramble.spec import Spec
from ramble.util.command_runner import (
    CommandRunner,
    NoPathRunnerError,
    RunnerError,
    ValidationFailedError,
)
from ramble.util.file_util import get_file_path
from ramble.util.foms import FomType

# Import new logger as tty to preserve old behavior
from ramble.util.logger import logger

tty = logger
from ramble.util.output_capture import OUTPUT_CAPTURE

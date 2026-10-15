# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# flake8: noqa: F401
"""toolkit is a set of useful build tools and directives for external dependencies.

Everything in this module is automatically imported into Ramble external dependency files.
"""

import llnl.util.filesystem
from llnl.util.filesystem import *

import ramble.language.utility_language
from ramble.language.shared_language import *
from ramble.language.utility_language import *
from ramble.repository import get_base_class
from ramble.spec import Spec
from ramble.util.command_runner import (
    CommandRunner,
    NoPathRunnerError,
    RunnerError,
    ValidationFailedError,
)
from ramble.util.file_util import get_file_path
from ramble.util.logger import logger
from ramble.util.output_capture import OUTPUT_CAPTURE

UtilityBase = get_base_class("utility-base")

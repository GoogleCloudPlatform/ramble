# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# flake8: noqa: F401
"""modkit is a set of useful modules to import when writing modifiers"""

import llnl.util.filesystem
from llnl.util.filesystem import *

import ramble.language.modifier_language
import ramble.repository
from ramble.language.modifier_language import *
from ramble.language.shared_language import *
from ramble.spec import Spec
from ramble.util.command_runner import (
    CommandRunner,
    NoPathRunnerError,
    RunnerError,
    ValidationFailedError,
)
from ramble.util.file_util import get_file_path

# Rename logger to tty to preserve old behavior
from ramble.util.logger import logger
from ramble.util.logger import logger as tty
from ramble.util.output_capture import OUTPUT_CAPTURE

base_class_type = ramble.repository.ObjectTypes.base_classes
ModifierBase = ramble.repository.get_obj_class("modifier-base", object_type=base_class_type)
BasicModifier = ramble.repository.get_obj_class("basic-modifier", object_type=base_class_type)
DisabledModifier = ramble.repository.get_obj_class(
    "disabled-modifier", object_type=base_class_type
)

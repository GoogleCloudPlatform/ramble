# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import deprecation
import ramble
from ramble.util.logger import logger


description = "(deprecated) list and get information on available modifiers"
section = "basic"
level = "short"


def setup_parser(subparser):
    pass


@deprecation.deprecated(
    deprecated_in="0.5.0",
    removed_in="0.6.0",
    current_version=str(ramble.ramble_version),
    details="Use `ramble list --type modifiers` or `ramble info --type modifiers` instead",
)
def mods(parser, args):
    """Look for a function called mods_<name> and call it."""

    logger.warn("Command is deprecated. Use alternate commands instead.")

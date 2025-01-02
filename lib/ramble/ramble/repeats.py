# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.util.logger import logger


class Repeats:
    """Class to represent configuration of experiment repeats"""

    def __init__(self):
        """Constructor for a Repeats object

        Creates a Repeats object with default setting of 'no repeats'."""
        self.n_repeats = 0
        self.is_repeat_base = False
        self.repeat_index = None

    def set_repeats(self, is_repeat_base, n_repeats):
        """Set if this instance will use repeats

        Args:
            is_repeat_base (Bool): True if this is the base experiment of a repeat set,
                                   False for singletons and for repeats
            n_repeats (Int): 0 for singletons and repeats, positive integer for base
                             experiment
        """
        if (is_repeat_base and n_repeats > 0) or (not is_repeat_base and n_repeats == 0):
            self.is_repeat_base = is_repeat_base
            self.n_repeats = n_repeats
            self.repeat_index = None
        else:
            logger.die(
                f"Failed to set repeats with is_repeats_base = {is_repeat_base}"
                f"and n_repeats = {n_repeats}."
            )

    def set_repeat_index(self, index):
        """Set the index for an instance of a repeated experiment"""
        self.n_repeats = 0
        self.is_repeat_base = False
        self.repeat_index = index

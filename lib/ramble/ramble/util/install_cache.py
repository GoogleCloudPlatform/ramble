# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""Provide data structures to assist with caching operations"""


class SetCache:
    def __init__(self):
        self.store = set()

    def add(self, tupl):
        self.store.add(tupl)

    def contains(self, tupl):
        return tupl in self.store

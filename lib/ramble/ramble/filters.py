# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import itertools


class Filters(object):
    """Object containing filters for limiting various operations in Ramble"""

    def __init__(self, phase_filters=['*'],
                 include_where_filters=None,
                 exclude_where_filters=None):
        """Create a new filter instance"""

        self.phases = phase_filters
        self.include_where = None
        self.exclude_where = None
        if include_where_filters:
            self.include_where = list(itertools.chain.from_iterable(include_where_filters))
        if exclude_where_filters:
            self.exclude_where = list(itertools.chain.from_iterable(exclude_where_filters))

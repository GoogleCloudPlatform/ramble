# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

"""This file dispatches to the correct implementation of OrderedDict."""

# TODO: this file, along with py26/ordereddict.py, can be removed when
# TODO: support for python 2.6 will be dropped

# Removing this import will make python 2.6
# fail on import of ordereddict
from __future__ import absolute_import

import sys

if sys.version_info[:2] == (2, 6):
    import ordereddict
    OrderedDict = ordereddict.OrderedDict
else:
    import collections
    OrderedDict = collections.OrderedDict

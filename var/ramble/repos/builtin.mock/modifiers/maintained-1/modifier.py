# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


class Maintained1(BasicModifier):
    """Define a maintained modifier"""
    name = "maintained-1"

    tags('test')

    maintainers('maintainer-1')

    mode('test', description='This is a test mode')

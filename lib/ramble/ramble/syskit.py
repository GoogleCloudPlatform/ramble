# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.language.shared_language import *  # noqa: F401, F403
from ramble.language.system_language import *  # noqa: F401, F403
from ramble.repository import get_base_class

SystemBase = get_base_class("system-base")

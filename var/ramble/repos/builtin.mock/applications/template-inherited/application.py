# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.app.builtin.mock.template import Template as TemplateBase
from ramble.appkit import *


class TemplateInherited(TemplateBase):
    """An app for testing object templates inheritance."""

    name = "template-inherited"

    workload_variable(
        "hello_name",
        default="world-inherited",
        description="hello name",
        workload="test_template",
    )

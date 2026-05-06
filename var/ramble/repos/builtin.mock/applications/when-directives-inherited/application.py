# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.app.builtin.mock.when_directives import WhenDirectives
from ramble.appkit import *


class WhenDirectivesInherited(WhenDirectives):
    name = "when-directives-inherited"

    log_file = "{experiment_run_dir}/test.out"
    always_on_fom_regex = (
        r"(?P<when_context>test inheritance)\s+(?P<inherited_fom>[0-9]+).*"
    )

    variant(
        "register_inherited_fom_when",
        default=False,
        values=[True, False],
        description="Register figure of merit to overwrite inherited FOM",
    )

    with when("+register_inherited_fom_when"):
        figure_of_merit_context(
            "always_context",
            regex=always_on_fom_regex,
            output_format="{when_context}",
        )

        figure_of_merit(
            "test_always_on_fom",
            fom_regex=always_on_fom_regex,
            group_name="inherited_fom",
            units="integer",
            log_file=log_file,
            contexts=["always_context"],
        )

# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class PrepareAnalysis(BasicModifier):
    """Define a modifier that defines a prepare_analysis hook"""

    name = "prepare-analysis"

    tags("test")

    mode("test", description="This is a test mode")

    _log_file = "{experiment_run_dir}/.prepare_analysis_hook_data"

    modifier_variable(
        "test-var",
        default="This test worked",
        description="tuned profile to use",
        mode="test",
    )

    figure_of_merit(
        "test-fom",
        fom_regex="Test fom = (?P<fom>.*)",
        log_file=_log_file,
        units="",
        group_name="fom",
    )

    def _prepare_analysis(self, workspace):
        with open(self.expander.expand_var(self._log_file), "w+") as f:
            to_write = self.expander.expand_var("{test-var}")
            f.write(f"Test fom = {to_write}")

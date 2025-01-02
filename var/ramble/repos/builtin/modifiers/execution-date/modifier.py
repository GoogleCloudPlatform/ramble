# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class ExecutionDate(BasicModifier):
    """Define a modifier to print the date"""

    name = "execution-date"

    maintainers("rfbgo")

    mode("standard", description="Standard execution mode")

    executable_modifier("get_startend_date")

    modifier_variable(
        "date_format",
        default="",
        description="Date args to format output",
        mode="standard",
    )

    def get_startend_date(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        if hasattr(self, "_already_applied"):
            return [], []

        self._already_applied = True

        pre_cmds = []
        post_cmds = []

        pre_cmds.append(
            CommandExecutable(
                "start-date",
                template=[self.expander.expand_var("date {date_format}")],
                redirect="{experiment_run_dir}/start_date",
            )
        )
        post_cmds.append(
            CommandExecutable(
                "end-date",
                template=[self.expander.expand_var("date {date_format}")],
                redirect="{experiment_run_dir}/end_date",
            )
        )
        return pre_cmds, post_cmds

    figure_of_merit(
        "Start Date",
        fom_regex=r"(?P<date>.*)",
        log_file="{experiment_run_dir}/start_date",
        group_name="date",
        units="",
    )

    figure_of_merit(
        "End Date",
        fom_regex=r"(?P<date>.*)",
        log_file="{experiment_run_dir}/end_date",
        group_name="date",
        units="",
    )

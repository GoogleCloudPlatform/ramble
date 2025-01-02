# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.modkit import *


SUCCESS_STRING = "Status: SUCCESS"


class TunedAdm(BasicModifier):
    """Define a modifier for TunedAdm

    This modifier is used to select a specific tuned profile.
    It also records the selected profile as a FOM.
    """

    name = "tuned-adm"

    tags("system-info", "sysinfo", "platform-info")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode for tuned-adm")

    software_spec("pdsh", pkg_spec="pdsh", package_manager="spack*")

    required_variable("hostlist")

    modifier_variable(
        "tuned-profile",
        default="google-hpc-compute-throughput",
        description="tuned profile to use",
        mode="standard",
    )

    register_builtin("set_tuning_profile")

    def set_tuning_profile(self):
        return [
            "pdsh -R ssh -w {hostlist} sudo tuned-adm profile {tuned-profile}",
            "pdsh -R ssh -w {hostlist} sudo tuned-adm active > {experiment_run_dir}/tuning_profile",
        ]

    def _prepare_analysis(self, workspace):
        run_dir = self.expander.expand_var("{experiment_run_dir}")
        read_profile_path = os.path.join(run_dir, "tuning_profile")

        if not os.path.exists(read_profile_path):
            return

        profiles = set()
        with open(read_profile_path) as f:

            for line in f.readlines():
                if "active profile:" in line:
                    profiles.add(line.split(":")[-1].strip())
            profiles_str = ",".join(profiles)

        if profiles:
            expected_profile = self.expander.expand_var("{tuned-profile}")
            write_profile_path = os.path.join(run_dir, "all_tuning_profiles")
            with open(write_profile_path, "w+") as f:
                profiles_str = ",".join(profiles)
                f.write(f"Applied profiles: {profiles_str}\n")
                if len(profiles) == 1 and profiles_str == expected_profile:
                    f.write(SUCCESS_STRING)

    figure_of_merit(
        "Tuning Profile",
        fom_regex=r"Applied profiles:\s*(?P<profile>.*)",
        log_file="{experiment_run_dir}/all_tuning_profiles",
        group_name="profile",
        units="",
    )

    success_criteria(
        "Expected tuning profile applied",
        mode="string",
        match=SUCCESS_STRING,
        file="{experiment_run_dir}/all_tuning_profiles",
    )

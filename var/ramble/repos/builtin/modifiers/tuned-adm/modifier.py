# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

from ramble.modkit import *


class TunedAdm(BasicModifier):
    """Define a modifier for TunedAdm

    This modifier is used to select a specific tuned profile.
    It also records the selected profile as a FOM.
    """

    name = "tuned-adm"

    tags("system-info", "sysinfo", "platform-info")

    maintainers("douglasjacobsen")

    mode("standard", description="Standard execution mode for tuned-adm")

    software_spec(
        "pdsh", pkg_spec="pdsh", when=["package_manager_family=spack"]
    )

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
        with open(read_profile_path, encoding="utf-8") as f:
            for line in f:
                if "active profile:" in line:
                    profiles.add(line.split(":")[-1].strip())

        if profiles:
            profiles_str = ",".join(sorted(profiles))
            self.add_inmem_fom_value("tuned_adm_profiles", profiles_str)

    figure_of_merit(
        "Tuning Profile",
        fom_map_key="tuned_adm_profiles",
        units="",
    )

    success_criteria(
        "Expected tuning profile applied",
        mode="fom_comparison",
        fom_name="Tuning Profile",
        formula="'{value}' == '{tuned-profile}'",
    )

# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class ExecModUsageFilters(BasicModifier):
    """Define a modifier to test usage filters on executable modifiers"""

    name = "exec-mod-usage-filters"

    tags("test")

    mode("test", description="This is a test mode")
    default_mode("test")

    modifier_conflict(MODIFIER_CONFLICT.name_mode_executables)

    variant(
        "usage_filter_type",
        default="none",
        values=["none", "once", "all_mpi", "first_mpi", "broken"],
        description="Control which usage filter to use on exec mods",
    )

    executable_modifier(
        "exec_mod_none", usage_filter=None, when=["usage_filter_type=none"]
    )

    def exec_mod_none(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_cmds = [
            CommandExecutable(
                "exec-mod-none-pre", template=["exec_mod_none_pre_applied"]
            )
        ]

        post_cmds = [
            CommandExecutable(
                "exec-mod-once-post", template=["exec_mod_none_post_applied"]
            )
        ]

        return pre_cmds, post_cmds

    executable_modifier(
        "exec_mod_once", usage_filter="once", when=["usage_filter_type=once"]
    )

    def exec_mod_once(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_cmds = [
            CommandExecutable(
                "exec-mod-once-pre", template=["exec_mod_once_pre_applied"]
            )
        ]

        post_cmds = [
            CommandExecutable(
                "exec-mod-once-post", template=["exec_mod_once_post_applied"]
            )
        ]

        return pre_cmds, post_cmds

    executable_modifier(
        "exec_mod_first_mpi",
        usage_filter="first_mpi",
        when=["usage_filter_type=first_mpi"],
    )

    def exec_mod_first_mpi(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_cmds = [
            CommandExecutable(
                "exec-mod-first-mpi-pre",
                template=["exec_mod_first_mpi_pre_applied"],
            )
        ]

        post_cmds = [
            CommandExecutable(
                "exec-mod-first-mpi-post",
                template=["exec_mod_first_mpi_post_applied"],
            )
        ]

        return pre_cmds, post_cmds

    executable_modifier(
        "exec_mod_all_mpi",
        usage_filter="all_mpi",
        when=["usage_filter_type=all_mpi"],
    )

    def exec_mod_all_mpi(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_cmds = [
            CommandExecutable(
                "exec-mod-all-mpi-pre",
                template=["exec_mod_all_mpi_pre_applied"],
            )
        ]

        post_cmds = [
            CommandExecutable(
                "exec-mod-all-mpi-post",
                template=["exec_mod_all_mpi_post_applied"],
            )
        ]

        return pre_cmds, post_cmds

    executable_modifier(
        "exec_mod_broken",
        usage_filter="__broken__",
        when=["usage_filter_type=broken"],
    )

    def exec_mod_broken(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_cmds = [
            CommandExecutable(
                "exec-mod-all-mpi-pre",
                template=["exec_mod_all_mpi_pre_applied"],
            )
        ]

        post_cmds = [
            CommandExecutable(
                "exec-mod-all-mpi-post",
                template=["exec_mod_all_mpi_post_applied"],
            )
        ]

        return pre_cmds, post_cmds

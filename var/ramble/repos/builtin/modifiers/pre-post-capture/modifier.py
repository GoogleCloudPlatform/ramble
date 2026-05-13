# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import fnmatch
import shlex

from ramble.modkit import *


class PrePostCapture(BasicModifier):
    """A modifier to inject command captures before and after certain executable commands.
    Useful for collecting debugging information at the beginning and end of an experiment.
    """

    name = "pre-post-capture"

    maintainers("douglasjacobsen")
    tags("debugging")

    mode("common", description="Mode for collecting common debugging captures")

    default_mode("common")

    modifier_variable(
        "pre_post_capture_exec_pattern",
        default="all_executables",
        description="Regex pattern to control which executables to capture. "
        "If set to 'all_executables', will only inject one pre and post "
        "capture at the start and end of the experiment.",
        modes=["*"],
    )

    modifier_variable(
        "pre_post_capture_names",
        expandable=False,
        default=["dmesg", "time"],
        description="Names to apply to captures",
        mode="common",
    )

    modifier_variable(
        "pre_post_capture_commands",
        expandable=False,
        default=[
            "sudo journalctl -k",
            "date +%s",
        ],
        description="Commands to captures",
        mode="common",
    )

    modifier_variable(
        "pre_post_capture_log_prefix",
        default="{experiment_run_dir}/pre_post_capture/pre_post_capture",
        description="Directory to store capture output",
        modes=["*"],
    )

    register_template(
        "pre_post_capture_collector",
        src_path="pre_post_capture_collector.sh.tpl",
        dest_path="pre_post_capture_collector.sh",
    )

    required_variable("hostlist")
    required_variable("hostfile")

    archive_pattern("{pre_post_capture_log_prefix}*")

    executable_modifier("inject_pre_post_captures")

    def inject_pre_post_captures(
        self, executable_name, executable, app_inst=None
    ):
        # Setup the executable names filter
        if not hasattr(self, "_exec_names_setup"):
            self._capture_names = self.expander.expand_var(
                "{pre_post_capture_names}", typed=True
            )
            self._capture_commands = self.expander.expand_var(
                "{pre_post_capture_commands}", typed=True
            )

            if not isinstance(self._capture_names, list):
                return [], []

            self._exec_names_setup = True
            self._pre_exec_names = set()
            self._post_exec_names = set()
            exec_pattern = self.expander.expand_var(
                "{pre_post_capture_exec_pattern}"
            )

            if not app_inst:
                app_inst = self._get_app_inst()

            exec_graph = app_inst.get_executable_graph(
                app_inst.expander.workload_name
            )
            last_exec = None
            node_idx = 0
            added = False
            for exec_node in exec_graph.walk():
                if isinstance(
                    exec_node.attribute,
                    ramble.util.executable.CommandExecutable,
                ):
                    if exec_pattern == "all_executables":
                        if node_idx == 0:
                            self._pre_exec_names.add(exec_node.key)
                        last_exec = exec_node.key
                        added = True
                    elif fnmatch.fnmatch(exec_node.key, exec_pattern):
                        self._pre_exec_names.add(exec_node.key)
                        self._post_exec_names.add(exec_node.key)
                        added = True
                    node_idx += 1

            if exec_pattern == "all_executables" and last_exec:
                self._post_exec_names.add(last_exec)
                added = True

            if added:
                if len(self._capture_names) != len(self._capture_commands):
                    logger.warn(
                        "Values for pre_post_capture_names and pre_post_capture_commands are "
                        f"different lengths\nin experiment {self.expander.experiment_namespace}"
                    )

        pre_cmds = []
        post_cmds = []

        orders = {}
        if executable_name in self._pre_exec_names:
            orders["pre"] = pre_cmds

        if executable_name in self._post_exec_names:
            orders["post"] = post_cmds

        if orders:

            for order, order_cmds in orders.items():
                for name, cmd in zip(
                    self._capture_names, self._capture_commands
                ):
                    arguments = f"{shlex.quote(order)} {shlex.quote(name)} {shlex.quote(cmd)}"
                    order_cmds.append(
                        ramble.util.executable.CommandExecutable(
                            f"{order}-{executable_name}-capture-{name}-pre-post-capture",
                            template=[
                                f'echo "  Capturing {name}"',
                                f'pdsh -R ssh -w {{hostlist}} "{{pre_post_capture_collector}} {arguments}"',
                            ],
                            redirect="",
                            output_capture="",
                        )
                    )
        return pre_cmds, post_cmds

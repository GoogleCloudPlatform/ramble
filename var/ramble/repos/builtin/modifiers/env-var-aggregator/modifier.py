# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.config
import ramble.util.executable
from ramble.modkit import *  # noqa: F403
from ramble.util import shell_utils
from ramble.util.logger import logger


class EnvVarAggregator(BasicModifier):
    """
    This modifier is used to prefix, and aggregate the names of environment
    variables into a common environment variable definition.

    There are two execution modes:
     'all' - Includes all environment variables defined in the environment
             when the experiment is being executed.
     'explicit' - Includes only explicitly defined environment variables

    The output of this modifier is to define a new environment variable
    (defined by aggregated_env_var_name) which will contain all of the
    aggregated environment variable names. For example, if the current
    environment has HOME, and PWD defined, then the resulting environment
    variable will have default contents of "-x HOME -x PWD".

    The prefix, and delimiter are configurable through experiment variables.
    """

    name = "env-var-aggregator"

    mode("all", description="Aggregate all environment variables")
    mode(
        "explicit",
        description="Construct an aggregated list of explicit variables",
    )
    default_mode("all")

    modifier_variable(
        "aggregated_env_var_item_prefix",
        default="-x",
        description="The string to prepend to each original environment variable name.",
        modes=["all", "explicit"],
    )

    modifier_variable(
        "aggregated_env_var_name",
        default="ENV_VAR_NAMES",
        description="The name of the new environment variable that will store the aggregated result.",
        modes=["all", "explicit"],
    )

    modifier_variable(
        "aggregated_env_var_delimiter",
        default=" ",
        description="The delimiter string to use between prefixed environment variable names.",
        modes=["all", "explicit"],
    )

    modifier_variable(
        "aggregated_env_var_exclude_list",
        default=["HOME", "PWD", "HOSTNAME", "SHELL"],
        track_used=False,
        description="List of environment variables to exclude from aggregation",
        modes=["all"],
    )

    modifier_variable(
        "aggregated_env_var_include_list",
        default=["PATH", "LD_LIBRARY_PATH"],
        track_used=False,
        description="List of environment variables to include in explicit aggregation",
        modes=["explicit"],
    )

    def __init__(self, file_path):
        super().__init__(file_path)
        self._applied_aggregation = False

    def _aggregate_all_env_vars(self, shell):
        script_lines = []

        exclude_env_var_list = self.expander.expand_var_name(
            "aggregated_env_var_exclude_list", typed=True
        )
        exclude_dict = {}
        for var_name in exclude_env_var_list:
            exclude_dict[var_name] = "EXCLUDE"

        if shell in ["bash", "sh"]:
            shell_exclude_dict = shell_utils.gen_dict_definition(
                "exclude_variables", dict=exclude_dict
            )

            script_lines.extend(
                [
                    f"{shell_exclude_dict}",
                    '{aggregated_env_var_name}=""',
                    "for VAR_NAME in `declare -x | awk '{print $3}' | sed 's/=.*//g'`; do",
                    '  if [[ ! "${exclude_variables[$VAR_NAME]}" == "EXCLUDE" ]]; then',
                    '    prefixed_name="{aggregated_env_var_item_prefix}{aggregated_env_var_delimiter}$VAR_NAME"',
                    '    {aggregated_env_var_name}="${aggregated_env_var_name}{aggregated_env_var_delimiter}$prefixed_name"',
                    "  fi",
                    "done",
                ]
            )

        return script_lines

    def _aggregate_explicit_env_vars(self, shell):
        delimiter = self.expander.expand_var_name(
            "aggregated_env_var_delimiter"
        )
        prefix = self.expander.expand_var_name(
            "aggregated_env_var_item_prefix"
        )
        var_names = self.expander.expand_var_name(
            "aggregated_env_var_include_list", typed=True
        )

        value = ""
        for var_name in var_names:
            value += f"{delimiter}{prefix}{delimiter}{var_name}"

        script_lines = []
        if shell in ["bash", "sh"]:
            script_lines.append(f'{{aggregated_env_var_name}}="{value}"')

        return script_lines

    executable_modifier("inject_env_aggregation_script")

    def inject_env_aggregation_script(
        self, executable_name, executable, app_inst=None
    ):
        pre_cmds = []
        post_cmds = []

        if self._applied_aggregation or not app_inst:
            return pre_cmds, post_cmds

        item_prefix = app_inst.expander.expand_var_name(
            "aggregated_env_var_item_prefix"
        )
        agg_var_name = app_inst.expander.expand_var_name(
            "aggregated_env_var_name"
        )

        if item_prefix is None or not agg_var_name:
            logger.warning(
                "EnvVarAggregator: 'aggregated_env_var_item_prefix' or 'aggregated_env_var_name' "
                "is not properly configured. 'aggregated_env_var_name' must be set, "
                "'aggregated_env_var_item_prefix' must be defined (can be empty)."
            )
            return pre_cmds, post_cmds

        shell = ramble.config.get("config:shell")

        if self._usage_mode == "all":
            script_lines = self._aggregate_all_env_vars(shell)

        elif self._usage_mode == "explicit":
            script_lines = self._aggregate_explicit_env_vars(shell)

        cmd_exec = ramble.util.executable.CommandExecutable(
            name="env_var_aggregation_script",
            template=script_lines,
            redirect=None,
            output_capture=None,
        )
        pre_cmds.append(cmd_exec)

        self._applied_aggregation = True

        return pre_cmds, post_cmds

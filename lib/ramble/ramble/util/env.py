# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import spack.util.environment
from ramble.util.shell_utils import get_compatible_base_shell


class Env:
    def get_env_set_commands(var_conf, var_set, shell="sh"):
        env_mods = RambleEnvModifications()
        for var, val in var_conf.items():
            var_set.add(var)
            env_mods.set(var, val)

        env_cmds_arr = env_mods.shell_modifications(shell=shell, explicit=True)

        return (env_cmds_arr.split("\n"), var_set)

    def get_env_unset_commands(var_conf, var_set, shell="sh"):
        env_mods = RambleEnvModifications()
        for var in var_conf:
            if var in var_set:
                var_set.remove(var)
            env_mods.unset(var)

        env_cmds_arr = env_mods.shell_modifications(shell=shell, explicit=True)

        return (env_cmds_arr.split("\n"), var_set)

    def get_env_append_commands(var_conf, var_set, shell="sh"):
        env_mods = RambleEnvModifications()

        append_funcs = {
            "vars": env_mods.append_flags,
            "paths": env_mods.append_path,
        }

        var_set_orig = var_set.copy()

        for append_group in var_conf:
            sep = " "
            if "var-separator" in append_group:
                sep = append_group["var-separator"]

            for group in append_funcs.keys():
                if group in append_group.keys():
                    for var, val in append_group[group].items():
                        if var not in var_set:
                            env_mods.set(var, "${%s}" % var)
                            var_set.add(var)
                        append_funcs[group](var, val, sep=sep)

        env_cmds_arr = env_mods.shell_modifications(shell=shell, explicit=True)

        return (env_cmds_arr.split("\n"), var_set_orig)

    def get_env_prepend_commands(var_conf, var_set, shell="sh"):
        env_mods = RambleEnvModifications()

        prepend_funcs = {
            "paths": env_mods.prepend_path,
        }

        var_set_orig = var_set.copy()

        for prepend_group in var_conf:
            for group in prepend_group.keys():
                for var, val in prepend_group[group].items():
                    if var not in var_set:
                        env_mods.set(var, "${%s}" % var)
                        var_set.add(var)
                    prepend_funcs[group](var, val)

        env_cmds_arr = env_mods.shell_modifications(shell=shell, explicit=True)

        return (env_cmds_arr.split("\n"), var_set_orig)


action_funcs = {
    "set": Env.get_env_set_commands,
    "unset": Env.get_env_unset_commands,
    "append": Env.get_env_append_commands,
    "prepend": Env.get_env_prepend_commands,
}


class RambleEnvModifications(spack.util.environment.EnvironmentModifications):

    def shell_modifications(self, shell="sh", explicit=False, env=None):
        """Wrapper around spack's shell_modifications"""
        base_shell = get_compatible_base_shell(shell)
        return super().shell_modifications(shell=base_shell, explicit=explicit, env=env)

# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
import os

from llnl.util.tty.color import colorize

import ramble.workspace
import ramble.repository
from spack.util.environment import EnvironmentModifications


def activate_header(ws, shell, prompt=None):
    # Construct the commands to run
    cmds = ""
    if shell == "csh":
        # TODO: figure out how to make color work for csh
        cmds += f"setenv {ramble.workspace.ramble_workspace_var} {ws.root};\n"
        if prompt:
            cmds += "if (! $?RAMBLE_OLD_PROMPT ) "
            cmds += 'setenv RAMBLE_OLD_PROMPT "${prompt}";\n'
            cmds += 'set prompt="%s ${prompt}";\n' % prompt
    elif shell == "fish":
        if "color" in os.getenv("TERM", "") and prompt:
            prompt = colorize("@G{%s} " % prompt, color=True)

        cmds += f"set -gx {ramble.workspace.ramble_workspace_var} {ws.root};\n"
        #
        # NOTE: We're not changing the fish_prompt function (which is fish's
        # solution to the PS1 variable) here. This is a bit fiddly, and easy to
        # screw up => spend time reasearching a solution. Feedback welcome.
        #
    elif shell == "bat":
        # TODO: Color
        cmds += f'set "{ramble.workspace.ramble_workspace_var}={ws.root}"\n'
        # TODO: prompt
    else:
        if "color" in os.getenv("TERM", "") and prompt:
            prompt = colorize("@G{%s}" % prompt, color=True)

        cmds += f"export {ramble.workspace.ramble_workspace_var}={ws.root};\n"
        if prompt:
            cmds += "if [ -z ${RAMBLE_OLD_PS1+x} ]; then\n"
            cmds += "    if [ -z ${PS1+x} ]; then\n"
            cmds += "        PS1='$$$$';\n"
            cmds += "    fi;\n"
            cmds += '    export RAMBLE_OLD_PS1="${PS1}";\n'
            cmds += "fi;\n"
            cmds += 'export PS1="%s ${PS1}";\n' % prompt

    return cmds


def deactivate_header(shell):
    cmds = ""
    if shell == "csh":
        cmds += "unsetenv %s;\n" % (ramble.workspace.ramble_workspace_var)
        cmds += "if ( $?RAMBLE_OLD_PROMPT ) "
        cmds += '    eval \'set prompt="$RAMBLE_OLD_PROMPT" &&'
        cmds += "        unsetenv RAMBLE_OLD_PROMPT';\n"
    elif shell == "fish":
        cmds += "set -e %s;\n" % (ramble.workspace.ramble_workspace_var)
        #
        # NOTE: Not changing fish_prompt (above) => no need to restore it here.
        #
    elif shell == "bat":
        # TODO: Color
        cmds += 'set "%s="\n' % (ramble.workspace.ramble_workspace_var)
        # TODO: despacktivate
        # TODO: prompt
    else:
        cmds += "if [ ! -z ${%s+x} ]; then\n" % (ramble.workspace.ramble_workspace_var)
        cmds += "unset {}; export {};\n".format(
            ramble.workspace.ramble_workspace_var,
            ramble.workspace.ramble_workspace_var,
        )
        cmds += "fi;\n"
        cmds += "if [ ! -z ${RAMBLE_OLD_PS1+x} ]; then\n"
        cmds += "    if [ \"$RAMBLE_OLD_PS1\" = '$$$$' ]; then\n"
        cmds += "        unset PS1; export PS1;\n"
        cmds += "    else\n"
        cmds += '        export PS1="$RAMBLE_OLD_PS1";\n'
        cmds += "    fi;\n"
        cmds += "    unset RAMBLE_OLD_PS1; export RAMBLE_OLD_PS1;\n"
        cmds += "fi;\n"

    return cmds


def activate(ws):
    """
    Activate an environment and append environment modifications

    To activate an environment, we add its configuration scope to the
    existing Spack configuration, and we set active to the current
    environment.

    Arguments:
        env (spack.environment.Environment): the environment to activate
        use_env_repo (bool): use the packages exactly as they appear in the
            environment's repository
        add_view (bool): generate commands to add view to path variables

    Returns:
        spack.util.environment.EnvironmentModifications: Environment variables
        modifications to activate environment.
    """
    ramble.workspace.activate(ws)

    env_mods = EnvironmentModifications()

    #
    # NOTE in the fish-shell: Path variables are a special kind of variable
    # used to support colon-delimited path lists including PATH, CDPATH,
    # MANPATH, PYTHONPATH, etc. All variables that end in PATH (case-sensitive)
    # become PATH variables.
    #

    return env_mods


def deactivate():
    """
    Deactivate an environment and collect corresponding environment modifications.

    Note: unloads the environment in its current state, not in the state it was
        loaded in, meaning that specs that were removed from the spack environment
        after activation are not unloaded.

    Returns:
        spack.util.environment.EnvironmentModifications: Environment variables
        modifications to activate environment.
    """
    env_mods = EnvironmentModifications()
    active = ramble.workspace.active_workspace()

    if active is None:
        return env_mods

    ramble.workspace.deactivate()

    return env_mods

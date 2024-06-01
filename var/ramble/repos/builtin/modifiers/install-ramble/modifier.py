# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *


class InstallRamble(BasicModifier):
    """Modifier to define commands to install ramble"""
    name = "install-ramble"

    tags('tool-installation')

    maintainers('douglasjacobsen')

    mode('standard', description='Standard execution mode for ramble')
    default_mode('standard')

    modifier_variable('ramble_url', default='https://github.com/GoogleCloudPlatform/ramble',
                      description='URL to clone ramble from', mode='standard')

    modifier_variable('ramble_ref', default='develop',
                      description='Ref to checkout for ramble', mode='standard')

    modifier_variable('ramble_install_dir', default='${HOME}/.ramble/ramble',
                      description='Directory to install ramble into', mode='standard')

    modifier_variable('ramble_venv_path', default='${HOME}/.ramble/ramble-venv',
                      description='Virtual environment path for ramble', mode='standard')

    create_ramble_venv = """
if [ ! -d {ramble_venv_path} ]; then
python -m venv {ramble_venv_path}
. {ramble_venv_path}/bin/activate
pip install --upgrade pip
pip install -r {ramble_install_dir}/requirements.txt
fi
"""

    install_ramble_full = """
if [ ! -d {ramble_install_dir} ]; then
git clone {ramble_url} {ramble_install_dir}
cd {ramble_install_dir}
git checkout {ramble_ref}
cd -
fi
"""

    install_ramble_shallow = """
if [ ! -d {ramble_install_dir} ]; then
git init {ramble_install_dir}
cd {ramble_install_dir}
git remote add origin {ramble_url}
git fetch --depth 1 origin {ramble_ref}
git checkout FETCH_HEAD
cd -
fi
"""
    modifier_variable('install_ramble_full', default=install_ramble_full + create_ramble_venv, description='Install script for full ramble history',
                      mode='standard')

    modifier_variable('install_ramble_shallow', default=install_ramble_shallow + create_ramble_venv, description='Install script for shallow ramble history',
                      mode='standard')

    executable_modifier('source_installed_ramble')

    def source_installed_ramble(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_exec = []
        post_exec = []

        if not hasattr(self, '_already_applied'):
            pre_exec.append(
                CommandExecutable('source-installed-ramble',
                                  template=['. {ramble_install_dir}/share/ramble/setup-env.sh']
                                  )
            )

            self._already_applied = True
        return pre_exec, post_exec

# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *
import spack.util.executable


class SpackStack(SpackApplication):
    '''Application definition for creating a spack software stack

    This application definition is used solely to create spack software stacks.

    As such, compiler installation and concretization are handled by
    `ramble workspace setup` but environment installation is handled
    as part of the experiment.

    The `spack install` phase happens with the '{mpi_command}' prefix to
    accelerate package installation.

    The experiments are considered successful if the installation completed.
    '''
    name = 'spack-stack'

    maintainers('douglasjacobsen')

    tags('software', 'configuration')

    executable('configure', template=['spack config add "config:install_tree:padded_length:{padded_length}"'],
               use_mpi=False)

    executable('install', 'spack install {install_flags}', use_mpi=True)

    workload('create', executables=['builtin::remove_env_files',
                                    'builtin::spack_source',
                                    'builtin::spack_activate',
                                    'configure',
                                    'install',
                                    'builtin::spack_deactivate'])

    executable('uninstall', 'spack uninstall {uninstall_flags}', use_mpi=True)

    workload('remove', executables=['builtin::spack_source',
                                    'builtin::spack_activate',
                                    'uninstall',
                                    'builtin::spack_deactivate'])

    workload_variable('install_flags', default='',
                      description='Flags to use for `spack install`',
                      workloads=['create'])

    workload_variable('padded_length', default='512',
                      description='Length to pad install prefixes with',
                      workloads=['create'])

    workload_variable('uninstall_flags', default='--all -y',
                      description='Flags to use for `spack uninstall`',
                      workloads=['remove'])

    success_criteria('view-updated', mode='string', match=r'.*==> Updating view at.*')

    pkg_regex = r'\s*==\> (?P<name>.*) Successfully installed (?P<spec>.*)'

    figure_of_merit('Previously installed packages',
                    fom_regex=r'\s*==\> (?P<quant>.*) of the packages are already installed',
                    group_name='quant', units='')

    figure_of_merit('{pkg_name} installed',
                    fom_regex=r'\s*==\> (?P<pkg_name>.*): Successfully installed (?P<spec>.*)',
                    group_name='spec', units='')

    figure_of_merit_context('Package', regex=pkg_regex,
                            output_format='({name}, {spec})')

    fom_parts = ['Autoreconf',
                 'Bootstrap',
                 'Build',
                 'Cmake',
                 'Configure',
                 'Edit',
                 'Install',
                 'Post-install',
                 'Stage',
                 'Total']
    for i, fom_part in enumerate(fom_parts):
        full_regex = r'.*\s*' + fom_part + r':\s+(?P<fom>[0-9\.]+)s.*'
        figure_of_merit(fom_part, fom_regex=full_regex, group_name='fom', units='s',
                        contexts=['Package'])

    register_builtin('remove_env_files', required=False)

    def remove_env_files(self):
        cmds = [
            'rm -f {env_path}/spack.lock',
            'rm -rf {env_path}/.spack-env'
        ]
        return cmds

    def _software_install(self, workspace, app_inst=None):
        """This application never installs software during setup."""
        pass

    def _define_package_paths(self, workspace, app_inst=None):
        pass

    def evaluate_success(self):
        import spack.util.spack_yaml as syaml
        spack_file = self.expander.expand_var('{env_path}/spack.yaml')
        spec_list = []
        with open(spack_file, 'r') as f:
            spack_data = syaml.load_config(f)

        tty.debug(f'Spack data: {spack_data}')

        for spec in spack_data['spack']['specs']:
            spec_list.append(spec)

        self.spack_runner.set_env(self.expander.env_path)
        self.spack_runner.activate()

        # Spack find errors if a spec is provided that is not installed.
        for spec in spec_list:
            try:
                self.spack_runner.spack('find', spec, output=str)
            except spack.util.executable.ProcessError:
                return False
        return True

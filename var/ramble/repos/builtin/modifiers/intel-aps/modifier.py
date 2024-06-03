# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.modkit import *  # noqa: F403


class IntelAps(SpackModifier):
    """Define a modifier for Intel's Application Performance Snapshot

    Intel's Application Performance Snapshot (APS) is a high level profiler. It
    gives a quick view into the high level performance characteristics of an
    experiment. This modifier allows for easy application of APS to experiments.
    """
    name = "intel-aps"

    tags('profiler', 'performance-analysis')

    maintainers('douglasjacobsen')

    mode('mpi', description='Mode for collecting mpi statistics')
    default_mode('mpi')

    variable_modification('aps_log_dir', 'aps_{executable_name}_results_dir',
                          method='set', modes=['mpi'])
    variable_modification('aps_flags', '-c mpi -r {aps_log_dir}', method='set', modes=['mpi'])
    variable_modification('mpi_command', 'aps {aps_flags}', method='append', modes=['mpi'])

    archive_pattern('aps_*_results_dir/*')

    software_spec('intel-oneapi-vtune', pkg_spec='intel-oneapi-vtune')

    required_package('intel-oneapi-vtune')

    executable_modifier('aps_summary')

    def aps_summary(self, executable_name, executable, app_inst=None):
        from ramble.util.executable import CommandExecutable

        pre_exec = []
        post_exec = []
        if executable.mpi:
            pre_exec.append(
                CommandExecutable(f'load-aps-{executable_name}',
                                  template=['spack load intel-oneapi-vtune'])
            )
            post_exec.append(
                CommandExecutable(f'unload-aps-{executable_name}',
                                  template=['spack unload intel-oneapi-vtune'])
            )
            post_exec.append(
                CommandExecutable(f'gen-aps-{executable_name}',
                                  template=['echo "APS Results for executable {executable_name}"',
                                            'aps-report -s -D {aps_log_dir}'],
                                  mpi=False,
                                  redirect='{log_file}'
                                  )
            )

        return pre_exec, post_exec

    figure_of_merit_context('APS Executable',
                            regex=r'APS Results for executable (?P<exec_name>\w+)',
                            output_format='APS on {exec_name}')

    summary_foms = [
        'Application',
        'Report creation date',
        'Number of ranks',
        'Ranks per node',
        'Used statistics'
    ]

    for fom in summary_foms:
        figure_of_merit(fom, fom_regex=r'\s*' + f'{fom}' + r'\s+:\s+(?P<value>.*)', group_name='value',
                        units='', log_file='{log_file}', contexts=['APS Executable'])

    elapsed_time_regex = r'\s*Elapsed Time:\s*(?P<time>[0-9\.]+)'
    figure_of_merit('Elapsed Time', fom_regex=elapsed_time_regex, group_name='time',
                    units='s', log_file='{log_file}', contexts=['APS Executable'])

    mpi_time_regex = r'\s*MPI Time:\s*(?P<time>[0-9\.]+)\s*s\s*(?P<percent>[0-9\.]+)%.*'
    figure_of_merit('MPI Time', fom_regex=mpi_time_regex, group_name='time',
                    units='s', log_file='{log_file}', contexts=['APS Executable'])
    figure_of_merit('MPI Percent', fom_regex=mpi_time_regex, group_name='percent',
                    units='%', log_file='{log_file}', contexts=['APS Executable'])

    mpi_imba_regex = r'\s*MPI Imbalance:\s*(?P<time>[0-9\.]+)\s*s\s*(?P<percent>[0-9\.]+)%.*'
    figure_of_merit('MPI Imbalance Time', fom_regex=mpi_imba_regex, group_name='time',
                    units='s', log_file='{log_file}', contexts=['APS Executable'])
    figure_of_merit('MPI Imbalance Percent', fom_regex=mpi_imba_regex, group_name='percent',
                    units='%', log_file='{log_file}', contexts=['APS Executable'])

    disk_io_regex = r'\s*Disk I/O Bound:\s*(?P<time>[0-9\.]+)\s*s\s*(?P<percent>[0-9\.]+)%.*'
    figure_of_merit('Disk I/O Time', fom_regex=disk_io_regex, group_name='time',
                    units='s', log_file='{log_file}', contexts=['APS Executable'])
    figure_of_merit('Disk I/O Percent', fom_regex=disk_io_regex, group_name='percent',
                    units='%', log_file='{log_file}', contexts=['APS Executable'])

    mpi_func_regex = r'\s*(?P<func_name>MPI_\S+):\s+(?P<time>[0-9\.]+) s\s+(?P<perc>[0-9\.]+)% of Elapsed Time'
    figure_of_merit('{func_name} Time', fom_regex=mpi_func_regex, group_name='time',
                    units='s', log_file='{log_file}', contexts=['APS Executable'])
    figure_of_merit('{func_name} Percent', fom_regex=mpi_func_regex, group_name='perc',
                    units='%', log_file='{log_file}', contexts=['APS Executable'])

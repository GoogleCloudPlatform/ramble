# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *
from ramble.expander import Expander


class Minixyce(SpackApplication):
    '''Define miniXyce application'''
    name = 'minixyce'

    maintainers('dodecatheon')

    tags('circuitdesign', 'miniapp', 'mini-app', 'minibenchmark', 'mini-benchmark')

    define_compiler('gcc12', spack_spec="gcc@12.2.0")

    software_spec('ompi415cxx', spack_spec='openmpi@4.1.5 +legacylaunchers +cxx',
                  compiler='gcc12')

    software_spec('minixyce', spack_spec='minixyce@1.0 +mpi',
                  compiler='gcc12')

    required_package('minixyce')

    executable('execute', 'miniXyce.x --circuit {workload_name}.net --pf params.txt', use_mpi=True)

    executable('get_simple_network',
               template=['cp {minixyce}/doc/tests/{workload_name}.net {experiment_run_dir}/{workload_name}.net'],
               use_mpi=False)

    executable('generate_RC_ladder',
               template=['perl {minixyce}/doc/tests/RC_ladder.pl {num_ladder_stages} > {experiment_run_dir}/{workload_name}.net; echo Running perl'],
               use_mpi=False)

    executable('generate_RLC_ladder',
               template=['perl {minixyce}/doc/tests/RLC_ladder.pl {num_ladder_stages} > {experiment_run_dir}/{workload_name}.net; echo Running perl'],
               use_mpi=False)

    executable('generate_RC_ladder2',
               template=['perl {minixyce}/doc/tests/RC_ladder2.pl {num_ladder_stages} > {experiment_run_dir}/{workload_name}.net; echo Running perl'],
               use_mpi=False)

    executable('generate_RLC_ladder2',
               template=['perl {minixyce}/doc/tests/RLC_ladder2.pl {num_ladder_stages} > {experiment_run_dir}/{workload_name}.net; echo Running perl'],
               use_mpi=False)

    cir_workloads = ['cir1', 'cir2', 'cir3', 'cir4', 'cir5']
    for cir_workload in cir_workloads:
        workload(cir_workload, executables=['get_simple_network', 'execute'])

    rc_workloads = ['RC_ladder', 'RLC_ladder', 'RC_ladder2', 'RLC_ladder2']
    for workload_name in rc_workloads:
        workload(workload_name, executables=['generate_' + workload_name, 'execute'])

    all_workloads = cir_workloads + rc_workloads
    workload_variable('t_start', default='0', description='Start time', workloads=all_workloads)
    workload_variable('t_step', default='1e-8', description='Time step', workloads=all_workloads)
    workload_variable('t_stop', default='5e-5', description='Stop time', workloads=all_workloads)
    workload_variable('tol', default='1e-6', description='Tolerance', workloads=all_workloads)
    workload_variable('k', default='10', description='Tells GMRES how often to restart', workloads=all_workloads)

    workload_variable('num_ladder_stages', default='1024',
                      description='Number of Ladder stages for RC|RLC ladder|ladder2 test generation',
                      workloads=rc_workloads)

    log_str = os.path.join(Expander.expansion_str('experiment_run_dir'),
                           Expander.expansion_str('workload_name') + '_tran_results.prn')
    out_file = os.path.join(Expander.expansion_str('experiment_run_dir'),
                            Expander.expansion_str('experiment_name') + '.out')
    processed_output = os.path.join(Expander.expansion_str('experiment_run_dir'),
                                    'processed_output.txt')

    result_regex = r'.*\s+(?P<num_iters>[0-9]+)\s+(?P<num_restarts>[0-9]+)'

    floating_point_regex = r'\d+\.\d+'
    scientific_number_regex = r'[\+\-]*\d+\.\d+[eE][\+\-]*\d+'

    success_regex = r'^\s*TIME.*num_GMRES_iters\s*num_GMRES_restarts'
    success_criteria('valid', mode='string',
                     match=success_regex,
                     file=log_str)

    figure_of_merit('Total Simulation Time', log_file=out_file,
                    fom_regex=r'Total Simulation Time:\s+(?P<time>' + floating_point_regex + r')',
                    group_name='time',
                    units='s'
                    )
    figure_of_merit('I/O File Time', log_file=out_file,
                    fom_regex=r'I/O File Time:\s+(?P<time>' + floating_point_regex + r')',
                    group_name='time',
                    units='s'
                    )

    enable_deck_based_FOMs = False
    if enable_deck_based_FOMs:
        figure_of_merit('Time_end', log_file=log_str,
                        fom_regex=r'\s+(?P<time>' + scientific_number_regex + r')',
                        group_name='time',
                        units='s'
                        )

        figure_of_merit('num_GMRES_iters', log_file=log_str,
                        fom_regex=result_regex,
                        group_name='num_iters',
                        units=''
                        )

        figure_of_merit('num_GMRES_restarts', log_file=log_str,
                        fom_regex=result_regex,
                        group_name='num_restarts',
                        units=''
                        )

        state_var_regex = r'\s*(?P<State_Variable>[0-9]+)*:*\s*(?P<name>[0-9A-Za-z]+)\s*=\s*(?P<value>' + scientific_number_regex + r')'

        figure_of_merit('Name', log_file=processed_output,
                        fom_regex=state_var_regex,
                        group_name='name',
                        units='', contexts=['state_variable']
                        )

        figure_of_merit('Value', log_file=processed_output,
                        fom_regex=state_var_regex,
                        group_name='value',
                        units='', contexts=['state_variable']
                        )

        figure_of_merit_context('state_variable',
                                regex=state_var_regex,
                                output_format='{State_Variable}')

    def _make_experiments(self, workspace, app_inst=None):
        super()._make_experiments(workspace)

        input_path = os.path.join(self.expander.expand_var_name('experiment_run_dir'), 'params.txt')

        settings = ['t_start', 't_step', 't_stop', 'tol', 'k']

        with open(input_path, 'w+') as f:
            for setting in settings:
                f.write(setting + ' = ' + self.expander.expand_var_name(setting) + '\n')

    def _analyze_experiments(self, workspace, app_inst=None):
        import os

        output_file = os.path.join(self.expander.expand_var_name('experiment_run_dir'),
                                   self.expander.expand_var_name('workload_name') + '_tran_results.prn')
        processed_output_path = os.path.join(self.expander.expand_var_name('experiment_run_dir'), 'processed_output.txt')

        if os.path.isfile(output_file):
            names = []
            with open(output_file, 'r') as f:
                names = f.readline().split()
                for line in (f.readlines()[-1:]):
                    values = line.split()

            with open(processed_output_path, 'w+') as f:
                for i, (name, value) in enumerate(zip(names[1:-2], values[1:-2])):
                    f.write("{}: {} = {}\n".format((i + 1), name, value))

        super()._analyze_experiments(workspace)

# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Elk(ExecutableApplication):
    '''
    An all-electron full-potential linearised augmented-plane wave (LAPW) code
    with many advanced features. Written originally at
    Karl-Franzens-Universität Graz as a milestone of the EXCITING EU Research
    and Training Network, the code is designed to be as simple as possible so
    that new developments in the field of density functional theory (DFT) can
    be added quickly and reliably. The code is freely available under the GNU
    General Public License.

    https://elk.sourceforge.io/

    This package intentionally does not use spack, and instead relies on the
    user to manage both the package install (eg via yum), and the environment
    through explicit paths. By default, yum installs to
    /usr/lib64/openmpi/bin/elk_openmpi
    '''

    name = 'elk'

    tags('LAPW', 'density-functional-theory')

    input_file('examples',
               url='https://master.dl.sourceforge.net/project/elk/elk-4.3.6.tgz',
               sha256='efd2893a55143ac045656d2acd1407becf773408a116c90771ed3ee9fede35c9',
               description='Main installer which contains various example input decks and species'
               )

    executable('execute', '{install_prefix}/elk_openmpi', use_mpi=True)
    executable('copy', 'cp {input_path}/elk.in {experiment_run_dir}/.', use_mpi=False)
    executable('update_input', "sed -i 's|../../../species/|{examples}/species/|g' elk.in", use_mpi=False)

    workload('Cu', executables=['copy', 'update_input', 'execute'], input='examples')

    workload_variable('install_prefix', default='/usr/lib64/openmpi/bin',
                      description='Install path to main executable',
                      workloads=['Cu'])

    workload_variable('input_path', default='{examples}/examples/basic/Cu',
                      description='Path to input deck',
                      workloads=['Cu'])

    success_criteria('prints_done', mode='string', match=r'.*Elk code stopped.*', file='{experiment_run_dir}/{experiment_name}.out')

    output_file = 'INFO.OUT'
    metrics = ['Timings (CPU seconds)', 'initialisation', 'Hamiltonian and overlap matrix set up', 'first-variational eigenvalue equation', 'charge density calculation', 'potential calculation', 'total']

    for metric in metrics:
        figure_of_merit(metric,
                        log_file=output_file,
                        fom_regex=rf'\s*(?P<metric>{metric})\s+:\s+(?P<value>[0-9]+\.[0-9]*).*',
                        group_name='value', units='s'
                        )

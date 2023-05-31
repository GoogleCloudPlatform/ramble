# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import re

import pytest

import ramble.workspace
import ramble.config
import ramble.software_environments
from ramble.main import RambleCommand


# everything here uses the mock_workspace_path
pytestmark = pytest.mark.usefixtures('mutable_config',
                                     'mutable_mock_workspace_path')

workspace = RambleCommand('workspace')


@pytest.mark.long
def test_known_applications(application):
    info_cmd = RambleCommand('info')

    workload_regex = re.compile(r'Workload: (?P<wl_name>.*)')
    ws_name = f'test_all_apps_{application}'

    base_config = """ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks}'
    batch_submit: '{execute_experiment}'
  applications:\n"""

    app_info = info_cmd(application)
    workloads = []
    for line in app_info.split('\n'):
        match = workload_regex.search(line)
        if match:
            workloads.append(match.group('wl_name').replace(' ', ''))

    with ramble.workspace.create(ws_name) as ws:
        ws.write()
        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, 'w+') as f:
            f.write(base_config)
            f.write(f'    {application}:\n')
            f.write('      workloads:\n')
            for workload in workloads:
                f.write(f"""        {workload.strip()}:
          experiments:
            test_experiment:
              variables:
                n_ranks: '1'
                n_nodes: '1'
                processes_per_node: '1'\n""")
            f.write("""  spack:
    concretized: false
    packages: {}
    environments: {}\n""")

        ws._re_read()
        ws.concretize()
        ws._re_read()
        ws.dry_run = True
        ws.run_pipeline('setup')
        ws.run_pipeline('analyze')
        ws.archive(create_tar=True)

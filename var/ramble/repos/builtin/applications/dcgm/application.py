# -*- coding: utf-8 -*-
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
NVIDIA Data Center GPU Manager (DCGM) application.
"""


from ramble.appkit import *

class Dcgm(ExecutableApplication):
  """NVIDIA Data Center GPU Manager (DCGM).

  DCGM is a suite of tools for managing and monitoring NVIDIA GPUs
  in cluster environments.


  # Example Ramble configuration for the DCGM application
  ramble:
    env_vars:
      set:
        OMP_NUM_THREADS: '{n_threads}'

    variants:
      package_manager: user-managed
      workflow_manager: user-managed

    variables:
      n_ranks: 1
      processes_per_node: 1
      mpi_command: '' # DCGM commands don't need MPI
      batch_submit: '{execute_experiment}' # Simple direct execution

    applications:
      dcgm:
        workloads:
          diag:
            experiments:
              dcgm_r{diag_level}: # Parameterize dcgmi diag level
                variables:
                  diag_level: [1,2,3]

    # No specific software packages needed if dcgmi is in the PATH
    software:
      packages: {}
      environments: {}
  """

  name = "dcgm"
  maintainers("samskillman")
  tags("gpu", "monitoring", "diagnostics", "dcgm")

  executable(
      "diag",
      "dcgmi diag -r {diag_level}",
      use_mpi=False,
      output_capture=OUTPUT_CAPTURE.ALL,
  )

  workload(
      "diag",
      executable="diag",
  )

  workload_variable(
      "diag_level",
      default=1,
      workloads=["diag"],
      description="Level for dcgmi diagnostics",
      expandable=False,
  )

  # FOMs from 'diag' executable
  # Example Output:
  # Successfully ran diagnostic for group.
  # +---------------------------+------------------------------------------------+
  # | Diagnostic                | Result                                         |
  # +===========================+================================================+
  # |-----  Metadata  ----------+------------------------------------------------|
  # | DCGM Version              | 3.3.9                                          |
  # | Driver Version Detected   | 570.133.20                                     |
  # | GPU Device IDs Detected   | 2335,2335,2335,2335,2335,2335,2335,2335        |
  # |-----  Deployment  --------+------------------------------------------------|
  # | Denylist                  | Pass                                           |
  # | NVML Library              | Pass                                           |
  # | CUDA Main Library         | Pass                                           |
  # | Permissions and OS Blocks | Pass                                           |
  # | Persistence Mode          | Pass                                           |
  # | Environment Variables     | Pass                                           |
  # | Page Retirement/Row Remap | Pass                                           |
  # | Graphics Processes        | Pass                                           |
  # | Inforom                   | Pass                                           |
  # +-----  Integration  -------+------------------------------------------------+
  # | PCIe                      | Pass - All                                     |
  # +-----  Hardware  ----------+------------------------------------------------+
  # | GPU Memory                | Pass - All                                     |
  # | Diagnostic                | Pass - All                                     |
  # +-----  Stress  ------------+------------------------------------------------+
  # | Targeted Stress           | Pass - All                                     |
  # | Targeted Power            | Pass - All                                     |
  # | Memory Bandwidth          | Pass - All                                     |
  # | EUD Test                  | Skip - All                                     |
  # +---------------------------+------------------------------------------------+

  figure_of_merit(
      "diag: {diag_test}",
      executable="diag",
      fom_regex=r"^\|\s*(?P<diag_test>[\w\s\/]+?)\s*\|\s*(?P<result>Pass|Fail)\b.*",
      group_name="result",
      units="",
      fom_type=FomType.INFO,
  )

  # Success Criteria
  success_criteria(
          '{fom_name}',
          mode="fom_comparison",
          fom_name="diag:*",
          formula="{value} == 'Pass'",
  )

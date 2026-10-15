# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.workspace
from ramble.main import RambleCommand

workspace = RambleCommand("workspace")

pytestmark = pytest.mark.usefixtures(
    "mutable_config",
    "mutable_mock_workspace_path",
)


def test_tunables(request):
    ws_name = request.node.name
    test_config = """
ramble:
  modifiers:
  - name: tunables
  variables:
    processes_per_node: 1
    n_nodes: 1
    mpi_command: ''
    batch_submit: '{execute_experiment}'
    hostlist: 'nodeset-[0-1]'
  applications:
    hostname:
      workloads:
        local:
          experiments:
            test: {}
"""
    with ramble.workspace.create(ws_name) as ws:
        ws.write()
        config_path = os.path.join(
            ws.config_dir, ramble.workspace.CONFIG_FILE_NAME
        )
        with open(config_path, "w+", encoding="utf-8") as f:
            f.write(test_config)
        ws._re_read()
        workspace("setup", "--dry-run", global_args=["-D", ws.root])
        run_dir = os.path.join(ws.experiment_dir, "hostname", "local", "test")
        with open(
            os.path.join(run_dir, "execute_experiment"), encoding="utf-8"
        ) as f:
            content = f.read()
            assert content.count("pdsh -R ssh -w nodeset-[0-1]") == 7
            assert "cat /proc/sys/kernel/randomize_va_space" in content
            assert "cat /proc/sys/kernel/numa_balancing" in content
            assert "cat /sys/devices/system/cpu/smt/active" in content
            assert "cat /sys/kernel/mm/transparent_hugepage/enabled" in content
            assert "cat /sys/kernel/mm/transparent_hugepage/defrag" in content
            assert "grep -i Hugepagesize /proc/meminfo" in content
            assert "grep -i HugePages_Total /proc/meminfo" in content

        with open(
            os.path.join(run_dir, "tunables.log"), "w+", encoding="utf-8"
        ) as f:
            f.write("""
nodeset-1: fom:address-space-randomization:2
nodeset-0: fom:address-space-randomization:2
nodeset-0: fom:smt-active:1
nodeset-1: fom:smt-active:0
nodeset-0: fom:thp-enabled:always
nodeset-1: fom:thp-enabled:madvise
nodeset-1: fom:hugepage-size:    2048 kB
nodeset-0: fom:hugepage-size:    2048 kB
""")
        workspace("analyze", global_args=["-w", ws_name])
        with open(
            os.path.join(ws.root, "results.latest.txt"), encoding="utf-8"
        ) as f:
            content = f.read()
            assert (
                "modifier::tunables::address-space-randomization = 2"
                in content
            )
            assert "modifier::tunables::hugepage-size = 2048 kB" in content
            # Assert output for multi-value FOMs
            assert (
                "modifier::tunables::smt-active = {'1': nodeset-0, '0': nodeset-1}"
                in content
            )
            assert (
                "modifier::tunables::thp-enabled = {'always': nodeset-0, 'madvise': nodeset-1}"
                in content
            )
            # Assert FOMs that are not present don't get included (as None)
            assert "modifier::tunables::numa-balancing" not in content

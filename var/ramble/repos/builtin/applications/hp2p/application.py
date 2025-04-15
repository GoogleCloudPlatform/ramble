# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Hp2p(ExecutableApplication):
    """
    HP2P (Heavy Peer To Peer) benchmark is a test which performs MPI Point-to-Point non-blocking communications between all MPI processes. Its goal is to measure the bandwidths and the latencies in a situation where the network is busy. This benchmark can help to detect network problems like congestions or problems with switches or links.
    """

    name = "hp2p"

    tags("benchmark", "mpi")
    maintainers("rfbgo")

    with when("package_manager_family=spack"):
        software_spec("hp2p", pkg_spec="hp2p@4.1")
        software_spec("openmpi412", pkg_spec="openmpi@4.1.2")

    executable(
        "execute",
        "hp2p.exe -n {iter} -s {msg_size} -m {nb_msg} -b 1",
        use_mpi=True,
    )

    workload("standard", executables=["execute"])

    workload_variable(
        "iter",
        default="1000",
        description="Number of iterations",
        workloads=["standard"],
    )

    workload_variable(
        "msg_size",
        default="1024",
        description="Message size",
        workloads=["standard"],
    )

    workload_variable(
        "nb_msg",
        default="10",
        description="Number of msg per comm",
        workloads=["standard"],
    )

    success_criteria(
        "prints_done", mode="string", match=r".*=== SUMMARY ===.*"
    )

    foms = [
        "Number of iteration",
        "Min bandwidth",
        "Max bandwidth",
        "Avg bandwidth",
        "Std bandwidth",
        "Min latency",
        "Max latency",
        "Avg latency",
        "Std latency",
        "Min bisection bandwidth",
        "Max bisection bandwidth",
        "Avg bisection bandwidth",
        "Std bisection bandwidth",
        "Min bisection efficiency",
        "Max bisection efficiency",
        "Avg bisection efficiency",
    ]

    for fom in foms:
        fom_regex = rf"\s*{fom}\s+\:\s(?P<val>\d+\.*\d*)\s*(?P<unit>.*)"
        figure_of_merit(
            fom,
            fom_regex=fom_regex,
            group_name="val",
            units="{unit}",
        )

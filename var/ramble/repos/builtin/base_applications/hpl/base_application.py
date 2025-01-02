# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *

import math


def pad_value(val, desc):
    return "{:<14}".format(val) + desc


class Hpl(ExecutableApplication):
    """Define a base HPL application."""

    name = "hpl"

    tags("benchmark-app", "benchmark", "linpack")

    workload_group("standard", workloads=[])

    workload_group("calculator", workloads=[])

    workload_variable(
        "output_file",
        default="HPL.out",
        description="Output file name (if any)",
        workload_group="standard",
    )
    workload_variable(
        "device_out",
        default="6",
        description="Output device",
        workload_group="standard",
    )
    workload_variable(
        "N-Ns",
        default="4",
        description="Number of problems sizes",
        workload_group="standard",
    )
    workload_variable(
        "Ns",
        default="29 30 34 35",
        description="Problem sizes",
        workload_group="standard",
    )
    workload_variable(
        "N-NBs",
        default="4",
        description="Number of NBs",
        workload_group="standard",
    )
    workload_variable(
        "NBs",
        default="1 2 3 4",
        description="NB values",
        workload_group="standard",
    )
    workload_variable(
        "PMAP",
        default="0",
        description="PMAP Process mapping. (0=Row-, 1=Column-Major)",
        workload_group="standard",
    )
    workload_variable(
        "N-Grids",
        default="3",
        description="Number of process grids (P x Q)",
        workload_group="standard",
    )
    workload_variable(
        "Ps",
        default="2 1 4",
        description="P values",
        workload_group="standard",
    )
    workload_variable(
        "Qs",
        default="2 4 1",
        description="Q values",
        workload_group="standard",
    )
    workload_variable(
        "threshold",
        default="16.0",
        description="Residual threshold",
        workload_group="standard",
    )
    workload_variable(
        "NPFACTs",
        default="3",
        description="Number of PFACTs",
        workload_group="standard",
    )
    workload_variable(
        "PFACTs",
        default="0 1 2",
        description="PFACT Values",
        workload_group="standard",
    )
    workload_variable(
        "N-NBMINs",
        default="2",
        description="Number of NBMINs",
        workload_group="standard",
    )
    workload_variable(
        "NBMINs",
        default="2 4",
        description="NBMIN values",
        workload_group="standard",
    )
    workload_variable(
        "N-NDIVs",
        default="1",
        description="Number of NDIVs",
        workload_group="standard",
    )
    workload_variable(
        "NDIVs",
        default="2",
        description="NDIV values",
        workload_group="standard",
    )
    workload_variable(
        "N-RFACTs",
        default="3",
        description="Number of RFACTs",
        workload_group="standard",
    )
    workload_variable(
        "RFACTs",
        default="0 1 2",
        description="RFACT values",
        workload_group="standard",
    )
    workload_variable(
        "N-BCASTs",
        default="1",
        description="Number of BCASTs",
        workload_group="standard",
    )
    workload_variable(
        "BCASTs",
        default="0",
        description="BCAST values",
        workload_group="standard",
    )
    workload_variable(
        "N-DEPTHs",
        default="1",
        description="Number of DEPTHs",
        workload_group="standard",
    )
    workload_variable(
        "DEPTHs",
        default="0",
        description="DEPTH values",
        workload_group="standard",
    )
    workload_variable(
        "SWAP",
        default="2",
        description="Swapping algorithm",
        workload_group="standard",
    )
    workload_variable(
        "swapping_threshold",
        default="64",
        description="Swapping threshold",
        workload_group="standard",
    )
    workload_variable(
        "L1",
        default="0",
        description="Storage for upper triangular portion of columns",
        workload_group="standard",
    )
    workload_variable(
        "U",
        default="0",
        description="Storage for the rows of U",
        workload_group="standard",
    )
    workload_variable(
        "Equilibration",
        default="1",
        description="Determines if equilibration should be enabled or disabled.",
        workload_group="standard",
    )
    workload_variable(
        "mem_alignment",
        default="8",
        description="Sets the alignment in doubles for memory addresses",
        workload_group="standard",
    )

    # calculator workload-specific variables:

    workload_variable(
        "percent_mem",
        default="85",
        description="Percent of memory to use (default 85)",
        workload_group="calculator",
    )

    workload_variable(
        "memory_per_node",
        default="240",
        description="Memory per node in GB",
        workload_group="calculator",
    )

    workload_variable(
        "block_size",
        default="384",
        description="Size of each block",
        workload_group="calculator",
    )

    workload_variable(
        "pfact",
        default="0",
        description="PFACT for optimized calculator",
        workload_group="calculator",
    )

    workload_variable(
        "nbmin",
        default="2",
        description="NBMIN for optimized calculator",
        workload_group="calculator",
    )

    workload_variable(
        "rfact",
        default="0",
        description="RFACT for optimized calculator",
        workload_group="calculator",
    )

    workload_variable(
        "bcast",
        default="0",
        description="BCAST for optimized calculator",
        workload_group="calculator",
    )

    workload_variable(
        "depth",
        default="0",
        description="DEPTH for optimized calculator",
        workload_group="calculator",
    )

    # FOMs:
    figure_of_merit(
        "Time",
        fom_regex=r".*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n",
        group_name="time",
        units="s",
        contexts=["problem-name"],
    )

    figure_of_merit(
        "GFlops",
        fom_regex=r".*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n",
        group_name="gflops",
        units="GFLOP/s",
        contexts=["problem-name"],
    )

    figure_of_merit_context(
        "problem-name",
        regex=r".*\s+(?P<N>[0-9]+)\s+(?P<NB>[0-9]+)\s+(?P<P>[0-9]+)\s+(?P<Q>[0-9]+)\s+(?P<time>[0-9]+\.[0-9]+)\s+(?P<gflops>[0-9].*)\n",
        output_format="N-NB-P-Q = {N}-{NB}-{P}-{Q}",
    )

    # MxP FOMs
    gflops_regex = (
        r"\s+GFLOPS = (?P<gflops>\S+), per GPU =\s+(?P<per_gflops>\S+)"
    )
    lu_gflops_regex = (
        r"\s+LU GFLOPS = (?P<gflops>\S+), per GPU =\s+(?P<per_gflops>\S+)"
    )
    figure_of_merit(
        "Total GFLOPs",
        fom_regex=gflops_regex,
        group_name="gflops",
        units="GFLOPs",
    )
    figure_of_merit(
        "Per GPU GFLOPs",
        fom_regex=gflops_regex,
        group_name="per_gflops",
        units="GFLOPs",
    )

    figure_of_merit(
        "Total LU GFLOPs",
        fom_regex=lu_gflops_regex,
        group_name="gflops",
        units="GFLOPs",
    )
    figure_of_merit(
        "Per GPU LU GFLOPs",
        fom_regex=lu_gflops_regex,
        group_name="per_gflops",
        units="GFLOPs",
    )

    # ( setting_name, setting_description )
    hpl_settings = [
        ("output_file", "output file name (if any)"),
        ("device_out", "(FORTRAN) device out (6=stdout,7=stderr,file)"),
        ("N-Ns", "Number of problem sizes (N)"),
        ("Ns", "Ns, Problem Sizes"),
        ("N-NBs", "Number of NBs"),
        ("NBs", "NBs, Block sizes"),
        ("PMAP", "PMAP process mapping (0=Row-,1=Column-major)"),
        ("N-Grids", "Number of Grids, process grids (P x Q)"),
        ("Ps", "Ps, Dimension 1 parallelization"),
        ("Qs", "Qs, Dimension 2 parallelization"),
        ("threshold", "threshold"),
        ("NPFACTs", "Number of PFACTs, panel fact"),
        ("PFACTs", "PFACT Values (0=left, 1=Crout, 2=Right)"),
        ("N-NBMINs", "Number of NBMINs, recursive stopping criteria"),
        ("NBMINs", "NBMINs (>= 1)"),
        ("N-NDIVs", "Number of NDIVs, panels in recursion"),
        ("NDIVs", "NDIVs"),
        ("N-RFACTs", "Number of RFACTS, recursive panel fact."),
        ("RFACTs", "RFACTs (0=left, 1=Crout, 2=Right)"),
        ("N-BCASTs", "Number of BCASTs, broadcast"),
        (
            "BCASTs",
            "BCASTs (0=1rg,1=1rM,2=2rg,3=2rM,4=Lng,5=LnM,6=MKL BPUSH,7=AMD Hybrid Panel)",
        ),
        ("N-DEPTHs", "Number of DEPTHs, lookahead depth"),
        ("DEPTHs", "DEPTHs (>=0)"),
        ("SWAP", "SWAP (0=bin-exch,1=long,2=mix)"),
        ("swapping_threshold", "swapping_threshold"),
        ("L1", "L1 in (0=transposed,1=no-transposed) form"),
        ("U", "U  in (0=transposed,1=no-transposed) form"),
        ("Equilibration", "Equilibration (0=no,1=yes)"),
        ("mem_alignment", "memory alignment in double (> 0)"),
    ]

    # Integer sqrt
    def _isqrt(self, n):
        if n < 0:
            raise Exception
        elif n < 2:
            return n
        else:
            lo = self._isqrt(n >> 2) << 1
            hi = lo + 1
            if (hi * hi) > n:
                return lo
            else:
                return hi

    register_phase(
        "calculate_values", pipeline="setup", run_before=["make_experiments"]
    )

    def _calculate_values(self, workspace, app_inst):
        expander = self.expander
        calculated_settings = {}
        if "calculator" in expander.workload_name:
            # Find the best P and Q whose product is the number of available
            # cores, with P less than Q
            nNodes = int(expander.expand_var_name("n_nodes"))
            processesPerNode = int(
                expander.expand_var_name("processes_per_node")
            )

            totalCores = nNodes * processesPerNode

            bestP = self._isqrt(totalCores)
            while (
                totalCores % bestP
            ) > 0:  # stops at 1 because any int % 1 = 0
                bestP -= 1

            bestQ = totalCores // bestP

            # Find LCM(P,Q)
            P = int(bestP)
            Q = int(bestQ)
            lcmPQ = Q  # Q is always the larger of P and Q
            while (lcmPQ % P) > 0:
                lcmPQ += Q

            # HPL maintainers recommend basing the target problem size on
            # the square root of 80% of total memory in words.
            memoryPerNode = int(expander.expand_var_name("memory_per_node"))
            memFraction = int(expander.expand_var_name("percent_mem")) / 100
            blockSize = int(expander.expand_var_name("block_size"))
            one_gb_mem_in_words = (1 << 30) / 8

            fullMemWords = nNodes * memoryPerNode * one_gb_mem_in_words

            targetProblemSize = math.sqrt(fullMemWords * memFraction)

            # Ensure that N is divisible by NB * LCM(P,Q)
            problemSize = int(targetProblemSize)
            problemSize -= problemSize % blockSize
            nBlocks = problemSize // blockSize
            nBlocks -= nBlocks % lcmPQ
            problemSize = blockSize * nBlocks
            usedPercentage = int(problemSize**2 / fullMemWords * 100)

            for name, var in self.workloads["standard"].variables.items():
                if var.name not in self.variables:
                    self.define_variable(var.name, var.default)

            # Key = Variable name
            #      Value: Value to override variable with
            #      Comment: Comment to append to variable comment
            calculated_settings = {
                "N-Ns": {"value": 1},
                "Ns": {
                    "value": int(problemSize),
                    "comment": f"(= {usedPercentage}% of total available memory)",
                },
                "N-NBs": {"value": 1},
                "NBs": {"value": blockSize},
                "Ps": {"value": int(bestP)},
                "Qs": {"value": int(bestQ)},
                "N-Grids": {"value": 1},
            }

        # Handle applying overrides, and apply comments to variable definitions.
        # If workload is calculator, `calculated_settings` is defined
        # If workload is standard, `calculated_settings` is empty
        for setting, comment in self.hpl_settings:
            pad_comment = ""
            if comment is not None:
                pad_comment = comment
            value = self.expander.expand_var_name(setting)

            if setting in calculated_settings:
                if "value" in calculated_settings[setting]:
                    value = calculated_settings[setting]["value"]
                if "comment" in calculated_settings[setting]:
                    pad_comment += (
                        " " + calculated_settings[setting]["comment"]
                    )

            if "mxp" in self.expander.workload_name:
                self.define_variable(setting, value)
            else:
                self.define_variable(setting, pad_value(value, pad_comment))

    def _make_experiments(self, workspace, app_inst=None):
        super()._make_experiments(workspace)

        input_path = os.path.join(
            self.expander.expand_var_name("experiment_run_dir"), "HPL.dat"
        )

        settings = [
            "output_file",
            "device_out",
            "N-Ns",
            "Ns",
            "N-NBs",
            "NBs",
            "PMAP",
            "N-Grids",
            "Ps",
            "Qs",
            "threshold",
            "NPFACTs",
            "PFACTs",
            "N-NBMINs",
            "NBMINs",
            "N-NDIVs",
            "NDIVs",
            "N-RFACTs",
            "RFACTs",
            "N-BCASTs",
            "BCASTs",
            "N-DEPTHs",
            "DEPTHs",
            "SWAP",
            "swapping_threshold",
            "L1",
            "U",
            "Equilibration",
            "mem_alignment",
        ]

        with open(input_path, "w+") as f:
            f.write("    HPLinpack benchmark input file\n")
            f.write(
                "Innovative Computing Laboratory, University of Tennessee\n"
            )

            for setting in settings:
                # This gets around an issue in expander where trailing comments
                # after '#' are not printed
                hash_replace_str = self.expander.expand_var_name(
                    setting
                ).replace("Number", "#")
                f.write(hash_replace_str + "\n")

            # Write some documentation at the bottom of the input file:
            f.write(
                "##### This line (no. 32) is ignored (it serves as a separator). ######"
            )

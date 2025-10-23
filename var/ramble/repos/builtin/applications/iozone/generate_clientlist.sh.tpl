#!/bin/bash

awk -v total="{n_ranks}" -v wd="{working_directory}" -v path="{iozone_bin_path}" '
    {
        hosts[NR-1] = $1
    }
    END {
        num_hosts = NR
        ppn = int("{processes_per_node}")
        for (h = 0; h < num_hosts; h++) {
            for (p = 0; p < ppn; p++) {
                print hosts[h], wd, path
            }
        }
    }
' "{hostfile_path}" > "{clientlist_path}"

#!/bin/bash
#SBATCH -N {n_nodes}
#SBATCH --ntasks-per-node {processes_per_node}

# This is a template execution script for
# running the execute pipeline.
#
# Variables surrounded by curly braces will be expanded
# when generating a specific execution script.
# Available variables are:
#   - exp_dir (Will be replaced with the experiment directory)
#   - command (Will be replaced with the command to run the experiment)
#   - log_dir (Will be replaced with the logs directory)
#   - exp_name (Will be replaced with the name of the experiment)
#   - workload_dir (Will be replaced with the directory of the workload
#   - app_name (Will be replaced with the name of the application)
#   - n_nodes (Will be replaced with the required number of nodes)
#   Any experiment parameters will be available as variables as well.

cd {experiment_run_dir}

{spack_setup}

export OMP_NUM_THREADS={n_threads}

scontrol show hostnames ${SLURM_JOB_NODELIST} > hostfile

{command}


---
name: ramble-workflow-managers
description: "Guide for configuring workflow managers (Slurm, GKE-MPI, user-managed) and batch schedulers in Ramble workspaces."
---

# Ramble Workflow Managers Guide

This skill provides guidelines for integrating workload managers and batch schedulers (starting with **Slurm**) in Ramble workspaces.

---

## 1. Overview & Workflow Manager Selection

Ramble abstracts job submission and batch scheduling via **Workflow Managers**. Configure the active workflow manager in the workspace `variants:` block:

```yaml
ramble:
  variants:
    workflow_manager: slurm
```

Available Workflow Managers can be listed via CLI:
```bash
ramble list --type workflow_managers
```
Common workflow managers include:
- `user-managed`: Direct local command execution (default).
- `slurm`: Slurm Workload Manager batch script generation (`#SBATCH`) and submission (`sbatch`).
- `gke-mpi`: Kubernetes/GKE MPI operator job generation.

---

## 2. Slurm Workflow Manager Configuration

When `workflow_manager: slurm` is active, Ramble generates executable batch submission scripts containing appropriate `#SBATCH` directives.

### Key Slurm Variables

Set batch parameters in the top-level `variables:` or experiment scope:

```yaml
ramble:
  variants:
    workflow_manager: slurm

  variables:
    n_nodes: 4
    processes_per_node: 32
    n_ranks: '{n_nodes} * {processes_per_node}'
    slurm_partition: 'hpc-partition'         # Maps to #SBATCH --partition
    time: '02:00:00'               # Maps to #SBATCH --time
    account: 'my-project-account'  # Maps to #SBATCH --account
    reservation: 'hpc-res'         # Maps to #SBATCH --reservation (optional)
```

### Best Practice: Let Workflow Manager Control Launchers
When using a workflow manager like Slurm, **do not manually set `batch_submit` or `mpi_command`** unless explicitly overriding defaults. The workflow manager automatically generates optimized `sbatch` headers and `srun`/`mpirun` invocation flags based on cluster configurations.

---

## 3. Dynamic Launcher Overrides (Advanced)

If comparing different MPI implementations (e.g., OpenMPI vs Intel MPI) under Slurm where launcher flags differ:

```yaml
ramble:
  variants:
    workflow_manager: slurm

  variables:
    slurm_partition: standard
    mpi_type: [intel-mpi, openmpi]
    intel-mpi_command: 'mpiexec -f {hostfile} -ppn {processes_per_node} -n {n_ranks}'
    openmpi_command: 'mpirun -hostfile {hostfile} -npernode {processes_per_node} -n {n_ranks}'
    mpi_command: '{{{mpi_type}_command}}'

  applications:
    hostname:
      workloads:
        local:
          experiments:
            exp_{mpi_type}:
              matrix:
                - mpi_type
```

---

## 4. Batch Execution Lifecycle & Executor Options

Launch batch execution using `ramble on`:

```bash
ramble -D <workspace> on
```

For advanced batch interaction, pass `--executor` flags to interact with cluster batch query or cancellation commands:

```bash
# Query active jobs
ramble -D <workspace> on --executor "{batch_query}"

# Cancel running workspace jobs
ramble -D <workspace> on --executor "{batch_cancel}"
```

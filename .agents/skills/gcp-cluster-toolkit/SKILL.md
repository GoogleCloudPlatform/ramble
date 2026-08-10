---
name: gcp-cluster-toolkit
description: "Guide for provisioning Google Cloud HPC and AI clusters using Cluster Toolkit (ghpc) to host Ramble experiments."
---

# Google Cloud Cluster Toolkit Integration Guide

This skill provides guidelines for provisioning HPC and AI clusters on Google Cloud Platform using **Google Cloud Cluster Toolkit (`ghpc`)** and integrating them with Ramble for benchmark experimentation.

---

## 1. Documentation & Agent Context References

When working with Cluster Toolkit and `gcloud`, refer to official documentation resources and check for environment agent context files:

- **Cluster Toolkit Documentation**: [Google Cloud Cluster Toolkit Docs](https://cloud.google.com/cluster-toolkit/docs) and [GitHub Repository](https://github.com/GoogleCloudPlatform/cluster-toolkit).
- **Google Cloud CLI Documentation**: [gcloud CLI Overview](https://cloud.google.com/sdk/gcloud).
- **Environment Agent Instructions**: Check if there are local `AGENTS.md` or skill definitions for Cluster Toolkit or `gcloud` in your environment or workspace before executing provisioning tasks.

---

## 2. Overview of Cluster Toolkit (`ghpc`)

Google Cloud Cluster Toolkit is an open-source tool that automates the deployment of high-performance computing (HPC) environments on GCP using Terraform. It provides modular blueprints for:
- Slurm HPC Clusters (with compute partitions, auto-scaling, and Slurm accounting).
- AI/ML Training Clusters (NVIDIA H100/A3, TPU v5p, GKE MPI operator).
- High-Performance Storage (Parallelstore, Filestore, Cloud Storage FUSE).

---

## 3. Cluster Provisioning Workflow

### Step 1: Create Blueprint YAML
Define cluster topology in a Cluster Toolkit blueprint (e.g., `hpc-cluster.yaml`):

```yaml
blueprint_name: ramble-hpc-cluster

vars:
  project_id: my-gcp-project
  deployment_name: ramble-slurm
  region: us-central1
  zone: us-central1-a

deployment_groups:
- group: primary
  modules:
  - id: network
    source: modules/network/vpc

  - id: slurm_login
    source: community/modules/scheduler/slurm-gcp-v6-login
    use: [network]

  - id: compute_partition
    source: community/modules/scheduler/slurm-gcp-v6-nodeset-bucket
    settings:
      node_count_dynamic_max: 16
      machine_type: c2-standard-60

  - id: slurm_controller
    source: community/modules/scheduler/slurm-gcp-v6-controller
    use: [network, slurm_login, compute_partition]
```

### Step 2: Build Deployment & Apply Terraform
```bash
# Build Terraform files from blueprint
ghpc create hpc-cluster.yaml

# Deploy cluster infrastructure
cd ramble-slurm/primary
terraform init
terraform apply -auto-approve
```

---

## 4. Preparing the Cluster Login Node for Ramble

### SSH to Login Node
```bash
gcloud compute ssh --zone "us-central1-a" "ramble-slurm-login-0" --project "my-gcp-project"
```

### Install Ramble & Spack on Shared Filesystem
Clone Ramble into a shared directory (e.g., `/home` or `/nfs`):

```bash
cd /home/$USER
git clone https://github.com/GoogleCloudPlatform/ramble.git
source ramble/share/ramble/setup-env.sh
```

---

## 5. Configuring Ramble Workspaces for Cloud Scaling

When running experiments on a GCP Cluster Toolkit provisioned Slurm cluster:

1. Set `config: workflow_manager: slurm` in `ramble.yaml`.
2. Use dynamic cloud instance PPN patterns for A/B machine comparisons:

```yaml
ramble:
  config:
    workflow_manager: slurm

  variables:
    machine_type: [c2_ppn, c3_ppn]
    c2_ppn: 60
    c3_ppn: 176
    processes_per_node: '{{{machine_type}}}'
    n_nodes: [1, 2, 4, 8]
    n_ranks: '{n_nodes} * {processes_per_node}'

  applications:
    hostname:
      workloads:
        local:
          experiments:
            cloud_scaling_{n_nodes}nodes:
              matrix:
                - n_nodes
                - machine_type
```

---

## 6. Teardown & Resource Cleanup

To prevent unnecessary cloud billing after experiment runs finish, tear down cluster infrastructure:

```bash
cd ramble-slurm/primary
terraform destroy -auto-approve
```

.. Copyright 2022-2026 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.


.. _workflow-manager-control:

=================
Workflow Managers
=================

Within Ramble's :ref:`variants configuration section <variants-config>`, users
can control which workflow manager is used for a set of experiments.

The workflow manager used controls many aspects of the experiment, and is
intended to broadly map to a workload manager. Experiments in a workspace can
select different workflow managers, and workflow managers can define additional
templates and logic that can construct complex workflows. These can include
getting an experiment's status, cancelling an experiment, or submitting an
experiment to a scheduler.

-----------------------------
Configuring Workflow Managers
-----------------------------

Workflow managers are controlled through a config option in the 
:ref:`variants configuration section <variants-config>`. The following shows an
example of controlling this

.. code-block:: yaml

  variants:
    workflow_manager: <workflow_manager_name>

The default workflow manager is ``user-managed`` which simply requires the user
to define the ``mpi_command`` and ``batch_submit`` variables to construct a working
workflow. The value of the workflow manager variant used can be a reference to a
variable, and will be expanded following Ramble's :ref:`variable definitions
<variable-dictionaries>` logic.

---------------------------
Supported Workflow Managers
---------------------------

Some of the currently supported workflow managers in Ramble include:

 * gke-mpi
 * google-batch
 * slurm
 * slurm-intel-mpi
 * slurm-pyxis
 * user-managed

^^^^^^^^^^^^^^^^^^^^^^^^
GKE MPI Workflow Manager
^^^^^^^^^^^^^^^^^^^^^^^^

Selecting the ``gke-mpi`` workflow manager will cause generated experiments to
create YAML formatted GKE manifest files for their experiments. Additionally,
the commands for submitting, and querying experiments will be handled through
``kubectl``.

It is important to note that GKE generally relies on containerized workloads.
Ramble supports additional mechanisms for testing containerized workflows, but
users might need to provide their own container for running in this mode.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Google Batch Workflow Manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Selecting the ``google-batch`` workflow manager will enable the use of the Google
Cloud Batch workflow. With this, experiments will have YAML formatted job
manifests generated that can be submitted to Google's cloud batch scheduler.

Additionally, submission and query commands utilize the ``gcloud`` cli command.

^^^^^^^^^^^^^^^^^^^^^^^^
SLURM* Workflow Managers
^^^^^^^^^^^^^^^^^^^^^^^^

There is a family of workflow managers that all apply some layered
functionality of Slurm on the generated experiments. The most basic of these is
the ``slurm`` workflow manager which uses a traditional SLURM workflow, including
the use of ``sbatch`` and ``srun``.

The ``slurm-intel-mpi`` workflow manager augments the base SLURM workflow manager
to use Intel MPI with ``srun``.

The ``slurm-pyxis`` workflow manager alternatively uses ``srun`` to run
containerized workloads. These are somewhat expected to have the ``pyxis-enroot``
modifier applied to them as well, to ensure the proper format.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
User Managed Workflow Manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``user-managed`` workflow manager can be selected if a user wants to control
all aspects of the workflow themselves within the workspace. In this case, the
user should specify all required variables in the workspace's configuration
file.

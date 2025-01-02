.. Copyright 2022-2025 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _modifying_an_experiment_tutorial:

=======================================
3) Modifying A GROMACS Experiment
=======================================

In this tutorial, you will learn how to modify an existing workspace
configuration that contains experiments using
`GROMACS <https://www.gromacs.org/>`_, a free and open-source application
for molecular dynamics.

This tutorial builds off of concepts introduced in previous tutorials. Please
make sure you review those before starting with this tutorial's content.

.. include:: shared/gromacs_workspace.rst

Experiment Descriptions
-----------------------

Now that your workspace has been configured, and activated, You can execute the
following command to see what experiments the workspace currently contains:

.. code-block:: console

    $ ramble workspace info

This command provides a summary view of the workspace. It includes the
experiment names, and the software environments. As an example, its output
might contain the following information:

.. code-block:: console

    Experiments:
      Application: gromacs
        Workload: water_gmx50
          Experiment: gromacs.water_gmx50.pme_single_rank
      Application: gromacs
        Workload: water_gmx50
          Experiment: gromacs.water_gmx50.rf_single_rank
      Application: gromacs
        Workload: water_bare
          Experiment: gromacs.water_bare.pme_single_rank
      Application: gromacs
        Workload: water_bare
          Experiment: gromacs.water_bare.rf_single_rank

To get detailed information about where variable definitions come from, you can use:

.. code-block:: console

    $ ramble workspace info --expansions

The experiments section of this command's output might contain the following:

.. code-block:: console

    Experiments:
      Application: gromacs
        Workload: water_gmx50
          Experiment: gromacs.water_gmx50.pme_single_rank
            Variables from Workspace:
              processes_per_node = 16 ==> 16
              mpi_command = mpirun -n {n_ranks} -ppn {processes_per_node} ==> mpirun -n 1 -ppn 16
              batch_submit = {execute_experiment} ==> {execute_experiment}
            Variables from Experiment:
              n_ranks = 1 ==> 1
              n_threads = 1 ==> 1
              size = 0003 ==> 0003
              type = pme ==> pme
      Application: gromacs
        Workload: water_gmx50
          Experiment: gromacs.water_gmx50.rf_single_rank
            Variables from Workspace:
              processes_per_node = 16 ==> 16
              mpi_command = mpirun -n {n_ranks} -ppn {processes_per_node} ==> mpirun -n 1 -ppn 16
              batch_submit = {execute_experiment} ==> {execute_experiment}
            Variables from Experiment:
              n_ranks = 1 ==> 1
              n_threads = 1 ==> 1
              size = 0003 ==> 0003
              type = rf ==> rf
      Application: gromacs
        Workload: water_bare
          Experiment: gromacs.water_bare.pme_single_rank
            Variables from Workspace:
              processes_per_node = 16 ==> 16
              mpi_command = mpirun -n {n_ranks} -ppn {processes_per_node} ==> mpirun -n 1 -ppn 16
              batch_submit = {execute_experiment} ==> {execute_experiment}
            Variables from Experiment:
              n_ranks = 1 ==> 1
              n_threads = 1 ==> 1
              size = 0003 ==> 0003
              type = pme ==> pme
      Application: gromacs
        Workload: water_bare
          Experiment: gromacs.water_bare.rf_single_rank
            Variables from Workspace:
              processes_per_node = 16 ==> 16
              mpi_command = mpirun -n {n_ranks} -ppn {processes_per_node} ==> mpirun -n 1 -ppn 16
              batch_submit = {execute_experiment} ==> {execute_experiment}
            Variables from Experiment:
              n_ranks = 1 ==> 1
              n_threads = 1 ==> 1
              size = 0003 ==> 0003
              type = rf ==> rf

The variables ``mpi_command``, ``processes_per_node``, and ``batch_submit``
come from the workspace scope towards the top of the YAML file. Each experiment
has its own definition for ``n_ranks``, ``n_threads``, ``size``, and ``type``.

The experiments in this configuration use both the ``water_bare`` and
``water_gmx50`` workloads.

Using Workload Variables
------------------------

Application definitions are allowed to expose variables that can be used within
experiments. These are called **workload variables**. User can view the
available variables with the following command:

.. code-block:: console

    $ ramble info --attrs workloads -v -p "water*" gromacs

Which should contain the following information:

.. code-block:: console

    Workload: water_gmx50
        Executables: ['pre-process', 'execute-gen']
        Inputs: ['water_gmx50_bare']
        Tags: []
        Variables:
            size:
                Description: Workload size
                Default: 1536
                Suggested Values: ['0000.65', '0000.96', '0001.5', '0003', '0006', '0012', '0024', '0048', '0096', '0192', '0384', '0768', '1536', '3072']
            type:
                Description: Workload type.
                Default: pme
                Suggested Values: ['pme', 'rf']
            input_path:
                Description: Input path for water GMX50
                Default: {water_gmx50_bare}/{size}
    Workload: water_bare
        Executables: ['pre-process', 'execute-gen']
        Inputs: ['water_bare_hbonds']
        Tags: []
        Variables:
            size:
                Description: Workload size
                Default: 1536
                Suggested Values: ['0000.65', '0000.96', '0001.5', '0003', '0006', '0012', '0024', '0048', '0096', '0192', '0384', '0768', '1536', '3072']
            type:
                Description: Workload type.
                Default: pme
                Suggested Values: ['pme', 'rf']
            input_path:
                Description: Input path for water bare hbonds
                Default: {water_bare_hbonds}/{size}


Within each of the workloads your workspace has experiments for, you can see
definitions for both ``size`` and ``type``. The ``Suggested Values`` attribute
defines possible values for each of the variables, which can be defined within
your workspace's ``ramble.yaml`` file.

While these variables contain ``Suggested Values`` some other variable
definitions can take any value you want. As a result, they might not provide
anything other than a default value. While the default value is expected to
function properly, you are allowed to override their definition within the
``ramble.yaml`` if your experiments would benefit from it. However, be aware
that this also has the potential to change the behavior of your experiments and
is considered an advanced action.

Editing Experiments
-------------------

Now that you know how to determine which values are possible, select one or
more of the possible values for the ``size`` variable. You will modify the
experiments in your workspace to use this (remember, you have 4 experiments
defined currently).

**NOTE** The larger the value, the more expensive the
experiment will be. However you can give each experiment a unique value.

To make editing the workspace easier, use the following command (assuming you
have an ``EDITOR`` environment variable set):

.. code-block:: console

    $ ramble workspace edit

This command opens the ``ramble.yaml`` file, along with any ``*.tpl`` files in
the workspace's ``configs`` directory. The root directory of the workspace can
be seen in the ``Location`` attribute output from:

.. code-blocks:: console

    $ ramble workspace info


When the ``ramble.yaml`` is open, modify any of the experiment's ``size``
variable definitions that you want to. Finally, save and exit the file.

These changes should now be reflected in the output of:

.. code-block:: console

    $ ramble workspace info --expansions

.. include:: shared/gromacs_execute.rst

If you have a ``results`` file from the :ref:`previous tutorial <running_an_experiment_tutorial>`,
you can compare it with the newly created results file to see what impact
changing the ``size`` variable had on your figures of merit.

Cleaning the Workspace
----------------------

After you are finished with the content of this tutorial, make sure you
deactivate your workspace using:

.. code-block:: console

    $ ramble workspace deactivate

If you no longer need the workspace materials, remove the entire workspace
with:

.. code-block:: console

    $ ramble workspace remove basic_gromacs

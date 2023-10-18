.. Copyright 2022-2023 Google LLC

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _running_an_experiment_tutorial:

=======================================
1) Running A Simple GROMACS Experiment
=======================================

This tutorial will provide a basic introduction to navigating Ramble and running
experiments. In this tutorial, you will set up and run a benchmark simulation
using `GROMACS <https://www.gromacs.org/>`_, a free and open-source application
for molecular dynamics.

------------
Installation
------------

To install Ramble, see the :doc:`../getting_started` guide.

----------------------
Available Applications
----------------------

Once Ramble is installed, viewing the available application definitions is as
simple as executing:

.. code-block:: console

    $ ramble list

The ``ramble list`` command also takes a query string, which can be used to
filter available application definitions. For example:

.. code-block:: console

    $ ramble list hp*

might output the following:

.. code-block:: console

    ==> 3 applications
    hpcc  hpcg  hpl

Additionally, applications can be filtered by their tags, e.g.

.. code-block:: console

    $ ramble list -t molecular-dynamics
    ==> 4 applications
    gromacs  hmmer  lammps  namd

The available tags (and their mappings to applications) can be listed using:

.. code-block:: console

    $ ramble attributes --all --tags

^^^^^^^^^^^^^^^^^^^^^^^^^
What's in an application?
^^^^^^^^^^^^^^^^^^^^^^^^^

Knowing what applications are available is only part of how you interact
with Ramble. Each application contains one or more workloads, all of which can
contain their own variables to control their behavior. The ``ramble info``
command can be used to get more information about a specific application
definition. As an example:

.. code-block:: console

    $ ramble info gromacs

Will print the workloads and variables the ``GROMACS`` application definition contains.

------------------------
Configuring experiments
------------------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Create and Activate a Workspace
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Before you can configure your GROMACS experiments, you'll need to set up a
workspace. You can call this workspace ``basic_gromacs``.

.. code-block:: console

    $ ramble workspace create basic_gromacs

This will create a workspace for you in:

.. code-block:: console

    $ $ramble_root/var/ramble/workspaces/basic_gromacs

Now you can activate the workspace and view its default configuration.

.. code-block:: console

    $ ramble workspace activate basic_gromacs
    $ ramble workspace info

You can use the ``ramble workspace info`` command after editing configuration
files to see how ramble would use the changes you made.

^^^^^^^^^^^^^^^^^^^^^^^^
Configure the Workspace
^^^^^^^^^^^^^^^^^^^^^^^^

Within the workspace directory, ramble creates a directory named ``configs``.
This directory contains generated configuration and template files. Each of
these files can be edited to configure the workspace, and examples will be
provided below.

The available files are:
* ``ramble.yaml`` This file describes all aspects of the workspace. This
includes the software stack, the experiments, and all variables.
* ``execute_experiment.tpl`` This file is a template shell script that will be
rendered to execute each of the experiments that ramble generates.

You can edit these files directly or with the command ``ramble workspace edit``.

To begin, you should edit the ``ramble.yaml`` file to set up the configuration
for your experiments. For this tutorial, replace the default yaml text with the
contents of ``$ramble_root/examples/basic_gromacs_config.yaml``:

.. code-block:: yaml

    ramble:
      variables:
        processes_per_node: 1
        mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
        batch_submit: '{execute_experiment}'
      applications:
        gromacs: # Application name, from `ramble list`
          workloads:
            water_gmx50: # Workload name from application, in `ramble info <app>`
              experiments:
                pme_single_rank: # Arbitrary experiment name
                  variables:
                    n_ranks: '1'
                    n_threads: '1'
                    size: '0003'
                    type: 'pme'
                rf_single_rank: # Arbitrary experiment name
                  variables:
                    n_ranks: '1'
                    n_threads: '1'
                    size: '0003'
                    type: 'rf'
            water_bare: # Workload name from application, in `ramble info <app>`
              experiments:
                pme_single_rank: # Arbitrary experiment name
                  variables:
                    n_ranks: '1'
                    n_threads: '1'
                    size: '0003'
                    type: 'pme'
                rf_single_rank: # Arbitrary experiment name
                  variables:
                    n_ranks: '1'
                    n_threads: '1'
                    size: '0003'
                    type: 'rf'
      spack:
        concretized: true
        packages:
          gcc9:
            spack_spec: gcc@9.3.0 target=x86_64
            compiler_spec: gcc@9.3.0
          impi2018:
            spack_spec: intel-mpi@2018.4.274 target=x86_64
            compiler: gcc9
          gromacs:
            spack_spec: gromacs@2021.6
            compiler: gcc9
        environments:
          gromacs:
            packages:
            - gromacs
            - impi2018

Note that specifying compilers that Spack doesn't have installed may take a while.
To see available compilers, use ``spack compilers`` or see `Spack documentation
<https://spack.readthedocs.io/en/latest/getting_started.html#spack-compilers>`_
for more information.

The second file you should edit is the ``execute_experiment.tpl`` template file.
This file contains a template script that will be rendered into an execution
script for each generated experiment. You can feel free to edit it as you need
to for your given system, but for this tutorial the default value will work.

^^^^^^^^^^^^^^^^^^^^^^^^^^^
Setting Up the Experiments
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now that the workspace is configured correctly, you can set up the experiments
in the active workspace using:

.. code-block:: console

    $ ramble workspace setup

This command will create experiment directories, download and expand input files,
and install the required software stack (and generate spack environments for
each workload).

It can take a bit to run depending on if you need to build new software and how
long the input files take to download. If you'd like to see what will be installed,
you can do a dry run of the setup using:

.. code-block:: console

    $ ramble workspace setup --dry-run

For each setup run, a set of logs will be created at:

.. code-block:: console

    $ $ramble_root/var/ramble/workspaces/$workspace_root/logs

Each run will have its own primary log, along with a folder containing a log for each
experiment that is being configured.

^^^^^^^^^^^^^^^^^^^^^^
Executing Experiments
^^^^^^^^^^^^^^^^^^^^^^

After the workspace is set up, its experiments can be executed. The two methods
to run the experiments are:

.. code-block:: console

    $ ramble on
   or;
    $ ./all_experiments

^^^^^^^^^^^^^^^^^^^^^^
Analyzing Experiments
^^^^^^^^^^^^^^^^^^^^^^

Once the experiments within a workspace are complete, the experiments can be
analyzed. This is done through:

.. code-block:: console

    $ ramble workspace analyze

This creates a ``results`` file in the root of the workspace that contains
extracted figures of merit. If the experiments were successful, this file will
show the following results:

* Core Time: CPU time (in seconds) spent on the benchmark calculations
* Wall Time: Elapsed real time (in seconds) spent on the benchmark calculations
* Percent Core Time: Core Time / Wall Time
* Nanosecs per day: Nanoseconds of simulation per day at the speed achieved
* Hours per nanosec: Hours required to calculate 1 nanosecond of simulation at
  the speed achieved

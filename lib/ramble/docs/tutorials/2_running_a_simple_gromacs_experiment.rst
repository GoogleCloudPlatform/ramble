.. Copyright 2022-2025 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _running_an_experiment_tutorial:

=======================================
2) Running A Simple GROMACS Experiment
=======================================

In this tutorial, you will set up and run a benchmark simulation using
`GROMACS <https://www.gromacs.org/>`_, a free and open-source application
for molecular dynamics.

This tutorial builds off of concepts introduced in previous tutorials. Please
make sure you review those before starting with this tutorial's content,
however this tutorial is fully stand-alone as far as steps you need to perform.

Application Information
-----------------------

As mentioned above, this tutorial uses the `GROMACS <https://www.gromacs.org/>`_
application definition. We will begin with the ``water_bare`` and ``water_gmx50``
workloads, as they are able to execute in a short amount of time.

Using a previously installed ``ramble``, the following command can be used to
get information about these workloads:

.. code-block:: console

    $ ramble info --attrs workloads -v -p "water*" gromacs

Under the workloads marked by ``Workload: water_bare`` and
``Workload: water_gmx50``, you should see something like the following output:

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

Here we see that both of these workloads have a ``type`` variable (with
possible values of ``pme`` and ``rf``) and a ``size`` variable with a variety
of available sizes.

To determine a suggested software configuration, you can use:

.. code-block:: console

  $ ramble info --attrs software_specs,compilers -v gromacs

With this command, you should see output similar to the following:

.. code-block:: console

  ##################
  # software_specs #
  ##################
  impi2018:
      pkg_spec: intel-mpi@2018.4.274
      compiler_spec: None
      compiler: None
      package_manager: spack*
  
  spack_gromacs:
      pkg_spec: gromacs@2020.5
      compiler_spec: None
      compiler: gcc9
      package_manager: spack*
  
  eessi_gromacs:
      pkg_spec: GROMACS/2024.1-foss-2023b
      compiler_spec: None
      compiler: None
      package_manager: eessi
  
  #############
  # compilers #
  #############
  gcc9:
      pkg_spec: gcc@9.3.0
      compiler_spec: None
      compiler: None
      package_manager: spack*

This output does not represent the only possible configuration that works for
this application, it only presents a good starting point. When using Ramble,
these can be modified freely and will be explored in a later tutorial.

.. include:: shared/gromacs_workspace.rst

Setting Up the Experiments
---------------------------

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

    $ $RAMBLE_ROOT/var/ramble/workspaces/$workspace_root/logs

Each run will have its own primary log, along with a folder containing a log
for each experiment that is being configured. While setup is running, you can
monitor the process by looking at the contents of:

.. code-block:: console

    $ $RAMBLE_ROOT/var/ramble/workspaces/basic_gromacs/logs/setup.latest/gromacs.water_gmx50.pme_single_rank.out

Executing Experiments
---------------------

After the workspace is set up, its experiments can be executed. The two methods
to run the experiments are:

.. code-block:: console

    $ ramble on
   or;
    $ ./all_experiments

Analyzing Experiments
---------------------

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

Workspace Directory Structure
-----------------------------

After analyzing the workspace, you can exmine the structure of the workspace at:

.. code-block:: console

    $ $RAMBLE_ROOT/var/ramble/workspaces/basic_gromacs

Within this directory, you should see the following directories:

 * ``configs`` - Contains all of the configuration files for the workspace
 * ``experiments`` - Contains all of the experiment execution directories
 * ``inputs`` - Contains all of the input files needed for the experiments
 * ``logs`` - Contains all log files from any Ramble command that acts on the workspace
 * ``shared`` - Contains auxiliary files the experiment might need, such as environment variable information for licenses
 * ``software`` - Contains software environments for the experiments

Cleanup the Workspace
---------------------

Once you are finished with the tutorial content, ensure you have deactivated
the workspace using:

.. code-block:: console

    $ ramble workspace deactivate

Additionally, you can remove the workspace using:

.. code-block:: console

    $ ramble workspace remove basic_gromacs

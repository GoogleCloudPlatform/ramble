.. Copyright 2022-2023 Google LLC

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
application definition. We will begin with the `water_bare` and `water_gmx50`
workloads, as they are able to execute in a short amount of time.

Using a previously installed ``ramble``, the following command can be used to
get information about these workloads:
.. code-block:: console

    $ ramble info gromacs

Searching the output for the sections marked ``Workload: water_bare`` and
``Workload: water_gmx50``, you should see something like the following output:

.. code-block:: console

    Workload: water_gmx50
        Executables: ['builtin::env_vars', 'builtin::spack_source', 'builtin::spack_activate', 'pre-process', 'execute-gen']
        Inputs: ['water_gmx50_bare']
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
        Executables: ['builtin::env_vars', 'builtin::spack_source', 'builtin::spack_activate', 'pre-process', 'execute-gen']
        Inputs: ['water_bare_hbonds']
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

Towards the bottom of the output you should also see information about a valid
software configuration:

.. code-block:: console

   Default Compilers:
    gcc9:
      spack_spec = gcc@9.3.0

    Software Specs:
      impi2018:
        spack_spec = intel-mpi@2018.4.274
      gromacs:
        spack_spec = gromacs@2020.5
        compiler = gcc9

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

    $ $ramble_root/var/ramble/workspaces/$workspace_root/logs

Each run will have its own primary log, along with a folder containing a log for each
experiment that is being configured.

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

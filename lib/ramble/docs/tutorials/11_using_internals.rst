.. Copyright 2022-2023 Google LLC

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _internals_tutorial:

=============
11) Internals
=============

In this tutorial, you will learn how to use ``internals`` within experiments
for
`WRF <https://www.mmm.ucar.edu/models/wrf>`_, a free and open-source
application for atmospheric research and operational forecasting applications.

This tutorial builds off of concepts introduced in previous tutorials. Please
make sure you review those before starting with this tutorial's content.

Create a Workspace
------------------

To begin with, you need a workspace to configure the experiments. This can be
created with the following command:

.. code-block:: console

    $ ramble workspace create internals_wrf


Activate the Workspace
----------------------

Several of Ramble's commands require an activated workspace to function
properly. Activate the newly created workspace using the following command:
(NOTE: you only need to run this if you do not currently have the workspace
active).

.. code-block:: console

    $ ramble workspace activate internals_wrf

Configure Experiment Definitions
--------------------------------

To being with, you need to configure the workspace. The workspace's root
location can be seen under the ``Location`` output of:

.. code-block:: console

    $ ramble workspace info

Additionally, the files can be edited directly with:

.. code-block:: console

    $ ramble workspace edit

Within the ``ramble.yaml`` file, write the following contents, which the
final configuration from a previous tutorial.

.. code-block:: YAML

    ramble:
      variables:
        processes_per_node: 4
        n_ranks: '{processes_per_node}*{n_nodes}'
        batch_submit: '{execute_experiment}'
        mpi_command: mpirun -n {n_ranks}
      applications:
        wrfv4:
          workloads:
            CONUS_12km:
              experiments:
                scaling_{n_nodes}:
                  variables:
                    n_nodes: [1, 2, 4]
      spack:
        concretized: true
        packages:
          gcc9:
            spack_spec: gcc@9.3.0
          intel-mpi:
            spack_spec: intel-mpi@2018.4.274
            compiler: gcc9
          wrfv4:
            spack_spec: wrf@4.2 build_type=dm+sm compile_type=em_real nesting=basic ~chem
              ~pnetcdf
            compiler: gcc9
        environments:
          wrfv4:
            packages:
            - intel-mpi
            - wrfv4

The above configuration will execute 3 experiments, comprising a basic scaling
study on three different sets of nodes. This is primarily defined by the use of
vector experiments, which are documented at :ref:`ramble-vector-logic`. Vector
experiments were also introduced in :ref:`vector_and_matrix_tutorial`.

Experiment Internals
--------------------

In Ramble, the concept of ``internals`` allows a user to override some aspects
of a workload within the workspace configuration file. More information about
``internals`` can be seen at :ref:`workspace_internals`.

The ``internals`` block within a workspace configuration file can be used to
define custom executables, and control the order of executables within an
experiment.

In this tutorial, you will define new executables for tracking the start and
end timestamp of each experiment, and properly inject these into the experiment
order.

Define New Executables
~~~~~~~~~~~~~~~~~~~~~~

The definition of a new executable lives within an ``internals`` block. Below
is an example of defining a new executable called ``start_time`` which time in
seconds since 1970-01-01 00:00 UTC:

.. code-block:: YAML

    internals:
      custom_executables:
        start_time:
          template:
          - 'date +%s'
          use_mpi: false
          redirect: '{experiment_run_dir}/start_time'

Within this ``start_time`` definition, the ``template`` attribute takes a list
of strings which will be injected as part of this executable. The ``use_mpi``
attribute tells Ramble if this executable apply the ``mpi_command`` variable
definition as a prefix to every entry of the ``template`` attribute. The
``redirect`` attribute defines the file each portion of ``template`` should be
redirected into.

Not shown above is the ``output_capture`` attribute, which defines the operator
used for capturing the output from the portions of ``template`` (the default is
``&>``).

By default, this would define the actual command to be:

.. code-block:: console

    date +%s &> {experiment_run_dir}/start_time


Edit your workspace configuration file using:

.. code-block:: console

    $ ramble workspace edit

Within this file, use the example above to define two new executables
``start_time`` and ``end_time``. Make sure you change the value of ``redirect``
in the ``end_time`` executable definition. The resulting file should look like
the following:

.. code-block:: YAML

    ramble:
      variables:
        processes_per_node: 4
        n_ranks: '{processes_per_node}*{n_nodes}'
        batch_submit: '{execute_experiment}'
        mpi_command: mpirun -n {n_ranks}
      applications:
        wrfv4:
          workloads:
            CONUS_12km:
              experiments:
                scaling_{n_nodes}:
                  internals:
                    custom_executables:
                      start_time:
                        template:
                        - 'date +%s'
                        redirect: '{experiment_run_dir}/start_time'
                        use_mpi: false
                      end_time:
                        template:
                        - 'date +%s'
                        redirect: '{experiment_run_dir}/end_time'
                        use_mpi: false
                  variables:
                    n_nodes: [1, 2, 4]
      spack:
        concretized: true
        packages:
          gcc9:
            spack_spec: gcc@9.3.0
          intel-mpi:
            spack_spec: intel-mpi@2018.4.274
            compiler: gcc9
          wrfv4:
            spack_spec: wrf@4.2 build_type=dm+sm compile_type=em_real nesting=basic ~chem
              ~pnetcdf
            compiler: gcc9
        environments:
          wrfv4:
            packages:
            - intel-mpi
            - wrfv4

Defining Executable Order
~~~~~~~~~~~~~~~~~~~~~~~~~

At this point, ``start_time`` and ``end_time`` are defined as new executables,
however they are not added to your experiments. To verify this, execute:

.. code-block:: console

    $ ramble workspace setup --dry-run

and examine the ``execute_experiment`` scripts in your experiment directories.
``date +%s`` should not be present in any of these. To fix this issue, we need
to modify the order of the executables for the workload your experiments are
using.

Currently, when controlling the order of executables, the entire order of
executables must be defined. To see the current list of executables for your
experiments, execute:

.. code-block:: console

    $ ramble info wrfv4


And examine the section under the ``Workload: CONUS_12km`` header. The
``Executables:`` definition lists the order of executables used for this
workload. As an example, you might see the following:

.. code-block:: console

    Executables: ['builtin::env_vars', 'builtin::spack_source', 'builtin::spack_activate', 'cleanup', 'copy', 'fix_12km', 'execute']

Now, edit the workspace configuration file with:

.. code-block:: console

    $ ramble workspace edit

And define the order of the executables for your experiments to include
``start_time`` and ``end_time`` in the correct locations. To do this, add a
``executables`` attribute to the ``internals`` dictionary. The contents of
``executables`` are a list of executable names provided in the order you
want them to be executed.

For the purposes of this tutorial, add ``start_time`` directly before
``execute`` and ``end_time`` directly after ``exectute``. The resulting
configuration file should look like the following:

.. code-block:: YAML

    ramble:
      variables:
        processes_per_node: 4
        n_ranks: '{processes_per_node}*{n_nodes}'
        batch_submit: '{execute_experiment}'
        mpi_command: mpirun -n {n_ranks}
      applications:
        wrfv4:
          workloads:
            CONUS_12km:
              experiments:
                scaling_{n_nodes}:
                  internals:
                    custom_executables:
                      start_time:
                        template:
                        - 'date +%s'
                        redirect: '{experiment_run_dir}/start_time'
                        use_mpi: false
                      end_time:
                        template:
                        - 'date +%s'
                        redirect: '{experiment_run_dir}/end_time'
                        use_mpi: false
                    executables:
                    - builtin::env_vars
                    - builtin::spack_source
                    - builtin::spack_activate
                    - cleanup
                    - copy
                    - fix_12km
                    - start_time
                    - execute
                    - end_time
                  variables:
                    n_nodes: [1, 2, 4]
      spack:
        concretized: true
        packages:
          gcc9:
            spack_spec: gcc@9.3.0
          intel-mpi:
            spack_spec: intel-mpi@2018.4.274
            compiler: gcc9
          wrfv4:
            spack_spec: wrf@4.2 build_type=dm+sm compile_type=em_real nesting=basic ~chem
              ~pnetcdf
            compiler: gcc9
        environments:
          wrfv4:
            packages:
            - intel-mpi
            - wrfv4

**NOTE** Omitting any executables from the ``executables`` list will
prevent it from being used in the generated experiments.

Execute Experiments
-------------------

Now that you have made the appropriate modifications, set up, execute, and
analyze the new experiments using:

.. code-block:: console

    $ ramble workspace setup
    $ ramble on
    $ ramble workspace analyze

This creates a ``results`` file in the root of the workspace that contains
extracted figures of merit. If the experiments were successful, this file will
show the following results:

* Average Timestep Time: Time (in seconds) on average each timestep takes
* Cumulative Timestep Time: Time (in seconds) spent executing all timesteps
* Minimum Timestep Time: Minimum time (in seconds) spent on any one timestep
* Maximum Timestep Time: Maximum time (in seconds) spent on any one timestep
* Number of timesteps: Count of total timesteps performed
* Avg. Max Ratio Time: Ratio of Average Timestep Time and Maximum Timestep Time

Examining the experiment run directories, you should see ``start_time`` and
``end_time`` files which contain the output of our custom executables.

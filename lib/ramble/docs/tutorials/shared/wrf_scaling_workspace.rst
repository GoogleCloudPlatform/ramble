.. Copyright 2022-2024 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

Configure Experiment Definitions
--------------------------------

To being with, you need to configure the workspace. The workspace's root
location can be seen under the ``Location`` output of:

.. code-block:: console

    $ ramble workspace info

Alternatively, the files can be edited directly with:

.. code-block:: console

    $ ramble workspace edit

Within the ``ramble.yaml`` file, write the following contents, which is the
final configuration from a previous tutorial.

.. code-block:: YAML

    ramble:
      env_vars:
        set:
          OMP_NUM_THREADS: '{n_threads}'
      variables:
        processes_per_node: 16
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
                    n_nodes: [1, 2]
      software:
        packages:
          gcc9:
            pkg_spec: gcc@9.4.0
          intel-mpi:
            pkg_spec: intel-oneapi-mpi@2021.11.0
            compiler: gcc9
          wrfv4:
            pkg_spec: wrf@4.2 build_type=dm+sm compile_type=em_real nesting=basic ~chem
              ~pnetcdf
            compiler: gcc9
        environments:
          wrfv4:
            packages:
            - intel-mpi
            - wrfv4

The above configuration will execute 2 experiments, comprising a basic scaling
study on 2 different sets of nodes. This is primarily defined by the use of
vector experiments, which are documented in the :ref:`vector
logic<ramble-vector-logic>` portion of the workspace configuration file
documentation. Vector experiments were also introduced in the :ref:`vector and
matrix tutorial <vector_and_matrix_tutorial>`.


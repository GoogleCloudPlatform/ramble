.. Copyright 2022-2023 Google LLC

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

Additionally, the files can be edited directly with:

.. code-block:: console

    $ ramble workspace edit

Within the ``ramble.yaml`` file, write the following contents, which the
final configuration from a previous tutorial.

.. code-block:: YAML

    ramble:
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

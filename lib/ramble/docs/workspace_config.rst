.. Copyright 2022-2023 Google LLC

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

============================
Workspace Configuration File
============================

Ramble workspaces are controlled through their configuration files. Each
workspace has a configuration file stored at ``$workspace/configs/ramble.yaml``.

This document will describe the syntax for writing a workspace configuration file.

Within the ``ramble.yaml`` file, there are two top level dictionairies.

.. code-block:: console

   ramble:
     ...
   spack:
     ...

Each of these dictionaires is used to control different aspects of the Ramble
workspace.

------------------
Ramble Dictionary:
------------------

The ramble dictionary is used to control the experiments a workspace is
responsible for configuring, executing, analyzing, and archiving.

.. code-block:: yaml

    ramble:
      mpi:
        command: mpirun
        args:
        - '-n'
        - '{n_ranks}'
      batch:
        submit: '{execute_experiment}'
      applications:
        hostname:
          workloads:
            serial:
              experiments:
                test_exp:
                  variables:
                    n_ranks: '1'
                    n_nodes: '1'

Within a ramble configuration file, configuration scopes for an experiment
include, ``application``, ``workload``, and ``experiment``. They are denoted by
these words in the configuration file. The name ``hostname`` name of the ramble
application (as seen by ``ramble list``), while the name ``serial`` is the name of the
workload (as seen by ``ramble info hostname``).

The name ``test_exp`` is user defined, and will be explained in :ref:`experiment-names`.

The name ``variables`` defines arbitrary variables, and will be explained in
:ref:`variable-dictionaries`.

.. _experiment-names:

^^^^^^^^^^^^^^^^^
Experiment Names:
^^^^^^^^^^^^^^^^^

While the names of applications and workloads are defined by the application
definition file, experiment names are more arbitrary. Experiment names are
string, and can take variables for expansion.

.. code-block:: yaml

    ramble:
      applications:
        hostname:
          workloads:
            serial:
              experiments:
                test_{n_ranks}_{n_nodes}:
                  variables:
                    n_ranks: '1'
                    n_nodes: '1'

In the above example, the experiment name would be: ``test_1_1`` when it is created.

**NOTE:** Each experiment has a namespace that follows this pattern:
``application.workload.experiment``. Every experiment needs a unique namespace,
or ramble will throw an error.

.. _variable-dictionaries:

^^^^^^^^^^^^^^^^^^^^^^
Variable Dictionaries:
^^^^^^^^^^^^^^^^^^^^^^

Within a variable dictionary, arbitrary variables can be defined. Defined
variables apply to all experiments within their scope.

These variables can be referred to within the YAML file, or template files
using python keyword ( ``{var_name}`` ) syntax to perform variable expansion.
This syntax allows basic math operations ( ``+``, ``-``, ``/``, ``*``, and
``**`` ) to evaluate math expressions using variable definitions.

If a variable is defined within multiple dictionaries, values defined closer to
individual experiments take precendence.

.. code-block:: yaml

    ramble:
      ...
      variables:
        processes_per_node: '16'
        n_ranks: '{n_nodes}*{processes_per_node}'
      applications:
        hostname:
          variables:
            n_threads: '1'
          workloads:
            serial:
              variables:
                n_nodes: '1'
              experiments:
                test_exp:
                  variables:
                    n_ranks: '1'

In this example, ``n_ranks`` will take a value of ``1`` within the ``test_exp``
experiment. This experiment will also include definitions for
``processes_per_node``, ``n_nodes``, and ``n_threads``.


^^^^^^^^^^^^^^
List Variables:
^^^^^^^^^^^^^^
Variables can be defined as a list of values as well (again, following the same
math and variable expansion syntax as defined above).

.. code-block:: yaml

    ramble:
      ...
      variables:
        processes_per_node: '16'
        n_ranks: '{n_nodes}*{processes_per_node}'
      applications:
        hostname:
          variables:
            n_threads: '1'
          workloads:
            serial:
              variables:
                n_nodes: ['1', '2', '3', '4']
              experiments:
                test_exp_{n_nodes}:
                  variables:
                    n_ranks: '1'

There are two noteable aspects of this config file are:
1. ``n_nodes`` is a list of values
2. The experiment name refernces variable values.

All lists defined within any experiment namespace are required to be the same
length. They are zipped together, and iterated over to generate unique experiments.

^^^^^^^^^^^^^^^^^^
Variable Matrices:
^^^^^^^^^^^^^^^^^^

In addition to allowing variables, Ramble's config file has a special syntax for define variable matrices.

Matrices consume list variables, and generate a matrix of variables with it.
Each independent matrix performs the cross product of any list variables it
consumes.

.. code-block:: yaml

    ramble:
      ...
      variables:
        n_ranks: '{n_nodes}*{processes_per_node}'
      applications:
        hostname:
          variables:
            n_threads: '1'
          workloads:
            serial:
              variables:
                processes_per_node: ['16', '32']
                n_nodes: ['1', '2', '3', '4']
              experiments:
                test_exp_{n_nodes}_{processes_per_node}:
                  variables:
                    n_ranks: '1'
                  matrix:
                  - processes_per_node

In the above example, the ``processes_per_node`` variable is consumed as part
of a matrix. The result is a matrix of shape 1x2. After this matrix is
consumed, it will be crossed with the zipped vectors (creating 8 unique experiments).

Mulitple matrices are allowed to be defined:

.. code-block:: yaml
   :linenos:

    ramble:
      ...
      variables:
        n_ranks: '{n_nodes}*{processes_per_node}'
      applications:
        hostname:
          variables:
            n_threads: '1'
          workloads:
            serial:
              variables:
                processes_per_node: ['16', '32']
                partition: ['part1', 'part2']
                n_nodes: ['1', '2', '3', '4']
              experiments:
                test_exp_{n_nodes}_{processes_per_node}:
                  variables:
                    n_ranks: '1'
                  matrices:
                  - - processes_per_node
                    - partition
                  - - n_nodes

The result of this is that two matrices are created. The first is a 2x2 matrix,
while the second is a 1x4 matrix. All matrices are required to have the same
number of elements, as they are flattened and zipped together. In this case,
there would be 4 experiments, each defined by a unique
``(processes_per_node, partition, n_nodes)`` tuple.

^^^^^^^^^^^^^^^^^^^
Reserved Variables:
^^^^^^^^^^^^^^^^^^^

There are several reserved, auto-generated, and required variables for Ramble
to function properly. This section will describe them.

"""""""""""""""""""
Required Variables:
"""""""""""""""""""

Ramble requires the following variables to be define:

* ``n_ranks`` - Defines the number of MPI ranks to use. If not explicitly set,
  is defined as: ``{processes_per_node}*{n_nodes}``
* ``n_nodes`` - Defines the number of machines needed for the experiment. If
  not explicitly set, is defined as:
  ``ceiling({n_ranks}/{processes_per_node})``
* ``processes_per_node`` - Defines how many ranks should be on each node. If
  not explicitly set, is defined as: ``ceiling({n_ranks}/{n_nodes})``

""""""""""""""""""""
Generated Variables:
""""""""""""""""""""

Ramble automatically generates definitions for the following varialbes:

* ``application_name`` - Set to the name of the application
* ``workload_name`` - Set to the name of the workload within the application
* ``experiment_name`` - Set to the name of the experiment
* ``spec_name`` - By default defined as ``{application_name}``. Can be
  overriden to control the spack definition to use.
* ``application_run_dir`` - Absolute path to
  ``$workspace_root/experiments/{application_name}``
* ``workload_run_dir`` - Absolute path to
  ``$workspace_root/experiments/{application_name}/{workload_name}``
* ``experiment_run_dir`` - Absolute path to
  ``$workspace_root/experiments/{application_name}/{workload_name}/{experiment_name}``
* ``application_input_dir`` - Absolute path to
  ``$workspace_root/inputs/{application_name}``
* ``workload_input_dir`` - Absolute path to
  ``$workspace_root/inputs/{application_name}/{workload_name}``
* ``spack_env`` - Absolute path to
  ``$workspace_root/software/{spec_name}.{workload_name}``
* ``log_dir`` - Absolute path to ``$workspace_root/logs``
* ``log_file`` - Absolute path to
  ``{experiment_run_dir}/{experiment_name}.out``
* ``<input_name>`` - Applications that have input files have variables defined
  that contain the absolute path to:
  ``$workspace_root/inputs/{application_name}/{workload_name}/<input_name>``
  where ``<input_name>`` is the name as defined in the ``input_file``
  directive.
* ``<template_name>`` - Any files with the ``.tpl`` extension in
  ``$workspace_root/configs`` have a variable generated that resolves to the
  absolute path to: ``{experiment_run_dir}/<template_name>`` where
  ``<template_name>`` is the filename of the template, without the extension.
* ``command`` - Set to all of the commands needed to perform an experiment.
* ``spack_setup`` - Set to the commands needed to load a spack environment for
  an experiment. Set to an empty string for non-spack applications

"""""""""""""""""""""""""""""""""""
Spack Specific Generated Variables:
"""""""""""""""""""""""""""""""""""
When using spack applications, Ramble also geneates the following variables:

* ``<software_spec_name>`` - Set to the equivalent of ``spack location -i
  <spec>`` for packages defined in a ramble ``spec_name`` package set.
  ``<software_spec_name>`` is set to the name of the package (one level lower
  than ramble's ``spec_name``).

"""""""""""""""""""
Reserved Variables:
"""""""""""""""""""

Ramble's internals use the following definitions. Overriding them within a
config file can negatively impact the functionality of ramble.

* ``mpi_command``
* ``batch_submit``

-----------------
Spack Dictionary:
-----------------

Within a ramble.yaml file, the ``spack:`` dictionary controlls the software
stack installation that ramble performs.

Below is an annotated example of the spack dictionary.

.. code-block:: yaml

    spack:
      compilers:
        gcc9: # Abstract name to refer to this compiler
          base: gcc # Spack packge name
          version: 9.3.0 # Spack package version
          target: x86_64 # Spack target option
      mpi_libraries:
        impi2018: # Abstract name to refer to this MPI
          base: intel-mpi
          version: 2018.4.274
          target: x86_64
      applications:
        gromacs: # Ramble's spec_name variable
          gromacs: # application.py named software_spec, name of Ramble spec object
            base: gromacs # Spack package name
            version: 2022.4 # Spack package version
            compiler: gcc9 # Ramble compiler name
            mpi: impi2018 # Ramble MPI name

Application definition files can define one or more ``software_spec``
directives, which are packages the application might need to run properly. Some
are marked as required, and others might not be.

Multiple compilers and MPI libraries can be defined, even if they are not used.

^^^^^^^^^^^^^^^^^^^
Ramble Spec Format:
^^^^^^^^^^^^^^^^^^^

When writing Spack spec information in Ramble configuration files, the format
is as follows:

.. code-block:: yaml

   <software_spec:name>:
     base: # Takes the Spack package name
     version: # Takes the version, which would be passed in with @
     compiler: # Takes the name of the ramble spec object to use
               # to compile this package

     variants: # Takes any variant strings the package should be built with
     mpi: # Takes the name of the Ramble spec object to use for an MPI dependency
     arch: # Takes the input to the Spack `arch` option
     target: # Takes the input to the Spack `target` option
     dependencies: # YAML List containing Ramble spec object names this
                   # package depends on

Not all of the options are required, but generally a spec object should contain
at least ``base``, and ``version``.

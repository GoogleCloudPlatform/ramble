.. Copyright 2022-2025 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _workspace-config:

============================
Workspace Configuration File
============================

Ramble workspaces are controlled through their configuration files. Each
workspace has a configuration file stored at ``$workspace/configs/ramble.yaml``.

This document will describe the syntax for writing a workspace configuration file.

Within the ``ramble.yaml`` file, all content lives under the top level ``ramble`` dictionary:

.. code-block:: console

   ramble:
     ...

This dictionary is used to control all of the aspects of the Ramble workspace.

-----------------
Ramble Dictionary
-----------------

The ramble dictionary is used to control the experiments a workspace is
responsible for configuring, executing, analyzing, and archiving.

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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

^^^^^^^^^^^^^^^^
Experiment Names
^^^^^^^^^^^^^^^^

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
                    mpi_command: 'mpirun -n {n_ranks}'
                    batch_submit: '{execute_experiment}'
                    n_ranks: '1'
                    n_nodes: '1'

In the above example, the experiment name would be: ``test_1_1`` when it is created.

**NOTE:** Each experiment has a namespace that follows this pattern:
``application.workload.experiment``. Every experiment needs a unique namespace,
or ramble will throw an error.

.. _variable-dictionaries:

^^^^^^^^^^^^^^^^^^^^^
Variable Dictionaries
^^^^^^^^^^^^^^^^^^^^^

Within a variable dictionary, arbitrary variables can be defined. Defined
variables apply to all experiments within their scope.

These variables can be referred to within the YAML file, or template files
using python keyword ( ``{var_name}`` ) syntax to perform variable expansion.

If a variable is defined within multiple dictionaries, values defined closer to
individual experiments take precedence.

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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


.. _ramble-supported-functions:

~~~~~~~~~~~~~~~~~~~
Supported Functions
~~~~~~~~~~~~~~~~~~~

Ramble's variable expansion logic supports several mathematical operators and
functions to help construct useful variable definitions.

Supported math operators are:

* ``+`` (addition)
* ``-`` (subtraction)
* ``*`` (multiplication)
* ``/`` (division)
* ``//`` (floor division)
* ``**`` (exponent)
* ``^`` (bitwise exclusive or)
* ``-`` (unary subtraction)
* ``==`` (equal)
* ``!=`` (not equal)
* ``>`` (greater than)
* ``>=`` (greator or equal than)
* ``<`` (less than)
* ``<=`` (less or equal than)
* ``and`` (logical and)
* ``or`` (logical or)
* ``%`` (modulo)

Supported functions are:

* ``str()`` (explicit string cast)
* ``int()`` (explicit integer cast)
* ``float()`` (explicit float cast)
* ``min()`` (minimum)
* ``max()`` (maximum)
* ``ceil()`` (ceiling of input)
* ``floor()`` (floor of input)
* ``range()`` (construct range, see :ref:`ramble vector logic<ramble-vector-logic>` for more information)
* ``simplify_str()`` (convert input string to only alphanumerical characters and dashes)
* ``randrange`` (from `random.randrange`)
* ``randint`` (from `random.randint`)
* ``re_search(regex, str)`` (determine if ``str`` contains pattern ``regex``, based on ``re.search``)

String slicing is supported:

* ``str[start:end:step]`` (string slicing)

Dictionary references are supported:

* ``dict_name["key"]`` (dictionary subscript)

.. _ramble-escaped-variables:

~~~~~~~~~~~~~~~~~
Escaped Variables
~~~~~~~~~~~~~~~~~

When referring to variables in Ramble, sometimes it is useful to be able to
escape curly braces to prevent the expander from fully expanding the variable
reference. Curly braces that are prefixed with a back slash (i.e. ``\{`` or
``\}``) will be replaced with an unexpanded curly brace by Ramble's expander.

Each time the variable is expanded, the escaped curly braces will be replaced
with unescaped curly braces (i.e. ``\{`` will expand to ``{``). Additional back
slashes can be added to prevent multiple expansions (i.e. ``\\{`` will expand
to ``\{``).

.. _ramble-vector-logic:

^^^^^^^^^^^^^^^^^^^^^^^^^^
List (or Vector) Variables
^^^^^^^^^^^^^^^^^^^^^^^^^^
Variables can be defined as a list of values as well (again, following the same
math and variable expansion syntax as defined above).

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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

There are two notable aspects of this config file are:
1. ``n_nodes`` is a list of values
2. The experiment name references variable values.

All lists defined within any experiment namespace are required to be the same
length. They are zipped together, and iterated over to generate unique experiments.

In addition to accepting explicit lists, Ramble supports using
`Python's range() function <https://docs.python.org/3/library/functions.html#func-range>`_
to create a list. With this functionality, the example above could be re-written as:

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
        processes_per_node: '16'
        n_ranks: '{n_nodes}*{processes_per_node}'
      applications:
        hostname:
          variables:
            n_threads: '1'
          workloads:
            serial:
              variables:
                n_nodes: 'range(1, 5)'
              experiments:
                test_exp_{n_nodes}:
                  variables:
                    n_ranks: '1'


.. _ramble-matrix-logic:

^^^^^^^^^^^^^^^^^
Variable Matrices
^^^^^^^^^^^^^^^^^

In addition to allowing variables, Ramble's config file has a special syntax for define variable matrices.

Matrices consume list variables, and generate a matrix of variables with it.
Each independent matrix performs the cross product of any list variables it
consumes.

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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

Multiple matrices are allowed to be defined:

.. code-block:: yaml
   :linenos:

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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


.. _ramble-explicit-zips:


^^^^^^^^^^^^^^^^^^^^^^
Explicit Variable Zips
^^^^^^^^^^^^^^^^^^^^^^

A common pattern in python for iterating over multiple lists in lock-step is to
use something called a zip. For more information on how this behaves in
practice, see
`Python's zip documentation <https://docs.python.org/3.3/library/functions.html#zip>`_.

Ramble's workspace config contains syntax for defining explicit variable zips.
These zips are named grouping of variables that are related and should be
iterated over together when generating experiments.

Zips consume list variables and generate a named grouping, which can be
consumed by matrices just as list variables would be.

Below is an example showing how to define explicit zips:

.. code-block:: yaml
   :linenos:

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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
                  zips:
                    partition_defs:
                    - partition
                    - processes_per_node
                  matrix:
                  - partition_defs
                  - n_nodes


Which would result in eight experiments, crossing the ``n_nodes`` variable with
the zip of ``partition`` and ``processes_per_node``.

.. _ramble-experiment-variants:


^^^^^^^^^^^^^^^
Variant Control
^^^^^^^^^^^^^^^

Within a workspace configuration file, experiments are able to define variants.
Variants are able to manipulate specific aspects of experiments and
applications. More information on these configuration options can be seen in
the :ref:`Variants Configuration Section<variants-config>` documentation. To
begin with, the only variant that can be specific is the ``package_manager``.

The ``package_manager`` variant is used to define which package manager is used
to configure and execute the experiments. To select ``spack`` as the package
manager, the following block can be added to any scope that variables can be
defined in.

.. code-block:: yaml

  variants:
    package_manager: spack

For more information about controlling package managers see the
:ref:`package manager documentation <package-manager-control>`.


.. _ramble-experiment-exclusion:

^^^^^^^^^^^^^^^^^^^^
Experiment Exclusion
^^^^^^^^^^^^^^^^^^^^

When writing a workspace configuration file, experiments can be explicitly
excluded from the generated set using an ``exclude`` block inside the
experiment definition. This block contains definitions of ``variables``,
``matrices``, ``zips``, and optional mathematical ``where`` statements to
define which experiments should be excluded from the generation process.

.. code-block:: yaml
   :linenos:

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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
                  zips:
                    partition_defs:
                    - partition
                    - processes_per_node
                  matrices:
                  - - partition_defs
                    - n_nodes
                  exclude:
                    variables:
                      n_nodes: ['2', '3']
                    matrix:
                    - partition_defs
                    - n_nodes

In the example above, of the eight experiments that would be generated from the
experiment definition, four will be excluded. In the defined ``exclude`` block
experiments with ``n_nodes = 2`` or ``n_nodes = 3`` will be excluded from the
generation process.

This logic can be replicated in a ``where`` statement as well:

.. code-block:: yaml
   :linenos:

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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
                  zips:
                    partition_defs:
                    - partition
                    - processes_per_node
                  matrices:
                  - - partition_defs
                    - n_nodes
                  exclude:
                    where:
                    - '{n_nodes} == 2'
                    - '{n_nodes} == 3'

``where`` statements can contain mathematical operations, but must result in a
boolean value. If any of the ``where`` statements evalaute to ``True`` within
an experiment, that experiment will be excluded from generation. To be more
explicit, all ``where`` statements are joined together with ``or`` operators.
Within any single ``where`` statement, operators can be joined together with
``and`` and ``or`` operators as well.

.. _ramble-experiment-repeats:

^^^^^^^^^^^^^^^^^^
Experiment Repeats
^^^^^^^^^^^^^^^^^^

Ramble provides a simple mechanism to repeat the same experiment a specified number of
times, and calculates summary statistics for the set of repeated experiments. To enable
repeats, an ``n_repeats`` block can be added at the application, workload, or experiment
level.

.. code-block:: yaml

    ramble:
      config:
        n_repeats: int
        repeats_success_strict: [True/False]
      applications:
        hostname:
          n_repeats: int
          workloads:
            serial:
              n_repeats: int
              experiments:
                test_experiment:
                  n_repeats: int

More information on setting repeats at the config level can be found in the
:ref:`configuration files<experiment-repeats-config-option>` documentation.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Environment Variable Control
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Environment variables can be controlled using an
:ref:`env_var config section<env-vars-config>`,
defined at the appropriate level of the workspace config.

As a concrete example:

.. code-block:: yaml

    env_vars:
      set:
        SET_VAR: set_val
      append:
      - var-separator: ','
        vars:
          APPEND_VAR: app_val
        paths:
          PATH: app_path
      prepend:
      - paths:
          PATH: prepend_path
      unset:
      - LD_LIBRARY_PATH

Would result in roughly the following bash commands:

.. code-block:: console

    export SET_VAR=set_val
    export APPEND_VAR=$APPEND_VAR,app_val
    export PATH=prepend_path:$PATH:app_path
    unset LD_LIBRARY_PATH

^^^^^^^^^^^^^^^^^^^^^
Templatized Workloads
^^^^^^^^^^^^^^^^^^^^^

As previously shown, variables can be defined using lists or matrices. In addition to
controlling several aspects of experiments, list and matrix variables can be used to
replicate an experiment across workloads.

.. code-block:: yaml

    ramble:
      applications:
        hostname:
          variables:
            application_workloads: ['parallel', 'serial', 'local']
          workloads:
            '{application_workloads}':
              experiments:
                test_exp:
                  variables:
                    n_ranks: '1'

In the above example, we use the ``application_workloads`` variable to define
the names of the workloads we'd like to generate experiments for. Any variable
can be used to define the name of the workloads, except those reserved by
Ramble. These can be seen in the :ref:`ramble-reserved-variables` section.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Cross Experiment Variable References
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Variables can be defined to pull the value of a variable out of a different
experiment. This is particularly useful when an experiment needs the path to
something ramble automatically generates in a different experiment.

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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
                test_exp1:
                  variables:
                    n_ranks: '1'
                    real_value: 'exp1_value'
                test_exp2:
                  variables:
                    n_ranks: '1'
                    test_value: real_value in hostname.serial.test_exp1

In the above example, ``test_value`` extracts the value of ``real_value`` as
defined in the experiment ``hostname.serial.test_exp1``. When evaluated, this
will set ``test_value`` to ``'exp1_value'``.

^^^^^^^^^^^^^^^^^^^^
Experiment Modifiers
^^^^^^^^^^^^^^^^^^^^

In addition to containing application definitions, Ramble also provides
experiment modifiers. Experiment modifiers encapsulate several aspects of a
standard modification to an experiment, such as prepending a binary with a tool
or profiler, and can be applied to experiments to modify their behavior.

Available experiment modifiers can be seen using ``ramble mods list``, and more
information about a particular modifier can be see with
``ramble mods info <mod_name>``.

Modifiers can be applied to experiments using the following YAML syntax:

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
        processes_per_node: '16'
      applications:
        gromacs:
          workloads:
            water_bare:
              experiments:
                test_exp1:
                  modifiers:
                  - name: intel-aps
                    mode: mpi
                    on_executable:
                    - '*'
                  variables:
                    n_ranks: '1'


Modifiers can be defined at any level variables can be defined at (and are even
their own config section).

When defining a modifier, the ``name`` attribute is the name of the modifier
that will be applied. The ``mode`` attribute is a modifier specific setting
allowing the user to select the modifier behavior. Modes can be seen by looking
at the modifier information, and represent modes of use for the modifier. Modes
group several general aspects of a modifier into one usage mode, and can allow
a general modifier to present many operational entry points. The
``on_executable`` attribute is a list of experiment executables that the
modifier should be applied to. These executable names are matched using
python's ``fnmatch.fnmatch`` functionality.

If it is not set, modifiers will attempt to determine their own ``mode``
attribute. This will succeed if the modifier has a single mode of operation. If
there are multiple modes, this will raise an exception.

Every modifier has a ``disabled`` mode that is defined by default. This mode
will never be automatically enabled, but it will allow experiments to turn off
the modifier without having to remove the modifier from the experiment
definitions.

If the ``on_executable`` attribute is not set, it will default to ``'*'`` which
will match all executables. Modifier classes can (and should) be implemented to
only act on the correct executable types (i.e. executables with ``use_mpi=true``).

.. _experiment_tags:

^^^^^^^^^^^^^^^
Experiment Tags
^^^^^^^^^^^^^^^

While applications and workloads can be tagged within an application definition
file (using the ``tags()`` or ``workload()`` directives), workloads and
experiments can also be tagged within a workspace configuration file. This
allows users to define their own tags to communicate what an experiment and
workload might be used for beyond the information captured in the application
definition file.

The below example shows how tags can be defined within a workspace:

.. code-block:: yaml

  ramble:
    variables:
      mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
        processes_per_node: '16'
      applications:
        gromacs:
          workloads:
            water_bare:
              tags:
              - wltag
              experiments:
                test_exp1:
                  tags:
                  - tag1
                  variables:
                    n_ranks: '1' 
                test_exp2:
                  tags:
                  - tag2
                  variables:
                    n_ranks: '1' 


In the above example, all experiments are tagged with the ``wltag`` tag. Only
the ``test_exp1`` experiment is tagged with the ``tag1`` tag, while the
``test_exp2`` experiment is tagged with the ``tag2`` tag.

These tags are propagated into a workspace's results file, and can be used to
filter pipeline commands, as show in the
:ref:`filtering experiments documentation <filter-experiments>`.

.. _workspace_including_external_files:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Including External Configuration Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ramble workspace configuration files support referring to external
configuration files. This allows a workspace to be composed of external files
and directories.

.. code-block::
   YAML

  ramble:
    include:
    - /absolute/path/to/applications.yaml
    - $workspace_root/directory/in/workspace/

Supported path variables include:

 * ``$workspace_root`` - Root directory of workspace
 * ``$workspace`` - Root directory of workspace
 * ``$workspace_configs`` - Configs directory in workspace
 * ``$workspace_software`` - Software directory in workspace
 * ``$workspace_logs`` - Logs directory in workspace
 * ``$workspace_inputs`` - Experiments directory in workspace
 * ``$workspace_shared`` - Shared directory in workspace
 * ``$workspace_archives`` - Archives directory in workspace
 * ``$workspace_deployments`` - Deployments directory in workspace

For more information, see the relevant portion of Spack's documentation on
`including configurations <https://spack.readthedocs.io/en/latest/environments.html#included-configurations>`_.

.. _workspace_internals:

^^^^^^^^^^^^^^^^^^^^^
Controlling Internals
^^^^^^^^^^^^^^^^^^^^^

Within a workspace config, an internals dictionary can be used to control
several internal aspects of the application, workload, and experiment.

This config section is defined in the
:ref:`internals config section<internals-config>`.

Below are examples of using this within a workspace config file.

""""""""""""""""""
Custom Executables
""""""""""""""""""

Custom executables can be created within the internals dictionary. Below is an
example, showing how to create a ``lscpu`` executable at the application level.

.. code-block:: yaml

    ramble:
      applications:
        hostname:
          internals:
            custom_executables:
              lscpu:
                template:
                - 'lscpu'
                use_mpi: false
                redirect: '{log_file}'
         ...

The above example creates a custom executable, named ``lscpu`` that will inject
the command ``lscpu`` into the command for an experiment when it is used. It is
important to note that this only creates the executable, and does not use it.

""""""""""""""""""""""""""""
Controlling Executable Order
""""""""""""""""""""""""""""

The internals dictionary allows the ability to control the order pre-defined
executables (or custom executables) are pieced together to build an experiment.

.. code-block:: yaml

   ramble:
     applications:
       hostname:
         internals:
           custom_executables:
             lscpu:
               template:
               - 'lscpu'
               use_mpi: false
               redirect: '{log_file}'
           executables:
           - serial
           - builtin::env_vars
           - lscpu

The above example builds off of the custom executable example, and shows how
one can control the order of the executables in the formatted executable expansions.

The default for the hostname application is ``[builtin::env_vars,
serial/parallel]`` but this changes the order and injects ``lscpu`` into the
expansion.


""""""""""""""""""""""""""
Using Executable Injection
""""""""""""""""""""""""""

Executable order can also be controlled via the ``executable_injection`` block
within the ``internals`` block. Injecting the ``lscpu`` executable to the end of
the list of executables can be performed with the following:

.. code-block:: yaml

   ramble:
     applications:
       hostname:
         internals:
           custom_executables:
             lscpu:
               template:
               - 'lscpu'
               use_mpi: false
               redirect: '{log_file}'
           executable_injection:
           - name: lscpu

This is a generic way to add the ``lscpu`` custom executable to the end of the
list of executables for the experiment. For more information on this see the
:ref:`internals config section<internals-config>` documentation.

"""""""""""""""""""""""""""""""
Overriding Variable Definitions
"""""""""""""""""""""""""""""""

When defining custom executables, sometimes it's useful to be able to override
specific variable definitions for only this executable definition. As an
example, consider running a command to get information from every node in a job
allocation. While the actual experiment might be utilizing many processes on
each compute node, the custom executable only wants to run a single process on
each compute node. Ramble provides the ability for users to define variables
that are scoped to only the custom executable instead of the entire experiment.
Consider the following example:

.. code-block:: yaml

   ramble:
     applications:
       gromacs:
         internals:
           custom_executables:
             all_hosts:
               template:
               - 'hostname'
               use_mpi: true
               variables:
                 n_ranks: '{n_nodes}'
                 processes_per_node: '1'
               redirect: '{log_file}'

In this example, a custom executable named ``all_hosts`` is defined. Within
this executable, the value of ``n_ranks`` is defined to be the value of
``n_nodes``, and ``processes_per_node`` is defined to be ``1``, causing only
one rank per compute node. This would print the hostname of each node in the
experiment once.

.. _ramble-reserved-variables:

^^^^^^^^^^^^^^^^^^
Reserved Variables
^^^^^^^^^^^^^^^^^^

There are several reserved, auto-generated, and required variables for Ramble
to function properly. This section will describe them.

""""""""""""""""""
Required Variables
""""""""""""""""""

Ramble requires the following variables to be defined:

* ``n_ranks`` - Defines the number of MPI ranks to use. If not explicitly set,
  is defined as: ``{processes_per_node}*{n_nodes}``
* ``n_nodes`` - Defines the number of machines needed for the experiment. If
  not explicitly set, is defined as:
  ``ceiling({n_ranks}/{processes_per_node})``
* ``processes_per_node`` - Defines how many ranks should be on each node. If
  not explicitly set, is defined as: ``ceiling({n_ranks}/{n_nodes})``
* ``mpi_command`` - Template for generating an MPI command
* ``batch_submit`` - Template for generating a batch system submit command

"""""""""""""""""""
Generated Variables
"""""""""""""""""""

Ramble automatically generates definitions for the following variables:

* ``application_name`` - Set to the name of the application
* ``workload_name`` - Set to the name of the workload within the application
* ``experiment_name`` - Set to the name of the experiment
* ``env_name`` - By default defined as ``{application_name}``. Can be
  overridden to control the software environment to use.
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
* ``experiment_index`` - Index, in set, of experiment. If part of a chain,
  shares a value with its root.
* ``env_path`` - Absolute path to
  ``$workspace_root/software/{package_manager_name}/{env_name}.{workload_name}``
  if no package manager is used, ``{package_manager_name}`` is replaced with
  ``no-package-manager``.
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

""""""""""""""""""""""""""""""""""""""""""""
Package Manager Specific Generated Variables
""""""""""""""""""""""""""""""""""""""""""""
Ramble also generates or requires the following variables, depending on the
package manager used:

* ``<software_spec_name>_path`` - Set to the installation location for the package
  for all packages defined in an experiment's environment definition.
  ``<software_spec_name>`` is the name of the package as defined in the
  ``software:packages`` dictionary.

When the package manager is ``spack`` this is the equivalent to the output of
``spack location -i`` for each install spec.

Any applications that have required packages require path variables to be
defined when a package manager is not used.

As an example:

.. code-block:: yaml

    ramble:
      variants:
        package_manager: spack
      software:
        packages:
          grm:
            pkg_spec: gromacs@2023.1
        environments:
          grm_env:
            packages:
            - grm

Defines a software environment named ``grm_env``. The default environment used
has the same name as the application the experiment is generated from. In
experiments which use this ``grm_env`` environment, a variable is defined
named: ``gromacs``, as that is the package named defined by the ``pkg_spec``
attribute of the ``grm`` package definition. This variable contains the path to
the installation location for the ``gromacs`` package.

**NOTE**: Package installation location variables are only generated when
actually performing the setup of a workspace. When a ``--dry-run`` is
performed, these paths are not populated.


-------------------
Software Dictionary
-------------------

Within a ramble.yaml file, the ``software:`` dictionary controls the software
stack installation that ramble performs. This configuration section is defined
in the :ref:`Software section<software-config>` documentation.
a packages dictionary, and an environments dictionary.

The ``ramble workspace concretize`` command can help construct a functional
software dictionary based on the experiments listed.

It is important to note that packages and environments that are not used by an
experiment are not installed.

Application definition files can define one or more ``software_spec``
directives, which are packages the application might need to run properly.
Additionally, packages can be marked as required through the
``required_package`` directive.

-------------------------------------------
Controlling MPI Libraries and Batch Systems
-------------------------------------------

Some workspaces might be configured with the goal of exploring the performance
of different MPI libraries (e.g. MPICH vs. Open MPI), or of performing the same
experiment in multiple batch schedulers (e.g. SLURM, PBS Pro, and Flux).

This section will show how to perform these experiments within a workspace
configuration file.


^^^^^^^^^^^^^^^^^^^
MPI Command Control
^^^^^^^^^^^^^^^^^^^

When writing a ramble configuration file to perform the same experiment with
different MPI libraries, the MPI section within the Ramble dictionary is
insufficient for changing the flags used based on the MPI library used.

However, Ramble's variable definitions can be used to control this on a
per-experiment basis.

Below is an example of running a Gromacs experiment in both MPICH and OpenMPI:

.. code-block:: yaml

    ramble:
      variants:
        package_manager: spack
      variables:
        batch_submit: '{execute_experiment}'
        mpi_command:
        - 'mpirun -n {n_ranks} -ppn {processes_per_node} ' # MPICH
        - 'mpirun -n {n_ranks} -nperhost {processes_per_node} ' # OpenMPI
      applications:
        gromacs:
          workloads:
            water_bare:
              experiments:
                '{env_name}':
                  variables:
                    n_ranks: '1'
                    n_nodes: '1'
                    env_name: ['gromacs-mpich', 'gromacs-ompi']
    software:
      packages:
        gcc9:
          pkg_spec: gcc@9.3.0 target=x86_64
        mpich:
          pkg_spec: mpich@4.0.2 target=x86_64
          compiler: gcc9
        ompi:
          pkg_spec: openmpi@4.1.4 target=x86_64
          compiler: gcc9
        gromacs:
          pkg_spec: gromacs@2022.4
          compiler: gcc9
      environments:
        gromacs-{mpi}:
          variables:
            mpi: ['mpich', 'ompi']
          packages:
          - gromacs
          - '{mpi}'

In the above example, you can see how ``env_name`` is used to test both an
OpenMPI and MPICH version of Gromacs. Additionally, the ``mpi_command``
variable is used to define how ``mpirun`` should look for each of the MPI
libraries.

Using the previously described Ramble vector syntax, this configuration file
will generate 2 experiments. Both ``env_name`` and ``mpi_command`` will be
zipped together, giving each experiment a tuple of: ``(mpi_command,
env_name)`` which allows us to pair a specific MPI command to the
corresponding Gromacs spec.


^^^^^^^^^^^^^^^^^^^^
Batch System Control
^^^^^^^^^^^^^^^^^^^^

Similar to the previously describe MPI command control, experiments can use
different batch systems by overriding the ``batch_submit`` variable.

Below is an example configuration file showing how the ``batch_submit``
variable can be used to submit the same experiment to multiple batch systems.

.. code-block:: yaml

    ramble:
      variants:
        package_manager: spack
      variables:
        mpi_command: 'mpirun -n {n_ranks} -ppn {processes_per_node}'
        batch_system:
        - slurm
        - pbs
        batch_submit:
        - 'sbatch {execute_slurm}'
        - 'qsub {execute_pbs}'
      applications:
        gromacs:
          workloads:
            water_bare:
              experiments:
                '{batch_system}'
                  variables:
                    n_ranks: '1'
                    n_nodes: '1'
    software:
      packages:
        gcc9:
          pkg_spec: gcc@9.3.0 target=x86_64
        impi2021:
          pkg_spec: intel-oneapi-mpi@2021.11.0 target=x86_64
          compiler: gcc9
        gromacs:
          pkg_spec: gromacs@2022.4
          compiler: gcc9
      environments:
        gromacs:
          packages:
          - impi2021
          - gromacs

The above example overrides the generated ``batch_submit`` variable to change
how different experiments are submitted. In this example, we submit the same
experiment to both SLURM and PBS.

Note that each of the two ``batch_submit`` commands submits a different
template. This means the workspace's configs directory should have two files:
``execute_slurm.tpl`` and ``execute_pbs.tpl`` which will be template submission
scripts to each of the batch systems.

-----------------
Experiment Chains
-----------------

Multiple experiments can be executed within the same context by a process known
as chaining, this allows multiple experiments (potentially from multiple
applications) to be executed in the same context and is useful for many
potential use cases such as running multiple experiments on the same physical
hardware

There are two important parts for defining an experiment chain. The first of
these is simply defining the experiment chain, and the second is defining
experiments which are only intended to be used when chained into another
experiment, known as template experiments.

^^^^^^^^^^^^^^^^^^^^^^^^^^
Defining Experiment Chains
^^^^^^^^^^^^^^^^^^^^^^^^^^

The following example shows how to specify a chain of experiments:

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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
                test_exp1:
                  variables:
                    n_ranks: '1'
                test_exp2:
                  variables:
                    n_ranks: '1'
                  chained_experiments:
                  - name: hostname.serial.test_exp1
                    command: '{execute_experiment}'
                    order: 'after_chain'
                    variables:
                      n_ranks: '2'

In the above example, the ``hostname.serial.test_exp2`` experiment defines an
experiment chain. The chain is defined by mergining the ``chained_experiments``
dictionaries and inserting itself at the appropriate location.

Experiments can be defined with in the ``chained_experiments`` dictionary using
the following format:

.. code-block:: yaml

   chained_experiments: # List of experiments to chain
   - name: Fully qualified experiment namespace
     command: Command that executes the sub experiment
     order: Order to chain this experiment. Defaults to 'after_root'
     variables: Variables dictionary to override the variables from the
                original experiment

Each chained experiment receives its own unique namespace. These take the form of:
``<parent_experiment_namespace>.chain.<chain_index>.<chained_experiment_namespace>``

In the above example, the chained experiment would have a namespace of:
``hostname.serial.test_exp2.chain.0.hostname.serial.test_exp1``

The ``name`` attribute can use `globbing
syntax<https://docs.python.org/3/library/fnmatch.html#module-fnmatch>`_ to chain
multiple experiments at once.

The ``order`` keyword is optional. Valid options include:

* ``before_chain`` Chained experiment is injected at the beginning of the chain
* ``before_root`` Chained experiment is injected right before the root experiment in the chain
* ``after_root`` Chained experiment is injected right after the root experiment in the chain
* ``after_chain`` Chained experiment is injected at the end of the chain

The ``root`` experiment is defined as the initial experiment that started the
chain. When examining the entire chain, the root experiment is the only one
that does not have ``chain.{idx}`` in its name.

The ``variables`` keyword is optional. It can be used to override the
definition of variables from the chained experiment if needed.

Once the experiments are defined, the final order of the chain can be viewed using
``ramble workspace info -vvv``.

**NOTE** When using the ``experiment_index`` variable, all experiments in a
chain share the same value. This ensures the resulting experiment will be
complete when executed.

^^^^^^^^^^^^^^^^^^^^^^^
Suppressing Experiments
^^^^^^^^^^^^^^^^^^^^^^^

The below example shows how to suppress generation of an experiment, by marking
it as a template.

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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
                test_exp1:
                  template: true
                  variables:
                    n_ranks: '1'
                test_exp2:
                  variables:
                    n_ranks: '1'
                  chained_experiments:
                  - name: hostname.serial.test_exp1
                    command: '{execute_experiment}'
                    order: 'after_chain'
                    variables:
                      n_ranks: '2'

In the above example, the ``template`` keyword is used to mark
``hostname.serial.test_exp1`` as a template experiment. This prevents it from
being used as a stand-alone experiment, but it will still be generated and used
when it's chained into other experiments.

^^^^^^^^^^^^^^^^^^^^
Variable Inheritance
^^^^^^^^^^^^^^^^^^^^

In some cases, it's useful for an experiment to take values for its variables
from the root of the chain. For example, if an allreduce benchmark should be
run on all of the nodes within a job before the actual experiment begins, but
the number of nodes changes based on the root experiment. In this case, a
workspace might be more simply defined if the root experiment can inject its
own definition for the number of nodes into the chained experiments. To
accomplish this, the: ``inherit_variables`` attribute within a chained
experiment definition can be used to define which variables should be inherited
from the root experiment.

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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
                test_exp1:
                  template: true
                  variables:
                    n_nodes: '1'
                test_exp2:
                  variables:
                    n_nodes: '4'
                  chained_experiments:
                  - name: hostname.serial.test_exp1
                    command: '{execute_experiment}'
                    order: 'after_chain'
                    inherit_variables:
                    - n_ranks

In the example above, the ``hostname.serial.test_exp2`` experiment represents
the root of the experiment chain. The ``inherit_variables`` list will cause
this root experiment to inject its own value for ``n_nodes`` into the chained
experiment, overriding its explicitly defined value in the experiment
definition.

^^^^^^^^^^^^^^^^^^^^^^^^^
Defining Chains of Chains
^^^^^^^^^^^^^^^^^^^^^^^^^

Ramble supports the ability to define chains of experiment chains. This allows
an experiment to automatically implicitly include all of the experiments chained
into the explicitly chained experiment.

Below is an example showing how chains of chains can be defined:

.. code-block:: yaml

    ramble:
      variables:
        mpi_command: 'mpirun -n {n_ranks}'
        batch_submit: '{execute_experiment}'
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
                child_level2_experiment:
                  template: true
                  variables:
                    n_ranks: '1'
                child_level1_experiment:
                  template: true
                  variables:
                    n_ranks: '1'
                  chained_experiments:
                  - name: hostname.serial.child_level2_experiment
                    order: 'before_root'
                    command: '{execute_experiment}'
                parent_experiment:
                  variables:
                    n_ranks: '1'
                  chained_experiments:
                  - name: hostname.serial.child_level1_experiment
                    command: '{execute_experiment}'

In the above example, the resulting experiment chain would be:

.. code-block:: yaml

    - hostname.serial.parent_experiment.chain.0.hostname.serial.child_level2_experiment
    - hostname.serial.parent_experiment
    - hostname.serial.parent_experiment.chain.1.hostname.serial.child_level1_experiment

.. Copyright 2022-2025 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _vector_and_matrix_tutorial:

=======================================
4) Using Vectors and Matrices
=======================================

In this tutorial, you will learn how to utilized vectors and matrices in Ramble
workspaces. Ramble's vector and matrix variable logic is defined in more detail in
:ref:`ramble-vector-logic` and :ref:`ramble-matrix-logic`

This tutorial builds off of concepts introduced in previous tutorials. Please
make sure you review those before starting with this tutorial's content.

**NOTE:** In this tutorial, you will encounter expected errors when copying and
pasting the commands. This is to help show situations you might run into when
trying to use Ramble on your own, and illustrate how you might fix them.

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

When comparing the ``ramble.yaml`` file to this output, you should notice that
the ``ramble.yaml`` file is very repetitive. Its current content shows how to
define many explicit experiments, but when trying to generate many experiments
that are similar it is unncessarily verbose. In the next step, we are going to
collapase the experiments into a single definition, and extend them to do a
basic rank based scaling study.

Editing Experiments
-------------------

In the next few sections, you will edit the workspace configuration file. To
make editing the workspace easier, use the following command (assuming you have
an ``EDITOR`` environment variable set):

.. code-block:: console

    $ ramble workspace edit

This command opens the ``ramble.yaml`` file, along with any ``*.tpl`` files in
the workspace's ``configs`` directory.

When the ``ramble.yaml`` is open, modify any of the content you want to, and
save and exit the file.

These changes should now be reflected in the output of:

.. code-block:: console

    $ ramble workspace info -vvv

Using Vector Variables
----------------------

Vector (or list) variables in Ramble are variables who's value is a list of
other values in the ``ramble.yaml`` workspace configuration file. There are
many reasons you might want to use list variables, such as defining a scaling
study, or exploring a range of a given parameter within a single experiment
definition.

Currently, your ``basic_gromacs`` workspace has 4 experiments defined. There
are two different workloads ( ``water_bare`` and ``water_gmx50`` ), and each
workload explores the two different values for the ``type`` variable ( ``pme``
and ``rf`` ).

Edit your workspace configuration, and collapse the experiment definitions
using vectors. To begin with, collapse the ``type`` values into a list within
each individual workload. You should end up with only a single experiment
definition within each of the workloads, which looks something like the
following:

.. code-block:: YAML

    pme_single_rank:
      variables:
        n_ranks: '1'
        n_threads: '1'
        size: '0003'
        type: ['pme', 'rf']

After writing this configuration, save and exit your ``ramble.yaml`` file, and execute:

.. code-block:: console

    $ ramble workspace info

To see the experiments within your workspace. If you use the configuration from
above, you should see the following error printed to the screen:

.. code-block:: console

    ==> Error: Experiment gromacs.water_bare.pme_single_rank is not unique.

Within Ramble, each experiment is required to have a unique namespace. The
namespace of an experiment is defined as:

.. code-block:: console

    <application name>.<workload name>.<rendered experiment name>

So, changing things like the application or workload automatically create a
unique namespace, but changing vector variables within an experiment do not
automatically generate a unique namespace. In this case, your experiments that
have a different ``type`` both result in the same experiment name.

Templatized Experiment Names
----------------------------

In order to generate unique experiment namespaces while using vector variable
definitions, Ramble allows the experiment name to be templatized using variable
names as expansion placeholders.

To fix the error from the previous section, you need to modify the experiment
name that contains the vector ``type`` definition. The result should look
something like the following:

.. code-block:: YAML

    '{type}_single_rank':
      variables:
        n_ranks: '1'
        n_threads: '1'
        size: '0003'
        type: ['pme', 'rf']

Notice how the name of the experiment changed from ``pme_single_rank`` to
``'{type}_single_rank'``. This allows Ramble to populate the experiment name by
expanding the ``{type}`` variable reference.

**NOTE** Because we are editing YAML, the experiment name needs to be
explicitly delimited as a string. Notice how in the above example we wrap the
experiment name in single quotes to explicitly make it a string. Without this,
YAML parsers identify the leading ``{`` character, and assume the content is a
dictionary.

Now, save and exit the file. The resulting experiments can be seen using:

.. code-block:: console

    $ ramble workspace info

And the result should be something like the following (if you have changed the
experiment definition under both workloads):

.. code-block:: console

    Experiments:
      Application: gromacs
        Workload: water_gmx50
          Experiment: gromacs.water_gmx50.pme_single_rank
          Experiment: gromacs.water_gmx50.rf_single_rank
      Application: gromacs
        Workload: water_bare
          Experiment: gromacs.water_bare.pme_single_rank
          Experiment: gromacs.water_bare.rf_single_rank

Vectorizing Workload Names
--------------------------

The next step in the process of simplifying your workspace configuration file
is to vectorize the workload names used. Here, we'll use a similar technique to
templates the experiment names.

Edit your workspace configuration file, and define a new variable named
``app_workload`` within one of the two experiments. Set the value of this
variable to ``['water_bare', 'water_gmx50']`` and delete the other experiment
definition entirely.

Finally, to allow ramble to generate experiments for each workload, change the
workload name to ``'{app_workload}'``. The resulting portion of the
``ramble.yaml`` file should look like the following:

.. code-block:: YAML

    workloads:
      '{app_workload}': # Workload name from application
        experiments:
          '{type}_single_rank': # Arbitrary experiment name
            variables:
              app_workload: ['water_bare', 'water_gmx50']
              n_ranks: '1'
              n_threads: '1'
              size: '0003'
              type: ['pme', 'rf']

At this point, you can save and exit. Executing:

.. code-block:: console

    $ ramble workspace info

Should show the following output:

.. code-block:: console

    Experiments:
      Application: gromacs
        Workload: {app_workload}
          Experiment: gromacs.water_bare.pme_single_rank
          Experiment: gromacs.water_gmx50.rf_single_rank

However, at this point you should only see two experiments while we expect to
see four. This is because of the way multiple vector variables are handled in
Ramble. After consuming vector variables (which we'll describe in the next
section) the resulting vectors are required to be the same length (in this case
they are both of length 2) and are zipped together and iterated over to
generate experiments. In this case, the resulting zip looks something like the
following:

.. code-block:: console

    [ (water_bare, pme), (water_gmx50, rf) ]

While we want something more like:

.. code-block:: console

    [ (water_bare, pme), (water_bare, rf), (water_gmx50, pme), (water_gmx50, rf) ]

To remedy this issue, we will use Ramble's matrix definitions.

Variable Matrices
-----------------

As you've seen so far, you can define vector variables in Ramble. These
definitions can be implicitly zipped together to generate multiple experiments.
However, sometimes you would actually prefer to have an explicit cross product
of the variable definitions to explore a wider range of parameter combinations.
To perform this task, Ramble allows you to use variable ``matrix`` or
``matrices`` definitions. These definitions can only happen at the lowest level
(i.e. within the individual experiment scope) of a ``ramble.yaml`` file.

Any variable listed within any matrix definition is considered **consumed** by
the matrix. This removes the variable definition from the implicit zip logic
defined in the previous section. Multiple matrices can be defined (though we
will not illustrate this in this tutorial). When multiple matrices are defined
within the same experiment, they are required to have the same resulting number
of elements. After they are individually built, they are zipped together to
create one large set of variable values to generate experiments from. If there
are unconsumed vector variables, they follow the zip logic described in the
previous section, and which is then crossed with the result of the matrix
construction.

To remedy your currently configuration issue (seeing two experiments instead of
the desired four experiments), we will employ a variable matrix to define the
additional experiments.

Edit your ``ramble.yaml`` and update your experiment definition to the following:

.. code-block:: YAML

    workloads:
      '{app_workload}': # Workload name from application
        experiments:
          '{type}_single_rank': # Arbitrary experiment name
            variables:
              app_workload: ['water_bare', 'water_gmx50']
              n_ranks: '1'
              n_threads: '1'
              size: '0003'
              type: ['pme', 'rf']
            matrix:
            - app_workload
            - type


You should notice the addition of the ``matrix`` section at the bottom of this.
Here we are constructing a new variable matrix which will be created using the
cross product of the ``app_workload`` and ``type`` variable definitions. Since
each has a length of two, the result would be a matrix with four elements in
it.

After saving and exiting this file, the resulting experiments can be seen using the:

.. code-block:: console

    $ ramble workspace info

command. Which should present the following output:

.. code-block:: console

    Experiments:
      Application: gromacs
        Workload: {app_workload}
          Experiment: gromacs.water_bare.pme_single_rank
          Experiment: gromacs.water_bare.rf_single_rank
          Experiment: gromacs.water_gmx50.pme_single_rank
          Experiment: gromacs.water_gmx50.rf_single_rank


Defining a Scaling Study
------------------------

The final modification you'll make to this workspace is to update the
experiment definition to perform a basic rank based scaling study.

Edit the ``ramble.yaml`` file, and perform the following steps:

 #. Update the value for ``n_ranks`` to be ``[1, 2]``
 #. Add the ``n_ranks`` variable to the matrix definition
 #. Ensure your experiment name uses the ``{n_ranks}`` placeholder

At this point, your complete ``ramble.yaml`` file should look like the
following:

.. literalinclude:: ../../../../examples/vector_matrix_gromacs_config.yaml
   :language: YAML

However, your experiment name template may look different from the above, as
long as it contains the ``{type}`` and ``{n_ranks}`` placeholders, you should
consider it correct.

To see the final set of experiments, execute:

.. code-block:: console

    $ ramble workspace info

Which should contain the following output:

.. code-block:: console

    Experiments:
      Application: gromacs
        Workload: {app_workload}
          Experiment: gromacs.water_bare.pme_1ranks
          Experiment: gromacs.water_bare.pme_2ranks
          Experiment: gromacs.water_bare.rf_1ranks
          Experiment: gromacs.water_bare.rf_2ranks
          Experiment: gromacs.water_gmx50.pme_1ranks
          Experiment: gromacs.water_gmx50.pme_2ranks
          Experiment: gromacs.water_gmx50.rf_1ranks
          Experiment: gromacs.water_gmx50.rf_2ranks

.. include:: shared/gromacs_execute.rst

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

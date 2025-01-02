.. Copyright 2022-2025 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _success-criteria_tutorial:

===================
9) Success Criteria
===================

In this tutorial, you will learn how to use success criteria. These will be
created and applied to experiments for
`WRF <https://www.mmm.ucar.edu/models/wrf>`_, a free and open-source
application for atmospheric research and operational forecasting applications.

This tutorial builds off of concepts introduced in previous tutorials. Please
make sure you review those before starting with this tutorial's content.

Create a Workspace
------------------

To begin with, you need a workspace to configure the experiments. This can be
created with the following command:

.. code-block:: console

    $ ramble workspace create success_wrf


Activate the Workspace
----------------------

Several of Ramble's commands require an activated workspace to function
properly. Activate the newly created workspace using the following command:
(NOTE: you only need to run this if you do not currently have the workspace
active).

.. code-block:: console

    $ ramble workspace activate success_wrf

.. include:: shared/wrf_scaling_workspace.rst

Success Criteria
----------------

Ramble provides you with the ability to define success criteria within an
application's ``application.py`` file, or within the ``success_criteria``
configuration scope (which can also be defined in a workspace's ``ramble.yaml``
configuration file). There are three supported types of success criteria,
including:

 #. Regular Expression String Matching
 #. Figure of Merit Logic Based
 #. Arbitrary Python Based

This tutorial will focus on the first two of these, as the third can only be
defined within the ``application.py`` file.

For more in-depth documentation about success criteria, see
:ref:`success-criteria`.

Regular Expression String Matching
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The most common success criteria is the regular expression based string
matching. These can be defined within either the ``application.py`` or the
``success_criteria`` configuration scope. Several ``application.py`` files
already define this type of success criteria in order to make it easier for
users to be sure their experiments completed successfully.

When WRF runs, it outputs the time each timestep takes. To begin with, you will
define a new success criteria within your workspace configuration file that
validates some timing data is present in the output of an experiment. In the
experiment output, the timing data is prefixed with the string
``Timing for main``.

This success criteria might look like the following:

.. code-block:: YAML

    success_criteria:
    - name: 'timing-present'
      mode: 'string'
      match: 'Timing for main.*'
      file: '{experiment_run_dir}/rsl.out.0000'

Edit your workspace configuration file with:

.. code-block:: console

    $ ramble workspace edit

And add the example block within the ``wrfv4`` application block. The resulting
configuration file might look like the following:

.. literalinclude:: ../../../../examples/tutorial_9_regex_criteria_config.yaml
   :language: YAML

Placing the success criteria definition here applies it to all of the
experiments defined within the ``wrfv4`` application.

Figure of Merit Logic Based
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to string matching, Ramble allows you to define a figure of merit
based success criteria. These success criteria can be defined as equations that
include placeholders for figures of merit the application will generate.

In this portion of the tutorial, you will define a new success criteria that
ensures the experiments all have at least 50 timesteps to be considered
successful. The figure of merit definition for this might look like the follow:

.. code-block:: YAML

    success_criteria:
    - name: 'correct-timesteps'
      mode: 'fom_comparison'
      fom_name: 'Number of timesteps'
      formula: '{value} >= 50'

Edit your workspace configuration using:

.. code-block:: console

    $ ramble workspace edit

And add the success criteria within the ``CONUS_12km`` workload definition. The
resulting configuration file might look like the following:

.. literalinclude:: ../../../../examples/tutorial_9_fom_criteria_config.yaml
   :language: YAML

This new success criteria will apply to all experiments within the
``CONUS_12km`` workload. This is because different workloads could have
different numbers of timesteps.

It is important to note that the ``formula`` attribute of the success criteria
definition can refer to other variables. As an example, one of the figures of
merit output by the ``wrfv4`` application definition is
``Average Timestep Time``. If you had a single node value for this figure of
merit and expected this to scale linerally you could define a success criteria
as follows:

.. code-block:: YAML

    variables:
      single_node_value: '1.0'
    success_criteria:
    - name: 'valid-scaling'
      mode: 'fom_comparison'
      fom_name: 'Average Timestep Time'
      formula: '{value} <= {single_node_value} / {n_nodes}'

You won't test this success criteria in this tutorial, as the
``single_node_value`` might not be correct for your system, but feel free to
explore using this after you perform experiments.


.. include:: shared/wrf_execute.rst

To ensure the success criteria are checked and the experiments pass them,
ensure ``SUCCESS`` is printed for the status of each experiment.

Running analyze in debug mode as:

.. code-block:: console

    $ ramble -d workspace analyze

Will print significnatly more output, but you should see where Ramble tests the
``timing-present`` and ``correct-timesteps`` success criteria in the output.

Clean the Workspace
-------------------

Once you are finished with the tutorial content, make sure you deactivate your workspace:

.. code-block:: console

    $ ramble workspace deactivate

Additionally, you can remove the workspace and all of its content with:

.. code-block:: console

    $ ramble workspace remove success_wrf

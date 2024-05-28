.. Copyright 2022-2024 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _modifying_an_experiment_tutorial:

============================
5) Changing A Software Stack
============================

In this tutorial, you will learn how to modify an existing workspace
configuration that contains experiments using
`GROMACS <https://www.gromacs.org/>`_, a free and open-source application
for molecular dynamics.

This tutorial builds off of concepts introduced in previous tutorials. Please
make sure you review those before starting with this tutorial's content.

.. include:: shared/gromacs_vector_workspace.rst

Software Description
--------------------

Now that your workspace has been created, and configured with the default
workspace configuration file you can examine the workspace contents. You can
execute the following command to see what software environments and packages
the workspace currently contains:

.. code-block:: console

    $ ramble workspace info

This command provides a summary view of the workspace. It includes the
experiment names, and the software environments. As an example, its output
might contain the following information regarding software packages and
environments:

.. code-block:: console

    Software Stack:
      Packages:
        gcc9:
          Rendered Packages:
            gcc9:
              Spack spec: gcc@9.4.0 target=x86_64
              Compiler spec: gcc@9.4.0
        impi2021:
          Rendered Packages:
            impi2021:
              Spack spec: intel-oneapi-mpi@2021.11.0 target=x86_64
              Compiler: gcc9
        gromacs:
          Rendered Packages:
            gromacs:
              Spack spec: gromacs@2021.6
              Compiler: gcc9
      Environments:
        gromacs:
          Rendered Environments:
            gromacs Packages:
              - gromacs
              - impi2021


Currently, this command outputs every package and software environment
definition, even if they are not used directly by an experiment. By default,
each experiment expects a software environment that is named the same as the
application. For example, an experiment for the application ``gromacs`` expects
a software environment named ``gromacs``. This can be overridden using the
variable ``env_name``, which can be the name of any environment defined in the
workspace configuration file.


The relevant portion of the workspace configuration file is:

.. code-block:: YAML

    spack:
      packages:
        gcc9:
          pkg_spec: gcc@9.4.0 target=x86_64
          compiler_spec: gcc@9.4.0
        impi2021:
          pkg_spec: intel-oneapi-mpi@2021.11.0 target=x86_64
          compiler: gcc9
        gromacs:
          pkg_spec: gromacs@2021.6
          compiler: gcc9
      environments:
        gromacs:
          packages:
          - gromacs
          - impi2021

In this configuration, the ``packages`` block defines software packages that
can be used to build experiment environments out of. The ``environments`` block
defines software environments which can be used for the experiments listed
within the ``ramble:applications`` block. Keys within both ``packages`` and
``environments`` are the name of the package or environment (respectively).
Each environment has a ``packages`` block, which contains a list of package
names that are defined in the higher level ``packages`` block.

These are further documented in the
:ref:`Spack configuration section<spack-config>` documentation.

Changing Software Definitions
-----------------------------

As the GROMACS application definition inherits from the ``SpackApplication``
base class, it is expected to use Spack as its package manager. When changing
the software definitions in a workspace, many options are available to you. For
example, you could modify the compiler used for building GROMACS (as defined on
line 45), or you could modify the MPI used for these experiments (as seen on
line 53). However, we will explore changing aspects of GROMACS itself (such as
its version or variants). 

**NOTE:** It is important to note that changing aspects of
compilation could result in build-time errors that need to be resolved before
Ramble can generate experiments. Oftentimes it is both easier and faster to
work through these issues (if you encounter them) outside of Ramble, using the
package manager directly. Because Ramble uses the package manager, if the
package is already installed it will not cause the package manager to re-install
it.

In order to get information about what changes you can make to the GROMACS
package, you can use:

.. code-block:: console

    $ spack info gromacs


This command will output all of the supported versions of GROMACS, along with
the variants for GROMACS which can modify its behavior. While you can change
any of these, we'll begin by only modifying the version of GROMACS from
``2021.6`` to ``2021.7``.

To make editing the workspace easier, use the following command (assuming you
have an ``EDITOR`` environment variable set):

.. code-block:: console

    $ ramble workspace edit

This command opens the ``ramble.yaml`` file, along with any ``*.tpl`` files in
the workspace's ``configs`` directory.

Once the ``ramble.yaml`` file is opened, change the version ``2021.6`` to
``2021.7`` on line 47. Then save and exit the files. These changes should now
be reflected in the output of:

.. code-block:: console

    $ ramble workspace info


.. include:: shared/gromacs_execute.rst

**NOTE**: Since you changed the package definition for GROMACS, it will be
recompiled (unless you compiled it outside of Ramble) during the ``ramble
workspace setup`` command. This will likely take longer than changing
experiments and performing setup again.

Adding Package Variants
-----------------------

So far, we have only explored changing the version a package used. More
complicated changes to the Spack specs can be made by adding variant
definitions. This can be directly added to the ``pkg_spec`` lines within the
package definitions in a workspace's ``ramble.yaml``.

The ``pkg_spec`` attribute can be parameterized with variable definitions
also, to allow a wide range of variants to be explored with a single
configuration.

Vector and Matrix Software Definitions
--------------------------------------

Package and environment definitions support the same vector and matrix logic as
introduced in :ref:`vector_and_matrix_tutorial`. Package and environment names
should similarly be unique, and can use placeholder values for variable
definitions.

As an example, to explore both of the versions of GROMACS described in this
tutorial, your ``ramble.yaml`` could look like the following:

.. literalinclude:: ../../../../examples/vector_gromacs_software_config.yaml
   :language: YAML

Using this configuration file, you can examine what changes it would make to
your workspace through:

.. code-block:: console

    $ ramble workspace info
    or;
    $ ramble workspace setup --dry-run

Cleaning the Workspace
----------------------

Once your are finished with the tutorial content, deactivate your workspace using:

.. code-block:: console

    $ ramble workspace deactivate

Additionally, you can remove the entire workspace and all of its contents using:

.. code-block:: console

    $ ramble workspace remove basic_gromacs

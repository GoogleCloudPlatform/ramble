.. Copyright 2022-2023 Google LLC

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _workspace:

================
Ramble Workspace
================

In Ramble, a workspace is a self contained directory representing a set of
experiments that should be executed. This document describes overall aspects of
workspaces, and how to use them.

-------------------
Creating Workspaces
-------------------

The ``ramble workspace create`` command can be used to create workspaces.

Workspaces are created with a standard structure, and some basic configuration
files that the user can modify to control the exact behavior of the experiments
within the workspace.

Ramble can create two types of workspaces:
* anonymous workspaces
* named workspaces

^^^^^^^^^^^^^^^
Named Workspace
^^^^^^^^^^^^^^^

By default, Ramble creates named workspaces, which are workspaces which Ramble
will manage. To create a named workspace, use:

.. code-block:: console

    $ ramble workspace create <name_of_workspace>

These workspaces are created by default in ``$ramble/var/ramble/workspaces``,
but that location can be changed. For example, the following command will
change the default location for creating workspaces to
``~/.ramble/workspaces``:

.. code-block:: console

    $ ramble config add 'config:workspace_dirs:~/.ramble/workspaces'

^^^^^^^^^^^^^^^^^^^
Anonymous Workspace
^^^^^^^^^^^^^^^^^^^

Anonymous workspaces are workspaces that Ramble will not manage and will live
in a specified directory. To create an anonymous workspace, use:

.. code-block:: console

    $ ramble workspace create -d <path_to_workspace>

.. _workspace-structure:

-------------------
Workspace Structure
-------------------

Ramble creates workspaces using the following structure by default:

.. code-block:: console

    $workspace
    | - configs/
    |   | - ramble.yaml
    |   | - execute_experiment.tpl
    |   | - auxiliary_software_files/
    | - experiments/
    | - inputs/
    | - logs/
    | - software/


This various parts of this directory structure are defined as:
* ``configs/``: Contain configuration for the workspace
* ``configs/auxiliary_software_files``: Contain files used by the package managers
* ``experiments/``: Contain experiments define by the workspace configuration
* ``inputs``: Contain the inputs experiments in this workspace require
* ``logs``: Contain some logging output from ramble
* ``software``: Contain software environments an application's package manager creates

In the ``configs`` directory, the ``ramble.yaml`` file is the primary workspace
configuration file. The definition for this file is documented in the
:ref:``workspace config documentation<workspace-config>``


Every file with the ``.tpl`` extension is considered a template file in the
workspace. These are rendered into each experiment (with the extension
omitted). This allows control over the script format to execute an experiment.


----------------------
Activating a Workspace
----------------------

Several Ramble commands require an activated workspace to function properly. A workspace can be activated in a few different ways:

.. code-block:: console

    $ ramble workspace activate <name_or_path>

will activate a workspace until it is deactivated, while

.. code-block:: console

    $ ramble -D <path_to_workspace workspace ...

    or

    $ ramble -w <workspace_name> workspace ...

will activate a workspace for the specific command.

------------------------------
Printing Workspace Information
------------------------------
In order to see an overview of what experiments a workspace contains, one can
use:

.. code-block:: console

    $ ramble workspace info

To get basic information, and:

.. code-block:: console

    $ ramble workspace info -v

To get more detailed information, including which variables are defined and
where they come from.

------------------------
Concretizing a Workspace
------------------------

The software definitions in a workspace need to be concretized before the
workspace can be set up. To have Ramble pull software definitions from the
appliaction definition files, one can use:

.. code-block:: console

    $ ramble workspace concretize


.. _workspace-setup:

----------------------
Setting up a Workspace
----------------------

To make Ramble fully configure a workspace, one can use:

.. code-block:: console

    $ ramble workspace setup

This can be an expensive process, and Ramble will:
* Install software
* Download input files
* Create all experiment directives and content

To perform a light-weight test version of this, one can use:

.. code-block:: console

    $ ramble workspace setup --dry-run

Which will create experiments, but it won't download or install anything.

^^^^^^^^^^^^^^^
Phase Selection
^^^^^^^^^^^^^^^

Some workflows would benefit from more fine-grained control of the phases that
are executed by Ramble. A good example is that sometimes one only wants to run
the ``make_experiments`` phase of a workspace instead of all of the phases.

The ``ramble workspace setup`` command has a ``--phases`` argument, which can
take phase filters which will be used to down-select the phases which should be
executed.

As an example:

.. code-block:: console

    $ ramble workspace setup --phases make_experiments

Would execute only the ``make_experiments`` phase of all experiments that have
this phase.

The ``--phases`` argument supports wildcard matching, i.e.:

.. code-block:: console

    $ ramble workspace setup --phases *_experiments

Would execute all phases that have then ``_experiments`` suffix.

^^^^^^^^^^^^^^^^^^^^^
Software Environments
^^^^^^^^^^^^^^^^^^^^^

When setting up a workspace, Ramble will install software defined by the
workspace configuration file. Ramble uses external package mangers to perform
the installation and generate software environments for each experiment.

As an example, if the applications and workspace configuration file provide a
configuration for Spack, Ramble will generate
`Spack environments<https://spack.readthedocs.io/en/latest/environments.html>`.

By default, Ramble uses the following format for creating a spack environment file:

.. code-block:: yaml

    spack:
      concretizer:
        unify: true
      specs:
      - packages
      - for
      - environment
      include:
      - files
      - from
      - auxiliary_software_files

In addition to generating a ``spack.yaml`` file for each software environment,
Ramble will expand unique copies of each file contained in the
``configs/auxiliary_software_files`` directory into every software environment
it generates.

These can be used to modify the behavior of Spack environments generated by Ramble.

^^^^^^^^^^^^^^^^^^^^^^^^^^^
Workspace Invetory and Hash
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setting up a workspace will create inventory files that can be used to identify
which aspects of experiments or workspaces change between different
invocations.

Most of an experiment's inventory is defined regardless of if ``--dry-run`` is
used or not. The notable exception to this is the ``software`` hashes. The file
that is hashed depends on if the underlying software environment is fully
defined or not.

As an example, if Spack applications are used, ``--dry-run`` only creates (and
hashes) ``spack.yaml`` files, which are not concrete. When ``--dry-run`` is not
used, Ramble will cause Spack to generate ``spack.lock`` files, which will then
be hashed, giving better information about if the file changes or not.

The hash for a workspace is written to ``$workspace/workspace_hash.sha256``,
and the inventories are written to
``$workspace/experiments/<application>/<workload>/<experiment>/ramble_inventory.json``
and ``$workspace/ramble_inventory.json``.

Below is an example of a workspace inventory:

.. code-block:: json

    {
      "experiments": [
        {
          "name": "gromacs.water_bare.test",
          "digest": "3f4a333db9f76a06826e4c3775bb4384af8904f474a74a4b1eb61f4d6d02939c",
          "contents": {
            "attributes": [
              {
                "name": "variables",
                "digest": "0fc2c3b848885404201f5435389e9028460ea68affd6c78149b7a8c7e925d004"
              },
              {
                "name": "modifiers",
                "digest": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
              },
              {
                "name": "chained_experiments",
                "digest": "74234e98afe7498fb5daf1f36ac2d78acc339464f950703b8c019892f982b90b"
              },
              {
                "name": "internals",
                "digest": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
              },
              {
                "name": "env_vars",
                "digest": "035f0c03572706ee6da6f0f74614717b201aabe0f7671fc094478d1a97e5dcc4"
              },
              {
                "name": "template",
                "digest": "fcbcf165908dd18a9e49f7ff27810176db8e9f63b4352213741664245224f8aa"
              }
            ],
            "inputs": [
              {
                "name": "water_bare",
                "digest": "2fb58b2b856117515c75be9141450cca14642be2a1afe53baae3c85d06935caf"
              }
            ],
            "software": [
              {
                "name": "software/gromacs.water_bare",
                "digest": "12f222f06ca05cb6fca37368452b3adedf316bc224ea447e894c87d672333cca"
              }
            ],
            "templates": [
              {
                "name": "execute_experiment",
                "digest": "ea07af55040670edaf23e2bfd0b537c8ed70280a3616021a5203bdf65e08a4c6"
              }
            ]
          }
        }
      ],
      "versions": [
        {
          "name": "ramble",
          "version": "0.3.0 (9947210de68fb42dfd843ed1ab982aba0145e9d3)",
          "digest": "02f5fbbfe0a9fe38b99186619e7fb1d11e6398c637a24bb972fffa66e82bf3fe"
        },
        {
          "name": "spack",
          "version": "0.20.0.dev0 (3c3a4c75776ece43c95df46908dea026ac2a9276)",
          "digest": "21fb90b4cffd46b2257469da346cdf0bcf7070227290262b000bb6c467acfc44"
        }
      ]
    }

As mentioned above, the only part that varies when switching ``--dry-run`` on
and off are the digest values for each software attribute. The hash of the
workspace is the hash of its inventory file. All hashes are sha256.

---------------------
Executing a Workspace
---------------------

Once a workspace is set up, the experiments inside it can be executed using:

.. code-block:: console

    $ ramble on

---------------------
Analyzing a Workspace
---------------------

After the experiments inside a workspace are complete, they can be analyzed using:

.. code-block:: console

    $ ramble workspace analyze

By default this creates text output describing the figures of merit from the
workspace's experiments. The format can be controlled using:

.. code-block:: console

    $ ramble workspace analyze --format text json yaml

With supported formats being ``text``, ``json``, or ``yaml``.

Ramble also include an experimental capability to uplodate figures of merit
into a back-end data base. Currently BigQuery is the only supported back-end,
however more back-ends can be implemented. To upload data, one can use:

.. code-block:: console

    $ ramble workspace analyze --upload

This will automatically read the upload configuration from the ``upload`` block
of :ref:`Ramble's config file<config-yaml>`.

---------------------
Archiving a Workspace
---------------------

A workspace can be archived to either:
* Share with other people
* Keep for future reproduction

In order to archive a workspace, one can use:

.. code-block:: console

    $ ramble workspace archive

An archive can be automatically uploaded to a mirror using:

.. code-block:: console

    $ ramble workspace archive -t --upload-url <mirror_url>

When Ramble creates an archive, it will collect the following files:
* All files in ``$workspace/configs``
* Generated files for each software environment. (i.e. Each ``spack.yaml`` for spack environments)
* For each experiment, the following are collected:
  * Every rendered template (created from a ``$workspace/configs/*.tpl`` file)
  * Every file a success criteria or figure of merit would be extract from
  * Every file that matches an ``archive_pattern`` from the ``application.py``

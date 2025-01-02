.. Copyright 2022-2025 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _definition-dev-guide-adv-topics:

=========================================
Advanced Topics for Definition Developers
=========================================

Some application or modifier definition files have more complex requirements
than those met with the directives that are covered the object specific
developer guides. This developers guide will teach you several more advanced
concepts to help write more specialized definition files.

The functionality described in this guide is briefly described within the
:ref:`package manager developer guide<package-manager-dev-guide>`, but will be
covered in more detail here. This functionality is shared by all of the object
types supported in Ramble.

.. _ramble-pipelines-and-phases:

------------------------------
Experiment Pipelines and Phases
------------------------------

Ramble has a concept of ``pipeline``, which represent full actions that can
be taken on a workspace. Some of the common ``pipelines`` that are used are the
``setup`` (driven with ``ramble workspace setup``) and ``analyze`` (driven with
``ramble workspace analyze``) pipelines.

There are several more pipelines that Ramble uses to perform complex actions
on a workspace, which can be seen in :mod:`ramble.pipeline`.

Pipelines are built out of phases. In Ramble, a ``phase`` represents a specific
step along the path of completing the action defined by the ``pipeline``.
Examples of phases include ``get_inputs`` (for downloading input files needed
by a workload) and ``software_install`` (for performing software installation
using a package manager).

Phases can be defined in a variety of locations. Some base classes (e.g.
:mod:`ramble.application`) define phases for specific pipelines. Additionally,
instances of application, modifier, or package manager definitions can define
phases as well. Each phase is defined in two parts. The first part is to define
a class method on a object definition. Phase names need to begin with an
underscore, and they have the following signature:

.. code-block::

  def _new_phase_name(self, workspace, app_inst=None)

In this signature, ``workspace`` is a reference to the workspace that has a
pipeline acting on it, and ``app_inst`` is a reference to the application
instance representing the experiment. The ``app_inst`` should be identical to
``self`` when ``self`` is an instance of an application definition.

Once the phase's method is complete, it can be registered into a pipeline as
follows:

.. code-block::

  register_phase("new_phase_name", pipeline="setup", run_before=["make_experiments"])

This example would register the phase defined by ``_new_phase_name`` into the
setup pipeline, and make sure it is executed before the ``make_experiments``
phase. Phase registration can also define a ``run_after`` list of phases to execute
before the newly registered phase. A phase can also be registered into multiple
pipelines, by calling the ``register_phase`` directive multiple times.

Applications, Modifiers, and Package Managers can all defined and register
their own phases to build more complex pipelines for specific usecases.

.. _ramble-builtins:

--------
Builtins
--------

Another component of object definitions is a ``builtin``. These are intended to
be semi-static command blocks that should / could be injected into experiments
using this definition. Similar to phases, builtins are defined in two steps.

The first step in defining a ``builtin`` is to define a class method with the
following signature:

.. code-block::

  def new_builtin(self):
    cmds = []
    ... add strings to cmds ...
    return cmds

Once the class method is defined, the second step is to register the builtin
into the object definition. Builtin registration is accomplished using the
``register_builtin`` directive, as follows:

.. code-block::

  register_builtin("new_builtin", required=True/False, injection_method="prepend"/"append", depends_on=[...])

When registering a builtin, the ``required`` attribute controls whether the builtin
is required to be present in experiments generated using the object or not. The
``injection_method`` attribute controls if the commands defined by the builtin
should be at the beginning (``prepend``) or end (``append``) of the experiment.
The ``depends_on`` attribute can be used to define the ordering of multiple
builtins relative to each other. Fully qualified builtin names are passed in
here, and their named depend on which object they are defined in.

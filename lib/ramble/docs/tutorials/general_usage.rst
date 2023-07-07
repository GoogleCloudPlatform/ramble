.. Copyright 2022-2023 Google LLC

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _general_usage_tutorial:

=============
General Usage
=============

This tutorial will provide a basic introduction to installing Ramble and some
of its commands.

-------------
Installation:
-------------

There are two ways to install Ramble. The first, and recommended, approach is to clone its git repository. This can be done with:

.. code-block:: console

    $ git clone https://github.com/GoogleCloudPlatform/ramble

By default, this will checkout the ``develop`` branch, which is the most
up-to-date version of Ramble. Several tags, as well as the ``main`` branch
(which contains the latest tag) can provide a more stable exeperience.

The second approach is to download one of the releases from
`Ramble's releases page <https://github.com/GoogleCloudPlatform/ramble/releases>`_

Once ramble is available on your system, its python dependencies can be
installed using the ``requirements.txt`` file included in the root of Ramble's
source directory.

To install this, you can use:

.. code-block:: console

    $ pip install -r requirements.txt

However, the exact command will depend on your environment.

In order to setup Ramble in your environment, you can execute:

.. code-block:: console

    $ . $ramble_root/share/ramble/setup-env.sh

Which would work for ``sh`` based shells. There are similarly setup scripts for
``csh`` and ``fish`` which can be used instead.


-----------------------
Available Applications:
-----------------------

Once Ramble is installed, viewing the available application definitions is as
simple as executing:

.. code-block:: console

    $ ramble list

The ``ramble list`` command also takes a query string, which can be used to
filter available application definitions. For example:

.. code-block:: console

    $ ramble list hp*

might output the following:

.. code-block:: console

    ==> 3 applications
    hpcc  hpcg  hpl


Additionally, applications can be filtered by their tags, e.g.

.. code-block:: console

    $ ramble list -t benchmark-app
    ==> 3 applications
    hpcc  hpcg  hpl

The available tags (and their mappings to applications) can be listed using:

.. code-block:: console

    $ ramble attributes --all --tags

^^^^^^^^^^^^^^^^^^^^^^^^^
What's in an application?
^^^^^^^^^^^^^^^^^^^^^^^^^

Knowing what applications are available is only part of how a user interacts
with Ramble. Each application contains one or more workloads, all of which can
contain their own variables to control their behavior. The ``ramble info``
command can be used to get more information about a specific application
definition. As an example:

.. code-block:: console

    $ ramble info hpl

Will print the workloads and variables the ``HPL`` application definition contains.

--------------------
Available Modifiers:
--------------------

In addition to application definitions, Ramble provides Modifier definitions.
Modifiers are objects which can modify experiments they are applied to without
having to change the definition of the application. Some examples of useful
modifiers are profilers and tools to get system information.

Available modifiers can be listed with:

.. code-block:: console

    $ ramble mods list

Information about what a modifier does, and how it can be used can be displayed
with the ``ramble mods info <mod-name>`` command. As an example:

.. code-block:: console

    $ ramble mods info lscpu

Will print information about the ``lscpu`` modifier.

.. Copyright 2022-2025 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.


.. _package_manager_control:

================
Package Managers
================

Within Ramble's :ref:`variants configuration section <variants-config>`, users
can control which package manager is used for a set of experiments.

The package manager used controls many aspects of the experiment, such as how
software is installed. Each experiment within a workspace can use a different
package manager, to explore the impact of changing this dimension of an
experimental design.

----------------------------
Configuring Package Managers
----------------------------

Package managers are controlled through a config option in the 
:ref:`variants configuration section <variants-config>`. The following shows an
example of controlling this

.. code-block:: yaml

  variants:
    package_manager: <package_manager_name>

The default package manager is `null` which disables the use of any package
manager in the generated experiments. The value of the package manager used can
be a reference to a variable, and will be expanded following Ramble's
:ref:`variable definitions <variable-dictionaries>` logic.

--------------------------
Supported Package Managers
--------------------------

Currently supported package managers in Ramble include:

 * None / null
 * environment-modules
 * eessi
 * pip
 * spack
 * spack-lightweight

^^^^^^^^^^^^^^^^^^^^
None Package Manager
^^^^^^^^^^^^^^^^^^^^

Setting the package manager config option to ``None`` or ``null`` disables the
use of a package manager within the experiments. In this case, experiments are
expected to define the paths to their own executables, and installation of
these executables should be provided outside of Ramble (i.e. manual
installation).


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Environment Modules Package Manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setting the package manager config option to ``environment-modules`` enables
the use of `Environment Modules <https://modules.readthedocs.io/en/latest/>`_
within the resulting experiments. Ramble will inject ``module load`` commands
into each experiment, to prepare the execution environment.

The :ref:`software configuration section <software-config>` is used to
determine what modules to load within the resulting environment.

The use of this package manager requires an installation of
``environment-modules`` outside of Ramble. This is handled by system
administrators on several clusters, but for more information see
`environment-modules's documentation <https://modules.readthedocs.io/en/latest/INSTALL.html>`_.

^^^^^^^^^^^^^^^^^^^^^
EESSI Package Manager
^^^^^^^^^^^^^^^^^^^^^

Setting the package manager config option to ``eessi`` enables the use of
`the European Environment for Scientific Software Installations (EESSI) <https://www.eessi.io/docs/>`_
for each experiment. Ramble will then inject commands to initialize the use of
EESSI, and load the correct module files for the execution environment.

The :ref:`software configuration section <software-config>` is used to
determine what modules to load within the resulting environment.

The use of this package manager requires an installation of EESSI outside of
Ramble. For more information, see
`EESSI's documentation <https://www.eessi.io/docs/getting_access/native_installation/>`_.

^^^^^^^^^^^^^^^^^^^
Pip Package Manager
^^^^^^^^^^^^^^^^^^^

Setting the package manager config option to ``pip`` enables the use of pip and
python virtual environments for each experiment. During the ``setup`` pipeline,
Ramble will construct a python virtual environment in the workspace's
``software`` directory. This environment will contain pip installed python
packages and will be automatically loaded within experiments using this package
manager.

The :ref:`software configuration section <software-config>` is used to
determine what packages to install within the resulting virtual environment.

The use of this package manager requires ``pip`` to be installed outside of
Ramble. This happens automatically in several Python installations. For more
information see
`pip's documentation<https://pip.pypa.io/en/stable/installation/>`_.

^^^^^^^^^^^^^^^^^^^^^
Spack Package Manager
^^^^^^^^^^^^^^^^^^^^^

Setting the package manager config option to ``spack`` enables the use of
`Spack <https://spack.io/>`_ for each experiment. During the ``setup`` pipeline,
Ramble will construct Spack environments and install the requested software.
The experiments using Spack will automatically load the environment to prepare
the experiment for execution.

The :ref:`software configuration section <software-config>` is used to
determine what packages to install within the resulting environment.

When using the Spack package manager, workspaces can also use the
``push-to-cache`` and ``mirror`` pipelines to cache compiled binaies, and
mirror software source.

The use of this package manager requires an external installation of Spack. For
instructions on installing Spack, see
`Spack's documentation <https://github.com/spack/spack#-spack>`_.


^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Spack Lightweight Package Manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Setting the package manager config option to ``spack-lightweight`` enables the
use of a lightweight version of `Spack <https://spack.io/>`_ for each
experiment. During the ``setup`` pipeline, Ramble will construct Spack
environments, however installation is deferred. This allows experiments to
install their own software, enabling parallel installation, rather than
requiring sequential installation at workspace setup time.

The :ref:`software configuration section <software-config>` is used to
determine what packages to install within the resulting environment.

When using the Spack package manager, workspaces can also use the
``push-to-cache`` and ``mirror`` pipelines to cache compiled binaies, and
mirror software source.

The use of this package manager requires an external installation of Spack. For
instructions on installing Spack, see
`Spack's documentation <https://github.com/spack/spack#-spack>`_.

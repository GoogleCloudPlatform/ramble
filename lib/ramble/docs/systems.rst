.. Copyright 2022-2026 Ramble a Series of LF projects, LLC

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.


.. _system-control:

=======
Systems
=======

Within Ramble's :ref:`variants configuration section <variants-config>`, users
can control which system is used for a set of experiments.

The system used can control many aspects of the experiment, and is
intended to broadly map to a cluster. Experiments in a workspace can
select different systems, and systems can apply default configurations for
several parts of the experiment. These include defining default variables,
selecting a default workflow manager or package manager, and limiting (or
selecting) the platform that an experiment can be used on.

-------------------
Configuring Systems
-------------------

Systems are controlled through a config option in the 
:ref:`variants configuration section <variants-config>`. The following shows an
example of controlling this

.. code-block:: yaml

  variants:
    system: <system_name>

The default system is ``user-managed`` which simply requires the user to
manually define aspects of the system used for validation in their workspace.
The value of the system variant used can be a reference to a variable, and will
be expanded following Ramble's :ref:`variable definitions
<variable-dictionaries>` logic.

-----------------
Supported Systems
-----------------

To begin with, the only supported system, provided with Ramble is below:

 * user-managed

^^^^^^^^^^^^^^^^^^^
User Managed System
^^^^^^^^^^^^^^^^^^^

The selection of ``user-managed`` for system will require users to specify the
``max_nodes`` variable, telling Ramble how many nodes are available of the
underlying platform.

Additionally, users have another default variant ``validate_system`` that is set
to True by default to validate aspects of the system. Users can disable this by
setting the variant to False explicitly.

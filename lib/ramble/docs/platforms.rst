.. Copyright 2022-2026 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.


.. _platform-control:

=========
Platforms
=========

Within Ramble's :ref:`variants configuration section <variants-config>`, users
can control which platform is used for a set of experiments.

The platform used can control many aspects of the experiment, and is intended
to broadly map to a physical compute node. Experiments in a workspace can
select different platforms, and platforms can apply default configurations for
several parts of the experiment. These include, but are not limited to,
defining default variables that are strongly coupled to the underlying platform
choice.

---------------------
Configuring Platforms
---------------------

Platforms are controlled through a config option in the 
:ref:`variants configuration section <variants-config>`. The following shows an
example of controlling this

.. code-block:: yaml

  variants:
    platform: <platform_name>

The default platform is ``user-managed`` which simply requires the user to
manually define aspects of the platform used for validation in their workspace.
The value of the platform variant used can be a reference to a variable, and will
be expanded following Ramble's :ref:`variable definitions
<variable-dictionaries>` logic.

-------------------
Supported Platforms
-------------------

To begin with, the only supported platform, provided with Ramble is below:

 * user-managed

^^^^^^^^^^^^^^^^^^^^^
User Managed Platform
^^^^^^^^^^^^^^^^^^^^^

The selection of ``user-managed`` for system will require users to specify the
following variables:

 * ``max_accelerators_per_node`` - The number of accelerators on each node of this platform
 * ``max_sockets_per_node`` - The number of sockets on each node of this platform
 * ``max_threads_per_core`` - The number of threads on each core of this platform
 * ``max_cores_per_node`` - The number of cores on each node of this platform
 * ``max_memory_per_node`` - The amount of memory on each node of this platform in GB

Additionally, users have another default variant ``validate_platform`` that is set
to True by default to validate aspects of the platform. Users can disable this by
setting the variant to False explicitly. Disabling validation will cause most
of the previously listed to not be required any more.

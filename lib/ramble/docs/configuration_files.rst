.. Copyright 2022-2024 Google LLC

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

===================
Configuration Files
===================

Ramble supports several different configuration files to control its behavior.
Some of these apply changes to Ramble's internals, while some modify the
experiments ramble generates.

This document describes each config section and its purpose. This document
does not cover the :ref:`workspace configuration file<workspace-config>`, which has its own document.

Ramble's configuration logic closely follows
`Spack's configuration logic <https://spack.readthedocs.io/en/latest/configuration.html>`.

-----------------------
Configuration Sections:
-----------------------

Currently, Ramble supports the following configuration sections:

* :ref:`applications <application-config>`
* :ref:`config <config-yaml>`
* :ref:`env_vars <env-vars-config>`
* :ref:`formatted_executables <formatted-execs-config>`
* :ref:`internals <internals-config>`
* :ref:`licenses <licenses-config>`
* :ref:`mirrors <mirrors-config>`
* :ref:`modifier_repos <modifier-repos-config>`
* :ref:`modifiers <modifiers-config>`
* :ref:`repos <repos-config>`
* :ref:`spack <spack-config>`
* :ref:`success_criteria <success-criteria-config>`
* :ref:`variables <variables-config>`

Each of these config sections has a defined schema contained in
``lib/ramble/ramble/schemas``.


.. _configuration_scopes:

--------------------
Configuration Scopes
--------------------

Ramble provides several configuration scopes, which are used to denote
precedence of configuration options. In precedence order (from lowest to
highest) Ramble contains the following scopes:

(1) **default**: Stored in ``$(prefix)/etc/ramble/defaults/``. These are the
default settings provided with Ramble. Users should generally not modify these
settings, and instead use a higher precedence configuration scope. These
defaults will change from version to version of Ramble.
(2) **system**: Store in ``/etc/ramble/``. These are Ramble settings for an
entire machine. These settings are typically managed by a systems
administrator, or something with root access on the machine. Settings defined
in this scope override settings in the **default** scope.
(3) **site**: Stored in ``$(prefix)/etc/ramble/``. Settings here only affect
*this instance* of Ramble, and they override both the **default** and
**system** scopes.
(4) **user**: Stored in ``~/.ramble/``. Settings here only affect a specific
user, and override **default**, **system**, and **site** scopes.
(5) **custom**: Stored in a custom directory, specified by ``--config-scope``.
If multiple scopes are listed on the command line, they are ordered from lowest
to highest precedence. Settings here override all previously defined scoped.
(6) **workspace configs dir**: Stored in ``$(workspace_root)/configs``
generally as a ``<config_section>.yaml`` file (i.e. ``variables.yaml``). These
settings apply to a specific workspace, and override all previous configuration
scopes.
(7) **workspace configuration file**: Stored in
``$(workspace_root)/configs/ramble.yaml``. Configuration scopes defined within
this config file override all previously defined configuration scopes.
(8) **command line**: Configuration options defined on the command line take
precedence over all other scopes.

Each configuration directory may contain several configuration files, such as
``config.yaml``, ``variables.yaml``, or ``modifiers.yaml``. When configurations
conflict, settings from higher-precedence (higher number in the above list)
scopes override lower-precedence settings.

In order to determine what settings will be used in a given context:

.. code-block:: console

    $ ramble config blame <section>

Will provide a listing of the configuration options within a given
configuration section, and where the setting is being derived from. Issuing
this command with an active workspace will include configuration sections
defined within a workspace scope.

Ramble's merging logic closely follows `Spack's configuration scope logic
<https://spack.readthedocs.io/en/latest/configuration.html#configuration-scopes>`.

.. _application-config:

--------------------
Application Section:
--------------------

The application configuration section is used to define the experiments a
workspace should generate. The general format for this config section is as follows:

.. code-block:: yaml

    applications:
      <application_name>:
        [optional_definitions]:
        workloads:
          <workload_name>:
            [optional_definitions]:
            experiments:
              <experiment_name>:
                [optional_definitions]:
                variables: {}
                [matrix]:
                [matrices]:


In the above ``[optional_definitions]`` can include any of:

* :ref:`env_vars <env-vars-config>`
* :ref:`internals <internals-config>`
* :ref:`modifiers <modifiers-config>`
* :ref:`success_criteria <success-criteria-config>`
* :ref:`variables <variables-config>`

Each of these will be described in their own section below.

Within an experiment, each portion of ``[optional_definitions]`` will be merged
together, with the order of precedence (from lowest to highest) being:

* application
* workload
* experiment

.. _config-yaml:

---------------
Config Section
---------------

The config configuration section is used to control internal aspects of Ramble.
The current default configuration is as follows:

.. code-block:: yaml

    config:
      shell: ''
      spack:
        install:
          flags: '--reuse'
        concretize:
          flags: '--reuse'
        buildcache:
          flags: ''
        env_create:
          flags: ''
        global
          flags: ''
      input_cache: '$ramble/var/ramble/cache'
      workspace_dirs: '$ramble/var/ramble/workspaces'
      upload:
        type: 'BigQuery'
        uri: ''

.. _upload-config-option:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Upload
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ramble aims to support the upload of experiment outcomes (including FOMs), to
SQL-like datastores. To do this we can specify an ``upload:type`` as defined by
:mod:`ramble.experimental.uploader.Upload`, and a ``upload:uri`` to specify the
destination.

As part of the upload it tries to attribute the data to a user. This can be
specified via ``config:user``, or if blank ramble will try deduce it based on
the calling user.


.. _disable-passthrough-config-option:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Disable Passthrough
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

An optional flag can be set in ``config`` or with ``--disable-passthrough``
on the command line to disable expansion passthrough. Its format is as follows:

.. code-block:: yaml

    config:
      disable_passthrough: True

Expansion passthrough allows variables that don't expand completely to pass
through and not cause an error. This is useful for things like `${ENV_VAR}` 
that are recognized as a variable. When passthrough is disabled, any variables
that fail to expand will raise a syntax error, which can aid in debugging.

.. _experiment-repeats-config-option:

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Experiment Repeats
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The repeats config options within the ``config`` section are used to define a number
of times each experiment will be repeated. Summary statistics will be calculated for
the set of repeats. Its format is as follows:

.. code-block:: yaml

    config:
      n_repeats: 'int'
      repeats_success_strict: [True/False]

By default, a set of repeats is successful if all individual repeats are successful.
When ``repeats_success_strict`` is set to false, the set will be considered successful
if any repeat succeeds, and statistics will be calculated over the successful experiments
only.

More information on using repeats within a workspace can be found in the
:ref:`workspace configuration file<workspace-config>`.

.. _env-vars-config:

------------------------------
Environment Variables Section:
------------------------------

The environment variables config section is named ``env_vars`` and controls
what environment variable modifications ramble should inject into experiments.

The format of this config section is as follows:

.. code-block:: yaml

    env_vars:
      set:
        var_name: var_value
      append:
      - var-separator: ','
        vars:
          var_to_append: val_to_append
        paths:
          path_to_append: val_to_append
      prepend:
      - paths:
          path_to_prepend: val_to_prepend
      unset:
      - var_to_unset


The above example is general, and intended to show the available functionality
of configuring environment variables. Below the ``env_vars`` level, one of four
actions is available. These actions are:
* ``set`` - Define a variable equal to a given value. Overwrites previously configured values
* ``append`` - Append the given value to the end of a previous variable definition. Delimited for vars is defined by ``var_separator``, ``paths`` uses ``:``
* ``prepend`` - Prepent the given value to the beginning of a previous variable definition. Only supports paths, delimiter is ``:``
* ``unset`` - Remove a variable definition, if it is set.

.. _formatted-execs-config:

------------------------------
Formatted Executables Section:
------------------------------

The formatted executables config section is named ``formatted_executables`` and
controls the creation of variables that represent the complete list of
executables an experiment needs to execute.

The format of this config section is as follows:

.. code-block:: yaml

  formatted_executables:
    new_command:
      indentation: 8
      prefix: '- '
      join_separator: '\n'


The above example defines a new variable named ``new_command`` which will be a
new-line (``\n``) demlimited list of executables, where each executable is
prefixed with ``- `` and is indented 8 space characters.

The default configuration files define one formatted executable named
``command``. Its definition can be seen with:

.. code-block:: console

  $ ramble config get formatted_executables

.. _internals-config:

------------------
Internals Section:
------------------

The internals config section is used to modify internal aspects of an
application definition when creating experiments.

**NOTE:** This section is intended as more of an advanced user section, and can
easily break aspects of the experiment if used incorrectly.

The format of the internals config section is as follows:

.. code-block:: yaml

    internals:
      custom_executables:
        <executable_name>:
          template: [list, of, commands, for, template]
          use_mpi: [True/False] # Default: False
          redirect: 'where_to_redirect_output' # Default '{log_file}'
          output_capture: 'operator_to_use_for_redirection' # Default >>
      executables:
      - list of
      - executables
      - to use in
      - experiments
      executable_injection:
      - name: <executable_name>
        order: 'before' / 'after' # Default: 'after'
        [relative_to: <relative_executable_name>]

Currently this section has two sub-sections.

The ``custom_executables`` sub-section can be used to define new executables
that an experiment should use. It can also be used to override the definition
of an internally defined executable within an experiment.

The ``executables`` sub-section can be used to control the order executables
will be used in the experiment. This is also the mechanism to inject custom
executables into an experiment.

The ``executable_injection`` sub-section can be used to inject custom
executables into the list of executables an experiment would use without having
to define the entire list. The ``name`` attribute should be set to the name of
an executable. This can be either a custom executable (defined in
``custom_executables``) or an existing executable (including a ``builtin``).
The ``order`` attrbite can be set to either ``before`` or ``after`` with
``after`` being the default value if it is not specified. The ``relative_to``
attribute can be set to the name of an executable already in the list of
experiment executables (including custom executables that are already injected).

Processing the ``executable_injection`` sub-section occurs after processing the
``executables`` sub-section. Executables are injected in the order they are
listed in the YAML file, with lower precedence scopes being processed first.
(e.g. ``workspace`` executables are injected before ``experiment`` executables
are).

.. _licenses-config:

-----------------
Licenses Section:
-----------------

The licenses config section is used to configure license environment variables
to applications. Its format is as follows:

.. code-block:: yaml

    licenses:
      <application_name>:
        set:
          var_to_set: 'VALUE'
        append:
        - var-separator: ','
          vars:
            var_to_append: 'VALUE'
        - paths:
            path_to_append: 'VALUE'
        prepend:
        - paths:
            path_to_prepend: 'VALUE'
        unset:
        - var_to_unset


Ramble will automatically inject these environment variable modifications into
experiments that use the application defined by ``<application_name>``.

.. _mirrors-config:

----------------
Mirrors Section:
----------------

The mirrors config section is used to control alternative locations Ramble
should download input files from. Mirros are checked before the default URL for
an input file. The format of the mirrors section is as follows:


.. code-block:: yaml

    mirrors:
      <mirror1_name>: 'url'
      <mirror2_name>:
        fetch: 'fetch_url'
        push: 'push_url'


.. _modifier-repos-config:

-----------------------
Modifier Repos Section:
-----------------------

The modifier repos config section is used to control which repositories should
be searched for when looking for modifiers. Its format is as follows:

.. code-block:: yaml

    modifier_repos:
    - 'path/to/repo'


.. _modifiers-config:

------------------
Modifiers Section:
------------------

The modifiers config section is used to control which modifiers will be used on
experiments ramble generates. Its format is as follows:

.. code-block:: yaml

    modifiers:
    - name: <modifier_name>
      mode: <mode_for_modifier> # Optional if modifier only has one mode or if default_mode is set
      on_executable: # Defaults to '*', follows glob syntax
      - list of
      - executables to apply
      - modifier to


.. _repos-config:

--------------
Repos Section:
--------------

The repos config section is used to control which repositories should
be searched for when looking for application definitions. Its format is as follows:

.. code-block:: yaml

    repos:
    - 'path/to/repo'


.. _spack-config:

--------------
Spack Section:
--------------

The spack config section is used to define package definitions, and software
environments created from those packages. Its format is as follows:

.. code-block:: yaml

    spack:
      concretized: [True/False] # Should be false unless defined in a concretized workspace
      [variables: {}]
      packages:
        <package_name>:
          spack_spec: 'spack_spec_for_package'
          compiler_spec: 'Compiler spec, if different from spack_spec' # Default: None
          compiler: 'package_name_to_use_as_compiler' # Default: None
          [variables: {}]
          [matrix:]
          [matrices:]
      environments:
        <environment_name>:
          packages:
          - list of
          - packages in
          - environment
          [variables: {}]
          [matrix:]
          [matrices:]
        <external_env_name>:
          external_spack_env: 'name_or_path_to_spack_env'

The packages dictionary houses ramble descriptions of spack packages that can
be used to construct environments with. A package is defined as software that
spack should install for the user. These have one required attribute, and two
optional attributes. The ``spack_spec`` attribute is required to be defined,
and should be the spec passed to ``spack install`` on the command line for the
package. Optionally, a package can define a ``compiler_spec`` attribute, which
will be the spec used when this package is used as a compiler for another
package. Packages can also optionally define a ``compiler`` attribute, which
is the name of another package that should be used as it's compiler.

The environments dictionary contains descriptions of spack environments that
Ramble might generate based on the requested experiments. Environments are
defined as a list of packages (in the aforementioned packages dictionary) that
should be bundled into a spack environment.

Below is an annotated example of the spack dictionary.

.. code-block:: yaml

    spack:
      packages:
        gcc9: # Abstract name to refer to this package
          spack_spec: gcc@9.3.0 target=x86_64 # Spack spec for this package
          compiler_spec: gcc@9.3.0 # Spack compiler spec for this package
        impi2018:
          spack_spec: intel-mpi@2018.4.274 target=x86_64
          compiler: gcc9 # Other package name to use as compiler for this package
        gromacs:
          spack_spec: gromacs@2022.4
          compiler: gcc9
      environments:
        gromacs:
          packages: # List of packages to include in this environment
          - impi2018
          - gromacs

Packages and environments defined inside the ``spack`` config section are
merely templates. They will be rendered into explicit environments and packages
by each individual experiment.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
External Spack Environment Support:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**NOTE**: Using external Spack environments is an advanced feature.

Some experiments will want to use an externally defined Spack environment
instead of having Ramble generate its own Spack environment file. This can be
useful when the Spack environment a user wants to experiment with is
complicated.

This section shows how this feature can be used.

.. code-block:: yaml

    spack:
      environments:
        gromacs:
          external_spack_env: name_or_path_to_spack_env

In the above example, the ``external_spack_env`` keyword refers an external
Spack environment. This can be the name of a named Spack environment, or the
path to a directory which contains a Spack environment. Ramble will copy the
``spack.yaml`` file from this environment, instead of generating its own.

This allows users to describe custom Spack environments and allow them to be
used with Ramble generated experiments.

It is important to note that Ramble copies in the external environment files
every time ``ramble workspace setup`` is called. The new files will clobber the
old files, changing the configuration of the environment that Ramble will use
for the experiments it generates.


.. _success-criteria-config:

-------------------------
Success Criteria Section:
-------------------------

The success criteria section is used to control what criteria experiment should
use when determining if they were successful or not. Its format is as follows:

.. code-block:: yaml

    success_criteria:
    - name: 'criteria_name'
      mode: 'criteria_mode' # i.e. 'string' for string matching
      match: 'regex_for_matching'
      file: 'file_criteria_should_be_found_in'


For more information about using success criteria, see the
:ref:`success criteria documentation<success-criteria>`.


.. _variables-config:

------------------
Variables Section:
------------------

The variables config section is used to define variables within ramble
experiments. These variables are used in several places within Ramble. Its
format is as follows:

.. code-block:: yaml

    variables:
      var_name: 'var_value'
      list_var_name: ['val1', 'val2']
      cross_reference_var: 'var in <app>.<workload>.<exp>'

Variables can be defined as lists, scalars, or can refer to a variable defined in
another fully qualified experiment (through the ``cross_ref_var`` syntax).

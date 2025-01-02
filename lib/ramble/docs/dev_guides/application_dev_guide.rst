.. Copyright 2022-2025 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

.. _application-dev-guide:

=======================================
Application Definition Developers Guide
=======================================


Application definition files represent building blocks to create experiments
from. They are intended to be portable, and as a result should not contain any
system specific logic. Each definition is a python module, with a specifically
named python class contained inside. The python class can be written with
provided directives, or can optionally override internal functions for more
advanced behavior.

This gudie will provide general steps for creating a new application definition file.

-----------
Preparation
-----------

To begin, it can be useful to prepare a few things about the application you
are writing a definition file for. These include:

#. Instructions for compiling / installing your application
#. A set of input files you would like to create workloads for
#. A working set of execution commands
#. Information about the output from the application

Most of these steps require some research, or up front exploration of the
application, but are incredibly helpful in lowering the effort required to
write an application definition file.

Below we will provide some basics of how to get started with these steps.
However, this guide will not provide exhaustive information for all
applications. So, in general, this step is left to you to complete.

.. _application-definition-compilation:

^^^^^^^^^^^^^^^^^^^^^^^^^^
Compilation / Installation
^^^^^^^^^^^^^^^^^^^^^^^^^^

Ramble has first party support for some package managers. The provided package
managers can be seen through the ``ramble list --type package_managers``
command. To improve provenance information that Ramble is able to track, we
strongly recommend using a supported package manager.

You have three options at this stage. The first (and arguably more complicated)
option is to add support for a new package manager, if your application is not
included in any of the supported package manager yet. The second is to add your
application to one of the supported package managers. The third and final
option is to manually install your application and use the default setting for
a package manager which disables package manager support.

This might include writing a definition file for the targeted package manager.
This guide will not walk you through this process, however the actual steps
vary dramatically from one package manager to another.  Spack has
`documentation to help write package definition files <https://spack.readthedocs.io/en/latest/packaging_guide.html>`_.

.. _experiment-input-files:

^^^^^^^^^^^^^^^^^
Collecting Inputs
^^^^^^^^^^^^^^^^^

Some, but not all, applications will require input files. They may require
multiple input files per experiment, or a single input file for each
experiment. Applications can also have a wide range of input files, that each
represent different workloads.

In Ramble, a workload can have an arbitrary number of input files. Before
writing an application definition file, it is useful to collect, and organize
the application's input files based on the workloads you want to create. This
might only involve collecting URLs and SHA256 checksums for the input files.

.. _example-execution:

^^^^^^^^^^^^^^^^^
Testing Execution
^^^^^^^^^^^^^^^^^

Since an application definition file will be used to generate experiments, it
is necessary to understand how to execute an experiment with the application.
For this step, it can be useful to manually test the application with a set of
input files for a specific workload.

.. _collect-output:

^^^^^^^^^^^^^^^^^^
Output Information
^^^^^^^^^^^^^^^^^^

As a manual execution is recommended, once a successful test has been
performed, it can be useful to retain the output of the application. Examining
this output, you can determine what figures of merit might be useful to extract
from the application output.

However, this step can be performed after experiments are functional from the
application definition file as well.

-------------------------------
Application Definition Creation
-------------------------------

Application definition files are stored within object repositories. These
repositories generally store all applications within a directory named
``applications``, however each repository can control this through their own
config file ( ``repo.yaml`` ).

Within the repository, each application definition file is a python module that
is stored within a directory named for the application. As an example, Ramble
comes with a repository named ``builtin``. This repository contains several
standard application definitions that are provided to the community. One of the
application definition files provided is
`HPL <https://github.com/GoogleCloudPlatform/ramble/tree/develop/var/ramble/repos/builtin/applications/hpl>`_.
The HPL application definition file is named ``application.py`` and is stored
within a directory named ``hpl``. Within the ``application.py`` file, a python
class is defined with a similar name to the application directory. Ramble's
application definition naming syntax follows
`Spack's package naming rules <https://spack.readthedocs.io/en/latest/packaging_guide.html#naming-directory-structure>`_.

^^^^^^^^^^^^
Base Classes
^^^^^^^^^^^^

Ramble provides base classes which can be inherited from when creating new
application definition files. Currently, these are used to abstract the package
manager logic, but more generally change the behavior of the underlying
application definitions. These can be seen in more detail in
:mod:`ramble.application_types`.

New application definitions can also inherit their behavior from other
application classes to replicate aspects of their behavior.

Existing application classes can be referenced using the:
``from ramble.app.builtin.<application_name> import <application_class>`` syntax.

---------------------------------
Writing an application definition
---------------------------------

After an application's ``application.py`` file is created, Ramble's language
features can be used to fill out the application definition. These language
features provide directives which define specific portions of the application's
functionality. This guide will introduce some of the basic language features to
create functional application definition files, but will not be exhaustive. For
an exhaustive list of application language features, see
:mod:`ramble.language`.

The directives from Ramble's application language are placed alongside class
variables, as in:

.. code-block:: python

    class Hpl(ExecutableApplication):
        executable(....)
        executable(....)
        input_file(....)
        input_file(....)
        workload(....)


^^^^^^^^^^^
Executables
^^^^^^^^^^^

A named executable in Ramble is one or more commands that should be executed
together within an experiment. Ramble contains a directive for defining named
executables :py:meth:`ramble.language.application_language.executable`

Having performed a test execution in :ref:`example-execution`, you should be
able to transcribe the execution commands into ``executable`` statements.

It is important to make sure every step needed to go from a vanilla input file
to performing an experiment is captured in named executables though.

^^^^^^^^^^^
Input Files
^^^^^^^^^^^

A named input file in Ramble describes a URL, a SHA256 checksum, and some
additional information about a file that a workload will require for its
experiments. The ``input_file`` directive 
(:py:meth:`ramble.language.application_language.input_file`) can be used to
define a named input file in an application definition file.

After collecting the input files needed for the workloads you are defining (as
in :ref:`experiment-input-files`), each input file can be written as its own
``input_file`` directive.

^^^^^^^^^
Workloads
^^^^^^^^^

Having used ``executable`` and ``input_file`` directives, these can now be
pieced together into a workload, using the ``workload`` directive
(:py:meth:`ramble.language.application_language.workload`).

The ``workload`` directive is used to define a named workload from which
experiments can be generated. A workload in Ramble is defined as the pairing of
one or more named executables with zero or more named input files. Defining a
workload in an ``application.py`` allows it to be used within a
:ref:`workspace-config` and will be shown when executing ``ramble info <app>``
on the named application.

^^^^^^^^^^^^^^^^^^
Workload Variables
^^^^^^^^^^^^^^^^^^

While a workload by itself can generate an experiment, sometimes a variable
should be exposed that can allow a parameter study or help abstract the
definition of the workload (such as executable commands). Each workload can
have an arbitrary number of workload variables, defined by
:py:meth:`ramble.language.application_language.workload_variable`.

Each variable has a default value, which can be override within a
:ref:`workspace-config`.

^^^^^^^^^^^^^^^^
Success Criteria
^^^^^^^^^^^^^^^^

Success criteria help Ramble identify if an experiment was executed
successfully or not. This information is extracted when ``ramble workspace
analyze`` is executed to help convey if the extract figures of merti should be
considered valid or not.

Applications can define any number of named success criteria, using
:py:meth:`ramble.language.shared_language.success_criteria`. For an experiment
to be considered successful, all of its success criteria must resolve to
``True``.

The simplest success criteria is a basic string match that requires a specific
string show up in an experiment's output file. More complex success criteria
can also be written (including defining an ``evaluate_success`` function within
the application definition file).

^^^^^^^^^^^^^^^^
Figures Of Merit
^^^^^^^^^^^^^^^^

Named figures of merit represent quantities that ramble should extract from an
experiment. They are allowed to relate to any metric of interest, whether it is
a physical quantity (such as total mass or energy), or a performance quantity
(such as wallclock time), or some other application output.

Each figure of merit is defined by
:py:meth:`ramble.language.shared_language.figure_of_merit` and contains
information about where the metric can be found, what the units of the metric
are, and how to extract it from a given output file.

^^^^^^^^^^^^^^^^^^^^^^^^
Figure Of Merit Contexts
^^^^^^^^^^^^^^^^^^^^^^^^

Sometimes, a figure of merit needs additional information (such as what
timestep it was collected from). To augment a figure of merit with this
additional information, Ramble has the ability to define a figure of merit
context. Each context represents a grouping of figures of merit that are
collected together. A figure of merit context can be defined using
:py:meth:`ramble.language.shared_language.figure_of_merit_context`.

^^^^^^^^^^^^^^^^^^
File path handling
^^^^^^^^^^^^^^^^^^

Ramble provides a utility function :py:meth:`ramble.util.file_util.get_file_path`
that should be used when referencing file paths in application definitions. This
helps with Ramble to properly mock out these paths during unit testing, where the
files may not exist under the dry-run setting.

--------------------------
Package Manager Directives
--------------------------

Each package manager will be its own base class, but additionally there are
directives that are intended to be package manager specific. As an example,
there are directives for Spack defined by:

* :meth:`ramble.language.shared_language.software_spec`
* :meth:`ramble.language.shared_language.define_compiler`
* :meth:`ramble.language.shared_language.required_package`

These provide Ramble with information about how Spack could install and require
packages. For more information, see the above reference.

----------------------
Usage While Developing
----------------------

It can be useful to test an ``application.py`` while developing it, to make
sure it behaves as expected. This section will describe how you can interact
with the various parts of an application definition file. This section will
provide you with tips to help accelerate development and testing of an
application development file

^^^^^^^^^^^^^^^^^^^^^^
Generating Experiments
^^^^^^^^^^^^^^^^^^^^^^

The most useful part of an application definition file is the ability to
generate new experiments for its workloads. To do this, the application
definition needs to contain a complete definition of at least one workload.
This includes its executables, input files, and workload variables.

Once this is complete, a workspace can be configured (following
:ref:`workspace-config`) to create experiments from the new workload. After
setting up the workspace, requested experiments directories will be created
following :ref:`workspace-structure`. In order to debug any issues with the
experiments, you can use the dry-run option from :ref:`workspace-setup`.
Additionally, you can filter the experiments you want to setup using the
``--where`` option, as in :ref:`filter-experiments`

^^^^^^^^^^^^^^^^^
Analyzing Results
^^^^^^^^^^^^^^^^^

Experiment analysis only works once figures of merit, and success criteria are
defined. Without these, Ramble has no information about how to extract relevant
metrics.

Once an experiment can be executed using the ``application.py`` file, you can
analyze the experiment to extract all of the figures of merit. However, if you
have the output file from :ref:`collect-output`, you can copy it into one of
the experiment directories to allow analyze to extract the correct information
without having to execute the experiment.


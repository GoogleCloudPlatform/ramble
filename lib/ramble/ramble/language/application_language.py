# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.definitions.variables
import ramble.language.language_helpers
import ramble.language.shared_language
import ramble.workload
from ramble.language.language_base import DirectiveError

"""This package contains directives that can be used within an application.

Directives are functions that can be called inside an application
definition to modify then application, for example:

    .. code-block:: python

      class Gromacs(ExecutableApplication):
          # Workload directive:
          workload('water_bare', executables=['pre-process', 'execute-gen'],
               input='water_bare_hbonds')

In the above example, 'workload' is a ramble directive

There are many available directives, the majority of which are implemented here.

Some examples include:

  workload
  executable
  figure_of_merit
  figure_of_merit_context
  input_file

For a full list see below, or consult the existing application definitions for
examples

"""


class ApplicationMeta(ramble.language.shared_language.SharedMeta):
    _directive_names = set()
    _directives_to_be_executed = []


application_directive = ApplicationMeta.directive


@application_directive("workloads")
def workload(
    name,
    executables=None,
    executable=None,
    input=None,
    inputs=None,
    tags=None,
    when=None,
    **kwargs,
):
    """Adds a workload to this application

    Defines a new workload that can be used within the context of
    its application.

    Args:
        executable (str): The name of an executable to be used
        executables (str): A list of executable names to be used
        input (str): Optional, name of an input be used
        inputs (str): Optional, A list of input names that will be used

    One of executable, or executables is required as an input argument.
    """

    def _execute_workload(app):
        all_execs = ramble.language.language_helpers.require_definition(
            executable, executables, app.executables, "executable", "executables", "workload"
        )

        all_inputs = ramble.language.language_helpers.merge_definitions(
            input, inputs, app.inputs, "input", "inputs", "workload"
        )

        when_list = ramble.language.language_helpers.build_when_list(when, app, name, "workload")
        when_set = frozenset(when_list)
        if when_set not in app.workloads:
            app.workloads[when_set] = {}

        app.workloads[when_set][name] = ramble.workload.Workload(name, all_execs, all_inputs, tags)

    return _execute_workload


@application_directive("workload_groups")
def workload_group(name, workloads=None, mode=None, **kwargs):
    """Adds a workload group to this application

    Defines a new workload group that can be used within the context of its
    application.

    Args:
        name (str): The name of the group
        workloads (list(str) | None): A list of workloads to be grouped
    """
    if workloads is None:
        workloads = []

    def _execute_workload_groups(app):
        if mode == "append":
            app.workload_groups[name].update(set(workloads))
        else:
            app.workload_groups[name] = set(workloads)

        # Apply any existing variables in the group to the workload
        for workload in workloads:
            for when_set in app.workloads:
                if workload in app.workloads[when_set]:
                    if name in app.workload_group_vars:
                        for var in app.workload_group_vars[name]:
                            app.workloads[when_set][workload].add_variable(var)

                    if name in app.workload_group_env_vars:
                        for env_var in app.workload_group_env_vars[name]:
                            app.workloads[when_set][workload].add_environment_variable(env_var)

    return _execute_workload_groups


@application_directive("executables")
def executable(name, template, when=None, **kwargs):
    """Adds an executable to this application

    Defines a new executable that can be used to configure workloads and
    experiments with.

    Executables may or may not use MPI.

    Required Args:
        name (str): Name of the executable
        template (list[str] | str): The template command this executable should generate from

    Optional Args:
        use_mpi or mpi (bool): determines if this executable should be
                        wrapped with an `mpirun` like command or not.

        variables (dict): Dictionary of variable definitions to use for this
                          executable only
        redirect (str): Optional, sets the path for outputs to be written to.
                             defaults to {log_file}
        output_capture (str): Optional, Declare which output (stdout, stderr,
                              both) to capture. Defaults to stdout
        run_in_background (bool): Optional, Declare if the command should
                                     run in the background. Defaults to False
        when (list | None): List of when conditions to apply to directive
    """

    def _execute_executable(app):
        from ramble.util.executable import CommandExecutable

        when_list = ramble.language.language_helpers.build_when_list(when, app, name, "executable")
        when_set = frozenset(when_list)
        if when_set not in app.executables:
            app.executables[when_set] = {}

        app.executables[when_set][name] = CommandExecutable(name=name, template=template, **kwargs)

    return _execute_executable


@application_directive("inputs")
def input_file(
    name,
    url,
    description,
    target_dir="{workload_input_dir}",
    sha256=None,
    extension=None,
    expand=True,
    when=None,
    **kwargs,
):
    """Adds an input file definition to this application

    Defines a new input file.
    An input file must define it's name, and a url where the input can be
    fetched from.

    Args:
        url (str): Path to the input file / archive
        description (str): Description of this input file
        target_dir (str): Optional, the directory where the archive will be
                               expanded. Defaults to the '{workload_input_dir}'
                               + os.sep + '{input_name}'
        sha256 (str): Optional, the expected sha256 checksum for the input file
        extension (str): Optiona, the extension to use for the input, if it isn't part of the
                              file name.
        expand (bool): Optional. Whether the input should be expanded or not. Defaults to True
        when (list | None): List of when conditions to apply to directive
    """

    def _execute_input_file(app):
        when_list = ramble.language.language_helpers.build_when_list(when, app, name, "input_file")
        when_set = frozenset(when_list)
        if when_set not in app.inputs:
            app.inputs[when_set] = {}

        app.inputs[when_set][name] = {
            "url": url,
            "description": description,
            "target_dir": target_dir,
            "sha256": sha256,
            "extension": extension,
            "expand": expand,
            "when": when_list,
        }

    return _execute_input_file


@application_directive("workload_group_vars")
def workload_variable(
    name,
    default,
    description,
    values=None,
    workload=None,
    workloads=None,
    workload_group=None,
    expandable: bool = True,
    track_used: bool = True,
    when=None,
    **kwargs,
):
    """Define a new variable to be used in experiments

    Defines a new variable that can be defined within the
    experiments.yaml config file, to control various aspects of
    an experiment.

    These are specific to each workload.

    Args:
        name (str): Name of variable to define
        default: Default value of variable definition
        description (str): Description of variable's purpose
        values (list): Optional list of suggested values for this variable
        workload (str): Single workload this variable is used in
        workloads (list): List of modes this variable is used in
        workload_group (str): Name of workload group this variable is used in
        expandable (bool): True if the variable should be expanded, False if not.
        track_used (bool): True if the variable should be tracked as used,
                           False if not. Can help with allowing lists without vectorizing
                           experiments.
        when (list | None): List of when conditions to apply to directive
    """

    def _execute_workload_variable(app):
        # Always apply passes workload/workloads
        all_workloads = ramble.language.language_helpers.merge_definitions(
            workload, workloads, app.workloads, "workload", "workloads", "workload_variable"
        )

        when_list = ramble.language.language_helpers.build_when_list(
            when, app, name, "workload_variable"
        )

        workload_var = ramble.definitions.variables.Variable(
            name,
            default=default,
            description=description,
            values=values,
            expandable=expandable,
            when=when_list,
            **kwargs,
        )

        for when_set, app_workloads in app.workloads.items():
            for wl_name in all_workloads:
                if wl_name in app_workloads:
                    app.workloads[when_set][wl_name].add_variable(workload_var.copy())

        if workload_group is not None:
            workload_group_list = app.workload_groups[workload_group]

            if workload_group not in app.workload_group_vars:
                app.workload_group_vars[workload_group] = []

            # Track which vars we add to, to allow us to re-apply during inheritance
            app.workload_group_vars[workload_group].append(workload_var.copy())

            for when_set, app_workloads in app.workloads.items():
                for wl_name in workload_group_list:
                    if wl_name in app_workloads:
                        # Apply the variable
                        app.workloads[when_set][wl_name].add_variable(workload_var.copy())

        if not all_workloads and workload_group is None:
            raise DirectiveError("A workload or workload group is required")

    return _execute_workload_variable


@application_directive(dicts=())
def license_name(name, **kwargs):
    """Add a new license name directive, to specify license name in a declarative way.

    Args:
        name (str): name to use during license lookup and propagation
    """

    def _execute_license_name(obj):
        license_from_base = getattr(obj, "license_names", [])

        # Here it is essential to copy, otherwise we might add to an empty list in the parent
        # It is important that we preserve order
        obj.license_names = list(dict.fromkeys(license_from_base + [name]))

    return _execute_license_name

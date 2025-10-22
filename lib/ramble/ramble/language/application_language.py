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
    default=None,
    description="",
    values=None,
    workload=None,
    workloads=None,
    workload_group=None,
    workload_defaults=None,
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
        workload_group (str): Name of workload group this variable is used in.
        workload_defaults (dict): Dictionary mapping workload names to default values.
                                  Mututally exclusive with workload, workloads, workload_group,
                                  and default.
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

        # If a workload map is passed, handle that.
        if workload_defaults:
            if any([workload, workloads, workload_group, default]):
                raise DirectiveError(
                    "workload_defaults cannot be used with workload, workloads, "
                    "workload_group, or default"
                )

            for wl_name, wl_default in workload_defaults.items():
                workload_var = ramble.definitions.variables.Variable(
                    name,
                    default=wl_default,
                    description=description or f"Default for {name} for {wl_name}",
                    values=values,
                    expandable=expandable,
                    when=when_list,
                    **kwargs,
                )
                for when_set, app_workloads in app.workloads.items():
                    if wl_name in app_workloads:
                        app.workloads[when_set][wl_name].add_variable(workload_var.copy())
            return

        # Handle the remainder of the workload_variable directive, if
        # workload_defaults was not passed
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


@application_directive("cleanups")
def cleanup(
    name,
    regex,
    directory=None,
    recurse=False,
    description="",
    pre=False,
    post=False,
    when=None,
    **kwargs,
):
    """Adds a cleanup operation to the application.

    This directive defines a cleanup step that removes files matching a
    regular expression from a specified directory.

    Args:
        name (str): Name of the cleanup operation.
        regex (str): Regex passed to `find` to match files and directories to be deleted.
        directory (str): The directory to perform the cleanup in. Defaults to {experiment_run_dir}.
        recurse (bool): Whether to search for files recursively in subdirectories.
        description (str): Description of the cleanup operation.
        pre (bool): Whether to run this cleanup before the main application execution.
        post (bool): Whether to run this cleanup after the main application execution.
        when (list | None): List of when conditions to apply to this directive.
    """

    def _define_cleanup(obj):
        if not pre and not post:
            raise ramble.language.language_base.DirectiveError(
                f"Cleanup directive '{name}' must set at least one of 'pre' or 'post' to True."
            )
        when_list = ramble.language.language_helpers.build_when_list(when, obj, name, "cleanup")
        when_set = frozenset(when_list)
        if when_set not in obj.cleanups:
            obj.cleanups[when_set] = {}

        obj.cleanups[when_set][name] = {
            "description": description,
            "regex": regex,
            "directory": directory,
            "recurse": recurse,
            "pre": pre,
            "post": post,
            "when": when_list,
        }

    return _define_cleanup


@application_directive("executables")
def stage_files(
    src,
    dst,
    name=None,
    when=None,
    **kwargs,
):
    """Adds an executable that stages an input file or directory.

    Defines a new executable that copies or links a file or directory
    from a source to a destination. This is useful for staging input
    files that are not managed by the `input_file` directive.

    The staging method is controlled by the `stage_method` configuration
    option, which can be set to 'cp', 'rsync', 'symbolic_link', or 'hard_link'.

    Args:
        src (str): The source path of the file or directory.
        dst (str): The destination path.
        name (str | None): The name of the executable. Defaults to 'stage-files'.
        when (list | None): List of when conditions to apply to this directive.
    """

    def _execute_stage_files(app):
        import os

        import ramble.config
        from ramble.util.executable import CommandExecutable

        cfg = ramble.config.config
        stage_method = cfg.get("config", {}).get("stage_method", "cp")

        exec_name = name if name else "stage-files"

        when_list = ramble.language.language_helpers.build_when_list(
            when, app, exec_name, "stage_files"
        )
        when_set = frozenset(when_list)
        if when_set not in app.executables:
            app.executables[when_set] = {}

        if (
            exec_name in app.executables[when_set]
            and not app.executables[when_set][exec_name].allow_extension
        ):
            raise DirectiveError(
                f"stage_files directive on application {app.name} is creating "
                f"has name attribute of '{exec_name}' which already exists "
                "as an executable. Please provide a unique name attribute."
            )

        # Prepare the core staging command
        if stage_method == "rsync":
            stage_cmd = f"rsync -r {src} {dst}"
        elif stage_method == "hard_link":
            stage_cmd = f"ln {src} {dst}"
        elif stage_method == "symbolic_link":
            stage_cmd = f"ln -s {src} {dst}"
        else:  # stage_method == "cp"
            stage_cmd = f"cp -r {src} {dst}"

        template = [stage_cmd]

        # Prepend mkdir if dst has a parent directory
        parent_dir = os.path.dirname(dst)
        if parent_dir and parent_dir != ".":
            template.insert(0, f"mkdir -p {parent_dir}")

        if exec_name in app.executables[when_set]:
            app.executables[when_set][exec_name].add_template(template)
        else:
            app.executables[when_set][exec_name] = CommandExecutable(
                name=exec_name, template=template, allow_extension=True, **kwargs
            )

    return _execute_stage_files

# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import ramble.language.language_base
import ramble.language.language_helpers
import ramble.success_criteria
from ramble.util.logger import logger
from ramble.util.foms import FomType


"""This module contains directives directives that are shared between multiple object types

Directives are functions that can be called inside an object
definition to modify the object, for example:

    .. code-block:: python

      class Gromacs(ExecutableApplication):
          # Required package directive
          required_package("gromacs", package_manager="spack")

In the above example, "required_package" is a ramble directive

Directives defined in this module are used by multiple object types, which
inherit from the SharedMeta class.
"""


class SharedMeta(ramble.language.language_base.DirectiveMeta):
    _directive_names = set()
    _directives_to_be_executed = []


# shared_directive = ramble.language.language_base.DirectiveMeta.directive
shared_directive = SharedMeta.directive


@shared_directive("archive_patterns")
def archive_pattern(pattern):
    """Adds a file pattern to be archived in addition to figure of merit logs

    Defines a new file pattern that will be archived during workspace archival.
    Archival will only happen for files that match the pattern when archival
    is being performed.

    Args:
      pattern (str): Pattern that refers to files to archive
    """

    def _execute_archive_pattern(obj):
        obj.archive_patterns[pattern] = pattern

    return _execute_archive_pattern


@shared_directive("figure_of_merit_contexts")
def figure_of_merit_context(name, regex, output_format):
    """Defines a context for figures of merit

    Defines a new context to contain figures of merit.

    Args:
      name (str): High level name of the context. Can be referred to in
                  the figure of merit
      regex (str): Regular expression, using group names, to match a context.
      output_format (str): String, using python keywords {group_name} to extract
                           group names from context regular expression.
    """

    def _execute_figure_of_merit_context(obj):
        obj.figure_of_merit_contexts[name] = {"regex": regex, "output_format": output_format}

    return _execute_figure_of_merit_context


@shared_directive("figures_of_merit")
def figure_of_merit(
    name,
    fom_regex,
    group_name,
    log_file="{log_file}",
    units="",
    contexts=[],
    fom_type: FomType = FomType.UNDEFINED,
):
    """Adds a figure of merit to track for this object

    Defines a new figure of merit.

    Args:
      name (str): High level name of the figure of merit
      log_file (str): File the figure of merit can be extracted from
      fom_regex (str): A regular expression using named groups to extract the FOM
      group_name (str): The name of the group that the FOM should be pulled from
      units (str): The units associated with the FOM
      contexts (list(str)): List of contexts (defined by
                            figure_of_merit_context) this figure of merit
                            should exist in.
      fom_type: The type of figure of merit
    """

    def _execute_figure_of_merit(obj):
        obj.figures_of_merit[name] = {
            "log_file": log_file,
            "regex": fom_regex,
            "group_name": group_name,
            "units": units,
            "contexts": contexts,
            "fom_type": fom_type,
        }

    return _execute_figure_of_merit


@shared_directive("compilers")
def define_compiler(name, pkg_spec, compiler_spec=None, compiler=None, package_manager="*"):
    """Defines the compiler that will be used with this object

    Adds a new compiler spec to this object. Software specs should
    reference a compiler that has been added.

    Args:
        name (str): Name of compiler package
        pkg_spec (str): Package spec to install compiler
        compiler_spec (str): Compiler spec (if different from pkg_spec)
        compiler (str): Package name to use for compilation
        package_manager (str): Glob supported pattern to match package managers
                               this compiler applies to
    """

    def _execute_define_compiler(obj):
        obj.compilers[name] = {
            "pkg_spec": pkg_spec,
            "compiler_spec": compiler_spec,
            "compiler": compiler,
            "package_manager": package_manager,
        }

    return _execute_define_compiler


@shared_directive("software_specs")
def software_spec(name, pkg_spec, compiler_spec=None, compiler=None, package_manager="*"):
    """Defines a new software spec needed for this object.

    Adds a new software spec (for spack to use) that this object
    needs to execute properly.

    Only adds specs to object that use spack.

    Specs can be described as an mpi spec, which means they
    will depend on the MPI library within the resulting spack
    environment.

    Args:
        name (str): Name of package
        pkg_spec (str): Package spec to install package
        compiler_spec (str): Spec to use if this package will be used as a
                             compiler for another package
        compiler (str): Package name to use as compiler for compiling this package
        package_manager (str): Glob supported pattern to match package managers
                               this package applies to
    """

    def _execute_software_spec(obj):
        # Define the spec
        obj.software_specs[name] = {
            "pkg_spec": pkg_spec,
            "compiler_spec": compiler_spec,
            "compiler": compiler,
            "package_manager": package_manager,
        }

    return _execute_software_spec


@shared_directive("package_manager_configs")
def package_manager_config(name, config, package_manager="*", **kwargs):
    """Defines a config option to set within a package manager

    Define a new config which will be passed to a package manager. The
    resulting experiment instance will pass the config to the package manager,
    which will control the logic of applying it.

    Args:
        name (str): Name of this configuration
        config (str): Configuration option to set
        package_manager (str): Name of the package manager this config should be used with
    """

    def _execute_package_manager_config(obj):
        obj.package_manager_configs[name] = {
            "config": config,
            "package_manager": package_manager,
        }

    return _execute_package_manager_config


@shared_directive("required_packages")
def required_package(name, package_manager="*"):
    """Defines a new spack package that is required for this object
    to function properly.

    Args:
        name (str): Name of required package
        package_manager (str): Glob package manager name to apply this required package to
    """

    def _execute_required_package(obj):
        obj.required_packages[name] = {
            "package_manager": package_manager,
        }

    return _execute_required_package


@shared_directive("success_criteria")
def success_criteria(
    name,
    mode,
    match=None,
    file="{log_file}",
    fom_name=None,
    fom_context="null",
    formula=None,
    anti_match=None,
):
    """Defines a success criteria used by experiments of this object

    Adds a new success criteria to this object definition.

    These will be checked during the analyze step to see if a job exited properly.

    Args:
      name (str): The name of this success criteria
      mode (str): The type of success criteria that will be validated
                  Valid values are: 'string', 'application_function', and 'fom_comparison'
      match (str): For mode='string'. Value to check indicate success (if found, it
                   would mark success)
      file (str): For mode='string'. File success criteria should be located in
      fom_name (str): For mode='fom_comparison'. Name of fom for a criteria.
                      Accepts globbing.
      fom_context (str): For mode='fom_comparison'. Context the fom is contained
                         in. Accepts globbing.
      formula (str): For mode='fom_comparison'. Formula to use to evaluate success.
                     '{value}' keyword is set as the value of the FOM.
      anti_match (str): For mode='string'. Value to check indicate failure.
                        This setting and `match` are mutually exclusive.
    """

    def _execute_success_criteria(obj):
        valid_modes = ramble.success_criteria.SuccessCriteria._valid_modes
        if mode not in valid_modes:
            logger.die(f"Mode {mode} is not valid. Valid values are {valid_modes}")

        obj.success_criteria[name] = {
            "mode": mode,
            "match": match,
            "anti_match": anti_match,
            "file": file,
            "fom_name": fom_name,
            "fom_context": fom_context,
            "formula": formula,
        }

    return _execute_success_criteria


@shared_directive("builtins")
def register_builtin(
    name, required=True, injection_method="prepend", depends_on=[], dependents=[]
):
    """Register a builtin

    Builtins are methods that return lists of strings. These methods represent
    a way to write python code to generate executables for building up
    workloads.

    Manual injection of a builtins can be performed through modifying the
    execution order in the internals config section.

    Modifier builtins are named:
    `modifier_builtin::modifier_name::method_name`.

    Application modifiers are named:
    `builtin::method_name`.

    Package manager builtins are named:
    `package_manager_builtin::package_manager_name::method_name`.

    As an example, if the following builtin was defined:

    .. code-block:: python

      register_builtin('example_builtin', required=True)
      def example_builtin(self):
        ...

    Its fully qualified name would be:
    * `modifier_builtin::test-modifier::example_builtin` when defined in a
    modifier named `test-modifier`
    * `builtin::example_builtin` when defined in an application

    The 'required' attribute marks a builtin as required for all workloads. This
    will ensure the builtin is added to the workload if it is not explicitly
    added. If required builtins are not explicitly added to a workload, they
    are injected into the list of executables, based on the injection_method
    attribute.

    The 'injection_method' attribute controls where the builtin will be
    injected into the executable list.
    Options are:
    - 'prepend' -- This builtin will be injected at the beginning of the executable list
    - 'append' -- This builtin will be injected at the end of the executable list

    Args:
        name (str): Name of builtin (should be the name of a class method) to register
        required (boolean): Whether the builtin will be auto-injected or not
        injection_method (str): The method of injecting the builtin. Can be
                                'prepend' or 'append'
        depends_on (list(str)): The names of builtins this builtin depends on
                                (and must execute after).
        dependents (list(str)): The names of builtins that should come
                                after the current one.
    """
    supported_injection_methods = ["prepend", "append"]

    def _store_builtin(obj):
        if injection_method not in supported_injection_methods:
            raise ramble.language.language_base.DirectiveError(
                f"Object {obj.name} defines builtin {name} with an invalid "
                f"injection method of {injection_method}.\n"
                f"Valid methods are {str(supported_injection_methods)}"
            )

        builtin_name = obj._builtin_name.format(obj_name=obj.name, name=name)

        obj.builtins[builtin_name] = {
            "name": name,
            "required": required,
            "injection_method": injection_method,
            "depends_on": depends_on.copy(),
            "dependents": dependents.copy(),
        }

    return _store_builtin


@shared_directive("phase_definitions")
def register_phase(name, pipeline=None, run_before=[], run_after=[]):
    """Register a phase

    Phases are portions of a pipeline that will execute when
    executing a full pipeline.

    Registering a phase allows an object to know what the phases
    dependencies are, to ensure the execution order is correct.

    If called multiple times, the dependencies are combined together. Only one
    instance of a phase will show up in the resulting dependency list for a phase.

    Args:
      name (str): The name of the phase. Phases are functions named '_<phase>'.
      pipeline (str): The name of the pipeline this phase should be registered into.
      run_before (list(str)): A list of phase names this phase should run before
      run_after (list(str)): A list of phase names this phase should run after
    """

    def _execute_register_phase(obj):
        import ramble.util.graph

        if pipeline not in obj._pipelines:
            raise ramble.language.language_base.DirectiveError(
                "Directive register_phase was "
                f'given an invalid pipeline "{pipeline}"\n'
                "Available pipelines are: "
                f" {obj._pipelines}"
            )

        if not isinstance(run_before, list):
            raise ramble.language.language_base.DirectiveError(
                "Directive register_phase was "
                "given an invalid type for "
                "the run_before attribute in object "
                f"{obj.name}"
            )

        if not isinstance(run_after, list):
            raise ramble.language.language_base.DirectiveError(
                "Directive register_phase was "
                "given an invalid type for "
                "the run_after attribute in object "
                f"{obj.name}"
            )

        if not hasattr(obj, f"_{name}"):
            raise ramble.language.language_base.DirectiveError(
                "Directive register_phase was "
                f"given an undefined phase {name} "
                f"in object {obj.name}"
            )

        if pipeline not in obj.phase_definitions:
            obj.phase_definitions[pipeline] = {}

        if name in obj.phase_definitions[pipeline]:
            phase_node = obj.phase_definitions[pipeline][name]
        else:
            phase_node = ramble.util.graph.GraphNode(name)

        for before in run_before:
            phase_node.order_before(before)

        for after in run_after:
            phase_node.order_after(after)

        obj.phase_definitions[pipeline][name] = phase_node

    return _execute_register_phase


@shared_directive(dicts=())
def maintainers(*names: str):
    """Add a new maintainer directive, to specify maintainers in a declarative way.

    Args:
        names (str(s)): GitHub username(s) for the maintainer. Can provide
                        multiple names as separate arguments.
    """

    def _execute_maintainer(obj):
        maintainers_from_base = getattr(obj, "maintainers", [])
        # Here it is essential to copy, otherwise we might add to an empty list in the parent
        obj.maintainers = list(sorted(set(maintainers_from_base + list(names))))

    return _execute_maintainer


@shared_directive(dicts=())
def tags(*values: str):
    """Add a new tag directive, to specify tags in a declarative way.

    Args:
        values (str(s)): Values to mark as a tag. Can provide multiple values
                         as separate arguments.
    """

    def _execute_tag(obj):
        tags_from_base = getattr(obj, "tags", [])
        # Here it is essential to copy, otherwise we might add to an empty list in the parent
        obj.tags = list(sorted(set(tags_from_base + list(values))))

    return _execute_tag


@shared_directive(dicts=())
def target_shells(shell_support_pattern=None):
    """Directive to specify supported shells.

    If not specified, i.e., not directly specified or inherited from the base,
    then it assumes all shells are supported.

    Args:
        shell_support_pattern (str): The glob pattern that is used to match
                                     with the configured shell
    """

    def _execute_target_shells(obj):
        if shell_support_pattern is not None:
            obj.shell_support_pattern = shell_support_pattern

    return _execute_target_shells

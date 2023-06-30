# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import llnl.util.tty as tty

import ramble.language.language_base
import ramble.language.language_helpers
import ramble.success_criteria


"""This module contains directives directives that are shared between multiple object types

Directives are functions that can be called inside an object
definition to modify the object, for example:

    .. code-block:: python

      class Gromacs(SpackApplication):
          # Required package directive
          required_package('zlib')

In the above example, 'required_package' is a ramble directive

Directives defined in this module are used by multiple object types, which
inherit from the SharedMeta class.
"""


class SharedMeta(ramble.language.language_base.DirectiveMeta):
    _directive_names = set()
    _diretives_to_be_executed = []


# shared_directive = ramble.language.language_base.DirectiveMeta.directive
shared_directive = SharedMeta.directive


@shared_directive('archive_patterns')
def archive_pattern(pattern):
    """Adds a file pattern to be archived in addition to figure of merit logs

    Defines a new file pattern that will be archived during workspace archival.
    Archival will only happen for files that match the pattern when archival
    is being performed.

    Args:
      pattern: Pattern that refers to files to archive
    """

    def _execute_archive_pattern(obj):
        obj.archive_patterns[pattern] = pattern

    return _execute_archive_pattern


@shared_directive('figure_of_merit_contexts')
def figure_of_merit_context(name, regex, output_format):
    """Defines a context for figures of merit

    Defines a new context to contain figures of merit.

    Args:
      name: High level name of the context. Can be referred to in
            the figure of merit
      regex: Regular expression, using group names, to match a context.
      output_format: String, using python keywords {group_name} to extract
                     group names from context regular expression.
    """

    def _execute_figure_of_merit_context(obj):
        obj.figure_of_merit_contexts[name] = {
            'regex': regex,
            'output_format': output_format
        }

    return _execute_figure_of_merit_context


@shared_directive('figures_of_merit')
def figure_of_merit(name, fom_regex, group_name, log_file='{log_file}', units='',
                    contexts=[]):
    """Adds a figure of merit to track for this object

    Defines a new figure of merit.

    Args:
      name: High level name of the figure of merit
      log_file: File the figure of merit can be extracted from
      fom_regex: A regular expression using named groups to extract the FOM
      group_name: The name of the group that the FOM should be pulled from
      units: The units associated with the FOM
    """

    def _execute_figure_of_merit(obj):
        obj.figures_of_merit[name] = {
            'log_file': log_file,
            'regex': fom_regex,
            'group_name': group_name,
            'units': units,
            'contexts': contexts
        }

    return _execute_figure_of_merit


@shared_directive('default_compilers')
def default_compiler(name, spack_spec, compiler_spec=None, compiler=None):
    """Defines the default compiler that will be used with this object

    Adds a new compiler spec to this object. Software specs should
    reference a compiler that has been added.
    """

    def _execute_default_compiler(obj):
        if hasattr(obj, 'uses_spack') and getattr(obj, 'uses_spack'):
            obj.default_compilers[name] = {
                'spack_spec': spack_spec,
                'compiler_spec': compiler_spec,
                'compiler': compiler
            }

    return _execute_default_compiler


@shared_directive('software_specs')
def software_spec(name, spack_spec, compiler_spec=None, compiler=None):
    """Defines a new software spec needed for this object.

    Adds a new software spec (for spack to use) that this object
    needs to execute properly.

    Only adds specs to object that use spack.

    Specs can be described as an mpi spec, which means they
    will depend on the MPI library within the resulting spack
    environment.
    """

    def _execute_software_spec(obj):
        if hasattr(obj, 'uses_spack') and getattr(obj, 'uses_spack'):

            # Define the spec
            obj.software_specs[name] = {
                'spack_spec': spack_spec,
                'compiler_spec': compiler_spec,
                'compiler': compiler
            }

    return _execute_software_spec


@shared_directive('required_packages')
def required_package(name):
    """Defines a new spack package that is required for this object
    to function properly.
    """

    def _execute_required_package(obj):
        obj.required_packages[name] = True

    return _execute_required_package


@shared_directive('success_criteria')
def success_criteria(name, mode, match=None, file='{log_file}',
                     fom_name=None, fom_context='null', formula=None):
    """Defines a success criteria used by experiments of this object

    Adds a new success criteria to this object definition.

    These will be checked during the analyze step to see if a job exited properly.

    Arguments:
      name: The name of this success criteria
      mode: The type of success criteria that will be validated
            Valid values are: 'string', 'application_function', and 'fom_comparison'
      match: For mode='string'. Value to check indicate success (if found, it
             would mark success)
      file: For mode='string'. File success criteria should be located in
      fom_name: For mode='fom_comparison'. Name of fom for a criteria.
                Accepts globbing.
      fom_context: For mode='fom_comparison'. Context the fom is contained
                   in. Accepts globbing.
      formula: For mode='fom_comparison'. Formula to use to evaluate success.
               '{value}' keyword is set as the value of the FOM.
    """

    def _execute_success_criteria(obj):
        valid_modes = ramble.success_criteria.SuccessCriteria._valid_modes
        if mode not in valid_modes:
            tty.die(f'Mode {mode} is not valid. Valid values are {valid_modes}')

        obj.success_criteria[name] = {
            'mode': mode,
            'match': match,
            'file': file,
            'fom_name': fom_name,
            'fom_context': fom_context,
            'formula': formula,
        }

    return _execute_success_criteria


@shared_directive('builtins')
def register_builtin(name, required=True, injection_method='prepend'):
    """Register a builtin

    Builtins are methods that return lists of strings. These methods represent
    a way to write python code to generate executables for building up
    workloads.

    Manual injection of a builtins can be performed through modifying the
    execution order in the internals config section.

    Modifier builtins are named:
    `modifier_builtin::modifier_name::method_name`.

    Application modifiers are named:
    `builtin::method_name`

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
    are injected  into the list of executables, based on the injection_method
    attribute.

    The 'injection_method' attribute controls where the builtin will be
    injected into the executable list.
    Options are:
    - 'prepend' -- This builtin will be injected at the beginning of the executable list
    - 'append' -- This builtin will be injected at the end of the executable list
    """
    supported_injection_methods = ['prepend', 'append']

    def _store_builtin(obj):
        if injection_method not in supported_injection_methods:
            raise ramble.language.language_base.DirectiveError(
                f'Object {obj.name} has an invalid '
                f'injection method of {injection_method}.\n'
                f'Valid methods are {str(supported_injection_methods)}'
            )

        builtin_name = obj._builtin_name.format(obj_name=obj.name, name=name)

        obj.builtins[builtin_name] = {'name': name,
                                      'required': required,
                                      'injection_method': injection_method}
    return _store_builtin


@shared_directive(dicts=())
def maintainers(*names: str):
    """Add a new maintainer directive, to specify maintainers in a declarative way.

    Args:
        names: GitHub username for the maintainer
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
        values: Value to mark as a tag
    """

    def _execute_tag(obj):
        tags_from_base = getattr(obj, "tags", [])
        # Here it is essential to copy, otherwise we might add to an empty list in the parent
        obj.tags = list(sorted(set(tags_from_base + list(values))))

    return _execute_tag

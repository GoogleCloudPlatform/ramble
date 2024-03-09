# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.
"""Define base classes for application definitions"""

import os
import stat
import re
import six
import textwrap
import string
import shutil
import fnmatch
import time
from typing import List

import llnl.util.filesystem as fs
import llnl.util.tty.color as color
from llnl.util.tty.colify import colified

import spack.util.executable
import spack.util.spack_json
import spack.util.environment
import spack.util.compression

import ramble.config
import ramble.graphs
import ramble.stage
import ramble.mirror
import ramble.fetch_strategy
import ramble.expander
import ramble.keywords
import ramble.repeats
import ramble.repository
import ramble.modifier
import ramble.pipeline
import ramble.util.executable
import ramble.util.colors as rucolor
import ramble.util.hashing
import ramble.util.env
import ramble.util.directives
import ramble.util.stats
import ramble.util.graph
from ramble.util.logger import logger

from ramble.workspace import namespace

from ramble.language.application_language import ApplicationMeta
from ramble.language.shared_language import SharedMeta, register_builtin, register_phase
from ramble.error import RambleError

from enum import Enum
experiment_status = Enum('experiment_status', ['UNKNOWN', 'SETUP', 'RUNNING',
                                               'COMPLETE', 'SUCCESS', 'FAILED'])


class ApplicationBase(object, metaclass=ApplicationMeta):
    name = None
    uses_spack = False
    _builtin_name = 'builtin::{name}'
    _builtin_required_key = 'required'
    _inventory_file_name = 'ramble_inventory.json'
    _status_file_name = 'ramble_status.json'
    _pipelines = ['analyze', 'archive', 'mirror', 'setup', 'pushtocache', 'execute']
    _language_classes = [ApplicationMeta, SharedMeta]

    #: Lists of strings which contains GitHub usernames of attributes.
    #: Do not include @ here in order not to unnecessarily ping the users.
    maintainers: List[str] = []
    tags: List[str] = []

    license_inc_name = 'license.inc'

    def __init__(self, file_path):
        super().__init__()

        self.keywords = ramble.keywords.keywords

        self._vars_are_expanded = False
        self.expander = None
        self._formatted_executables = {}
        self.variables = None
        self.no_expand_vars = None
        self.experiment_set = None
        self.internals = {}
        self.is_template = False
        self.repeats = ramble.repeats.Repeats()
        self._command_list = []
        self.chained_experiments = None
        self.chain_order = []
        self.chain_prepend = []
        self.chain_append = []
        self.chain_commands = {}
        self._env_variable_sets = {}
        self.modifiers = []
        self.experiment_tags = []
        self._modifier_instances = []
        self._modifier_builtins = {}
        self._input_fetchers = None
        self.results = {}
        self._phase_times = {}
        self._pipeline_graphs = None
        self.custom_executables = {}

        self.hash_inventory = {
            'application_definition': None,
            'modifier_definitions': [],
            'attributes': [],
            'inputs': [],
            'software': [],
            'templates': [],
        }
        self.experiment_hash = None

        self._file_path = file_path

        self.application_class = 'ApplicationBase'

        self._verbosity = 'short'

        self.license_path = ''
        self.license_file = ''

        ramble.util.directives.define_directive_methods(self)

    def copy(self):
        """Deep copy an application instance"""
        new_copy = type(self)(self._file_path)

        if self._env_variable_sets:
            new_copy.set_env_variable_sets(self._env_variable_sets.copy())
        if self.variables:
            new_copy.set_variables(self.variables.copy(), self.experiment_set)
        if self.internals:
            new_copy.set_internals(self.internals.copy())
        if self._formatted_executables:
            new_copy.set_formatted_executables(self._formatted_executables.copy())

        new_copy.set_template(False)
        new_copy.repeats.set_repeats(False, 0)
        new_copy.set_chained_experiments(None)

        return new_copy

    def is_actionable(self):
        """Determine if an experiment should be actioned in pipelines

        Returns True if the experiment should be actioned in a pipeline, False
        if not.
        """

        if self.is_template:
            return False

        return True

    def build_phase_order(self):
        if self._pipeline_graphs is not None:
            return

        self._pipeline_graphs = {}
        for pipeline in self._pipelines:
            if pipeline not in self.phase_definitions:
                self.phase_definitions[pipeline] = {}

            self._pipeline_graphs[pipeline] = ramble.graphs.PhaseGraph(
                self.phase_definitions[pipeline],
                self
            )

            for mod_inst in self._modifier_instances:
                # Define phase nodes
                for phase, phase_node in mod_inst.all_pipeline_phases(pipeline):
                    self._pipeline_graphs[pipeline].add_node(
                        phase_node, obj_inst=mod_inst
                    )

                # Define phase edges
                for phase, phase_node in mod_inst.all_pipeline_phases(pipeline):
                    self._pipeline_graphs[pipeline].define_edges(
                        phase_node, internal_order=True
                    )

    def _long_print(self):
        out_str = []
        out_str.append(rucolor.section_title('Application: ') + f'{self.name}\n')
        out_str.append('\n')

        out_str.append(rucolor.section_title('Description:\n'))
        if self.__doc__:
            out_str.append(f'\t{self.__doc__}\n')
        else:
            out_str.append('\tNone\n')

        if hasattr(self, 'maintainers'):
            out_str.append('\n')
            out_str.append(rucolor.section_title("Maintainers:\n"))
            out_str.append(colified(self.maintainers, tty=True))
            out_str.append('\n')

        if hasattr(self, 'tags'):
            out_str.append('\n')
            out_str.append(rucolor.section_title('Tags:\n'))
            out_str.append(colified(self.tags, tty=True))
            out_str.append('\n')

        for pipeline in self._pipelines:
            out_str.append('\n')
            out_str.append(rucolor.section_title(f'Pipeline "{pipeline}" Phases:\n'))
            out_str.append(colified(self.get_pipeline_phases(pipeline), tty=True))

        # Print all FOMs without a context
        if hasattr(self, 'figures_of_merit'):
            out_str.append('\n')
            out_str.append(rucolor.section_title('Figure of merit contexts:\n'))
            out_str.append(rucolor.nested_1('\t(null) context (default):\n'))
            for name, conf in self.figures_of_merit.items():
                if len(conf['contexts']) == 0:
                    out_str.append(rucolor.nested_2(f'\t\t{name}\n'))
                    out_str.append(f'\t\t\tunits = {conf["units"]}\n')
                    out_str.append(f'\t\t\tlog file = {conf["log_file"]}\n')

            if hasattr(self, 'figure_of_merit_contexts'):
                for context_name, context_conf in self.figure_of_merit_contexts.items():
                    out_str.append(rucolor.nested_1(f'\t{context_name} context:\n'))
                    for name, conf in self.figures_of_merit.items():
                        if context_name in conf['contexts']:
                            out_str.append(rucolor.nested_2(f'\t\t{name}\n'))
                            out_str.append(f'\t\t\tunits = {conf["units"]}\n')
                            out_str.append(f'\t\t\tlog file = {conf["log_file"]}\n')

        if hasattr(self, 'workloads'):
            out_str.append('\n')
            for wl_name, wl_conf in self.workloads.items():
                out_str.append(rucolor.section_title('Workload:') + f' {wl_name}\n')
                out_str.append('\t' + rucolor.nested_1('Executables: ') +
                               f'{self._get_exec_order(wl_name)}\n')
                out_str.append('\t' + rucolor.nested_1('Inputs: ') +
                               f'{wl_conf["inputs"]}\n')
                out_str.append('\t' + rucolor.nested_1('Workload Tags: \n'))
                if 'tags' in wl_conf and wl_conf['tags']:
                    out_str.append(colified(wl_conf['tags'], indent=8) + '\n')

                if wl_name in self.environment_variables:
                    out_str.append(rucolor.nested_1('\tEnvironment Variables:\n'))
                    for var, conf in self.environment_variables[wl_name].items():
                        indent = '\t\t'

                        out_str.append(rucolor.nested_2(f'{indent}{var}:\n'))
                        out_str.append(f'{indent}\tDescription: {conf["description"]}\n')
                        out_str.append(f'{indent}\tValue: {conf["value"]}\n')

                if wl_name in self.workload_variables:
                    out_str.append(rucolor.nested_1('\tVariables:\n'))
                    for var, conf in self.workload_variables[wl_name].items():
                        indent = '\t\t'

                        out_str.append(rucolor.nested_2(f'{indent}{var}:\n'))
                        out_str.append(f'{indent}\tDescription: {conf["description"]}\n')
                        out_str.append(f'{indent}\tDefault: {conf["default"]}\n')
                        if 'values' in conf:
                            out_str.append(f'{indent}\tSuggested Values: {conf["values"]}\n')

            out_str.append('\n')

        if hasattr(self, 'builtins'):
            out_str.append(rucolor.section_title('Builtin Executables:\n'))
            out_str.append('\t' + colified(self.builtins.keys(), tty=True) + '\n')
        return out_str

    def set_env_variable_sets(self, env_variable_sets):
        """Set internal reference to environment variable sets"""

        self._env_variable_sets = env_variable_sets.copy()

    def set_variables(self, variables, experiment_set):
        """Set internal reference to variables

        Also, create an application specific expander class.
        """

        self.variables = variables
        self.experiment_set = experiment_set
        self.expander = ramble.expander.Expander(self.variables, self.experiment_set)

        self.no_expand_vars = set()
        workload_name = self.expander.workload_name
        if workload_name in self.workload_variables:
            for var, conf in self.workload_variables[workload_name].items():
                if 'expandable' in conf and not conf['expandable']:
                    self.no_expand_vars.add(var)

        self.expander.set_no_expand_vars(self.no_expand_vars)

    def set_internals(self, internals):
        """Set internal reference to application internals
        """

        self.internals = internals

    def set_template(self, is_template):
        """Set if this instance is a template or not"""
        self.is_template = is_template

    def set_chained_experiments(self, chained_experiments):
        """Set chained experiments for this instance"""
        self.chained_experiments = None
        if chained_experiments:
            self.chained_experiments = chained_experiments.copy()

    def set_modifiers(self, modifiers):
        """Set modifiers for this instance"""
        if modifiers:
            self.modifiers = modifiers.copy()

    def set_tags(self, tags):
        """Set experiment tags for this instance"""

        self.experiment_tags = self.tags.copy()

        workload_name = self.expander.workload_name
        self.experiment_tags.extend(self.workloads[workload_name]['tags'])

        if tags:
            self.experiment_tags.extend(tags)

    def set_formatted_executables(self, formatted_executables):
        """Set formatted executables for this instance"""
        self._formatted_executables = formatted_executables.copy()

    def has_tags(self, tags):
        """Check if this instance has provided tags.

        Args:
            tags (list): List of strings, where each string is an indivudal tag
        Returns:
            (bool): True if all tags are in this instance, False otherwise
        """

        if tags and self.experiment_tags:
            tag_set = set(tags)
            exp_tag_set = set(self.experiment_tags)

            for tag in tag_set:
                if tag not in exp_tag_set:
                    return False
            return True

        return False

    def experiment_log_file(self, logs_dir):
        """Returns an experiment log file path for the given logs directory"""
        return os.path.join(
            logs_dir,
            self.expander.experiment_namespace) + \
            '.out'

    def get_pipeline_phases(self, pipeline, phase_filters=['*']):
        self.build_modifier_instances()
        self.build_phase_order()

        if pipeline not in self._pipelines:
            logger.die(f'Requested pipeline {pipeline} is not valid.\n',
                       f'\tAvailable pipelinese are {self._pipelines}')

        phases = set()
        if pipeline in self._pipeline_graphs:
            for phase in self._pipeline_graphs[pipeline].walk():
                for phase_filter in phase_filters:
                    if fnmatch.fnmatch(phase.key, phase_filter):
                        phases.add(phase)

        include_phase_deps = ramble.config.get('config:include_phase_dependencies')
        if include_phase_deps:
            phases_for_deps = list(phases)
            while phases_for_deps:
                cur_phase = phases_for_deps.pop(0)
                for phase in phases:
                    if phase is not cur_phase and phase not in phases:
                        if cur_phase.key in phase._order_before:
                            phases_for_deps.append(phase)
                            phases.add(phase)

                for dep_phase_name in cur_phase._order_after:
                    dep_node = self._pipeline_graphs[pipeline].get_node(dep_phase_name)
                    if dep_node not in phases:
                        phases_for_deps.append(dep_node)
                        phases.add(dep_node)

        phase_order = []
        for node in self._pipeline_graphs[pipeline].walk():
            if node in phases:
                phase_order.append(node.key)
        return phase_order

    def _short_print(self):
        return [self.name]

    def __str__(self):
        if self._verbosity == 'long':
            return ''.join(self._long_print())
        elif self._verbosity == 'short':
            return ''.join(self._short_print())
        return self.name

    def print_vars(self, header='', vars_to_print=None, indent=''):
        print_vars = vars_to_print
        if not print_vars:
            print_vars = self.variables

        color.cprint(f'{indent}{header}:')
        for var, val in print_vars.items():
            expansion_var = self.expander.expansion_str(var)
            expanded = self.expander.expand_var(expansion_var)
            color.cprint(f'{indent}  {var} = {val} ==> {expanded}'.replace('@', '@@'))

    def build_used_variables(self, workspace):
        """Build a set of all used variables

        By expanding all necessary portions of this experiment (required /
        reserved keywords, templates, commands, etc...), determine which
        variables are used throughout the experiment definition.

        Variables can have list definitions. These are iterated over to ensure
        variables referenced by any of them are tracked properly.

        Args:
            workspace (Workspace): Workspace to extract templates from

        Returns:
            (set): All variable names used by this experiment.
        """
        self.add_expand_vars(workspace)

        # Add all known keywords
        for key in self.keywords.keys:
            self.expander._used_variables.add(key)
            self.expander.expand_var_name(key)

        if self.chained_experiments:
            for chained_exp in self.chained_experiments:
                if namespace.inherit_variables in chained_exp:
                    for var in chained_exp[namespace.inherit_variables]:
                        self.expander._used_variables.add(var)

        # Add variables from success criteria
        criteria_list = workspace.success_list
        for criteria in criteria_list.all_criteria():
            if criteria.mode == 'fom_comparison':
                self.expander.expand_var(criteria.formula)
                self.expander.expand_var(criteria.fom_name)
                self.expander.expand_var(criteria.fom_context)
            elif criteria.mode == 'application_function':
                self.evaluate_success()

        for template_name, template_conf in workspace.all_templates():
            self.expander._used_variables.add(template_name)
            self.expander.expand_var(template_conf['contents'])

        return self.expander._used_variables

    def print_internals(self, indent=''):
        if not self.internals:
            return

        if namespace.custom_executables in self.internals:
            header = rucolor.nested_4('Custom Executables')
            color.cprint(f'{indent}{header}:')

            for name in self.internals[namespace.custom_executables]:
                color.cprint(f'{indent}  {name}')

        if namespace.executables in self.internals:
            header = rucolor.nested_4('Executable Order')
            color.cprint(f'{indent}{header}: {str(self.internals[namespace.executables])}')

        if namespace.executable_injection in self.internals:
            header = rucolor.nested_4('Executable Injection')
            color.cprint(
                f'{indent}{header}: {str(self.internals[namespace.executable_injection])}'
            )

    def print_chain_order(self, indent=''):
        if not self.chain_order:
            return

        header = rucolor.nested_4('Experiment Chain')
        color.cprint(f'{indent}{header}:')
        for exp in self.chain_order:
            color.cprint(f'{indent}- {exp}')

    def format_doc(self, **kwargs):
        """Wrap doc string at 72 characters and format nicely"""
        indent = kwargs.get('indent', 0)

        if not self.__doc__:
            return ""

        doc = re.sub(r'\s+', ' ', self.__doc__)
        lines = textwrap.wrap(doc, 72)
        results = six.StringIO()
        for line in lines:
            results.write((" " * indent) + line + "\n")
        return results.getvalue()

    # Phase execution helpers
    def run_phase(self, pipeline, phase, workspace):
        """Run a phase, by getting its function pointer"""
        self.add_expand_vars(workspace)
        if self.is_template:
            logger.debug(f'{self.name} is a template. Skipping phases')
            return
        if self.repeats.is_repeat_base:
            logger.debug(f'{self.name} is a repeat base. Skipping phases')
            return

        phase_node = self._pipeline_graphs[pipeline].get_node(phase)

        if phase_node is None:
            logger.die(f'Phase {phase} is not defined in pipeline {pipeline}')

        logger.msg(f'  Executing phase {phase}')
        start_time = time.time()
        for mod_inst in self._modifier_instances:
            mod_inst.run_phase_hook(workspace, pipeline, phase)
        phase_func = phase_node.attribute
        phase_func(workspace, app_inst=self)
        self._phase_times[phase] = time.time() - start_time

    def print_phase_times(self, pipeline, phase_filters=['*']):
        """Print phase execution times by pipeline phase order

        Args:
            pipeline (str): Name of pipeline to print timing information for
            phase_filters (list(str)): Filters to limit phases to print
        """
        logger.msg('Phase timing statistics:')
        for phase in self.get_pipeline_phases(pipeline, phase_filters=phase_filters):
            # Set default time to 0.0 s, to prevent KeyError from skipped phases
            if phase not in self._phase_times:
                self._phase_times[phase] = 0.0
            logger.msg(f'  {phase} time: {round(self._phase_times[phase], 5)} (s)')

    def create_experiment_chain(self, workspace):
        """Create the necessary chained experiments for this instance

        This method determines which experiments need to be chained, grabs the
        base instance from the experiment set, creates a copy of it (with a
        unique name), injects the copy back into the experiment set,
        and builds an internal mapping from unique name to the chaining definition.
        """

        if not self.chained_experiments or self.is_template:
            return

        # Build initial stack. Uses a reversal of the current instance's
        # chained experiments
        parent_namespace = self.expander.experiment_namespace
        classes_in_stack = set([self])
        chain_idx = 0
        chain_stack = []
        for exp in reversed(self.chained_experiments):
            for exp_name in self.experiment_set.search_primary_experiments(exp['name']):
                child_inst = self.experiment_set.get_experiment(exp_name)

                if child_inst in classes_in_stack:
                    raise ChainCycleDetectedError('Cycle detected in experiment chain:\n' +
                                                  f'    Primary experiment {parent_namespace}\n' +
                                                  f'    Chained expeirment name: {exp_name}\n' +
                                                  f'    Chain definition: {str(exp)}')
                chain_stack.append((exp_name, exp))

        parent_run_dir = self.expander.expand_var(
            self.expander.expansion_str(self.keywords.experiment_run_dir)
        )

        # Continue until the stack is empty
        while len(chain_stack) > 0:
            cur_exp_name = chain_stack[-1][0]
            cur_exp_def = chain_stack[-1][1]

            # Perform basic validation on the chained experiment definition
            if 'name' not in cur_exp_def:
                raise InvalidChainError('Invalid experiment chain defined:\n' +
                                        f'    Primary experiment {parent_namespace}\n' +
                                        f'    Chain definition: {str(exp)}\n' +
                                        '    "name" keyword must be defined')

            if 'order' in cur_exp_def:
                possible_orders = ['after_chain', 'after_root', 'before_chain', 'before_root']
                if cur_exp_def['order'] not in possible_orders:
                    raise InvalidChainError('Invalid experiment chain defined:\n' +
                                            f'    Primary experiment {parent_namespace}\n' +
                                            f'    Chain definition: {str(exp)}\n' +
                                            '    Optional keyword "order" must ' +
                                            f'be one of {str(possible_orders)}\n')

            if 'command' not in cur_exp_def.keys():
                raise InvalidChainError('Invalid experiment chain defined:\n' +
                                        f'    Primary experiment {parent_namespace}\n' +
                                        f'    Chain definition: {str(exp)}\n' +
                                        '    "command" keyword must be defined')

            if 'variables' in cur_exp_def:
                if not isinstance(cur_exp_def['variables'], dict):
                    raise InvalidChainError('Invalid experiment chain defined:\n' +
                                            f'    Primary experiment {parent_namespace}\n' +
                                            f'    Chain definition: {str(exp)}\n' +
                                            '    Optional keyword "variables" ' +
                                            'must be a dictionary')

            base_inst = self.experiment_set.get_experiment(cur_exp_name)
            if base_inst in classes_in_stack:
                chain_stack.pop()
                classes_in_stack.remove(base_inst)

                order = 'after_root'
                if 'order' in cur_exp_def:
                    order = cur_exp_def['order']

                chained_name = f'{chain_idx}.{cur_exp_name}'
                new_name = f'{parent_namespace}.chain.{chained_name}'

                new_run_dir = os.path.join(parent_run_dir,
                                           namespace.chained_experiments, chained_name)

                if order == 'before_chain':
                    self.chain_prepend.insert(0, new_name)
                elif order == 'before_root':
                    self.chain_prepend.append(new_name)
                elif order == 'after_root':
                    self.chain_append.insert(0, new_name)
                elif order == 'after_chain':
                    self.chain_append.append(new_name)
                self.chain_commands[new_name] = cur_exp_def[namespace.command]

                # Skip editing the new instance if the base_inst doesn't work
                # This happens if the originating command is `workspace info`
                # The printing experiment set doesn't have access to all
                # of the experiment, so the base_inst command above
                # doesn't get an application instance.
                if base_inst:
                    new_inst = base_inst.copy()

                    if namespace.variables in cur_exp_def:
                        for var, val in cur_exp_def[namespace.variables].items():
                            new_inst.variables[var] = val

                    new_inst.expander._experiment_namespace = new_name
                    new_inst.variables[self.keywords.experiment_run_dir] = new_run_dir
                    new_inst.variables[self.keywords.experiment_name] = new_name
                    new_inst.variables[self.keywords.experiment_index] = \
                        self.expander.expand_var_name(self.keywords.experiment_index)
                    new_inst.repeats = self.repeats
                    new_inst.read_status()

                    # Extract inherited variables
                    if namespace.inherit_variables in cur_exp_def:
                        for inherit_var in cur_exp_def[namespace.inherit_variables]:
                            new_inst.variables[inherit_var] = self.variables[inherit_var]

                    # Expand the chained experiment vars, so we can build the execution command
                    new_inst.add_expand_vars(workspace)
                    chain_cmd = new_inst.expander.expand_var(cur_exp_def[namespace.command])
                    self.chain_commands[new_name] = chain_cmd
                    cur_exp_def[namespace.command] = chain_cmd
                    self.experiment_set.add_chained_experiment(new_name, new_inst)

                chain_idx += 1
            else:
                # Avoid cycles, from children
                if base_inst in classes_in_stack:
                    chain_stack.pop()
                else:
                    if base_inst.chained_experiments:
                        for exp in reversed(base_inst.chained_experiments):
                            for exp_name in \
                                    self.experiment_set.search_primary_experiments(exp['name']):
                                child_inst = self.experiment_set.get_experiment(exp_name)
                                if child_inst in classes_in_stack:
                                    raise ChainCycleDetectedError('Cycle detected in ' +
                                                                  'experiment chain:\n' +
                                                                  '    Primary experiment ' +
                                                                  f'{parent_namespace}\n' +
                                                                  '    Chained expeirment name: ' +
                                                                  f'{cur_exp_name}\n' +
                                                                  '    Chain definition: ' +
                                                                  f'{str(cur_exp_def)}')

                                chain_stack.append((exp_name, exp))
                    classes_in_stack.add(base_inst)

        # Create the final chain order
        for exp in self.chain_prepend:
            self.chain_order.append(exp)
        self.chain_order.append(self.expander.experiment_namespace)
        for exp in self.chain_append:
            self.chain_order.append(exp)

        # Inject the chain order into the children experiments
        for exp in self.chain_prepend:
            exp_inst = self.experiment_set.get_experiment(exp)
            if exp_inst:
                exp_inst.chain_order = self.chain_order.copy()

        for exp in self.chain_append:
            exp_inst = self.experiment_set.get_experiment(exp)
            if exp_inst:
                exp_inst.chain_order = self.chain_order.copy()

    def define_variable(self, var_name, var_value):
        self.expander._variables[var_name] = var_value
        for mod_inst in self._modifier_instances:
            mod_inst.expander._variables[var_name] = var_value

    def build_modifier_instances(self):
        """Built a map of modifier names to modifier instances needed for this
           application instance
        """

        if not self.modifiers:
            return

        self._modifier_instances = []

        mod_type = ramble.repository.ObjectTypes.modifiers

        for mod in self.modifiers:
            mod_inst = ramble.repository.get(mod['name'], mod_type).copy()

            if 'on_executable' in mod:
                mod_inst.set_on_executables(mod['on_executable'])
            else:
                mod_inst.set_on_executables(None)

            if 'mode' in mod:
                mod_inst.set_usage_mode(mod['mode'])
            else:
                mod_inst.set_usage_mode(None)

            mod_inst.inherit_from_application(self)

            self._modifier_instances.append(mod_inst)

            # Add this modifiers required variables for validation
            self.keywords.update_keys(mod_inst.required_vars)

        # Validate the new modifiers variables exist
        # (note: the base ramble variables are checked earlier too)
        self.keywords.check_required_keys(self.variables)

        # Ensure no expand vars are set correctly for modifiers
        for mod_inst in self._modifier_instances:
            for var in mod_inst.no_expand_vars():
                self.expander.add_no_expand_var(var)
                mod_inst.expander.add_no_expand_var(var)

    def define_modifier_variables(self):
        """Extract default variable definitions from modifier instances"""

    def _define_custom_executables(self):
        # Define custom executables
        if namespace.custom_executables in self.internals:
            for name, conf in self.internals[namespace.custom_executables].items():
                if name in self.executables or name in self.custom_executables:
                    experiment_namespace = self.expander.expand_var_name('experiment_namespace')
                    raise ExecutableNameError(f'In experiment {experiment_namespace} '
                                              f'a custom executable "{name}" is defined.\n'
                                              f'However, an executable "{name}" is already '
                                              'defined')

                self.custom_executables[name] = ramble.util.executable.CommandExecutable(
                    name=name,
                    **conf
                )

    def _get_exec_order(self, workload_name):
        graph = self._get_executable_graph(workload_name)
        order = []
        for node in graph.walk():
            order.append(node.key)
        return order

    def _get_executable_graph(self, workload_name):
        """Return executables for add_expand_vars"""
        self._define_custom_executables()
        exec_order = self.workloads[workload_name]['executables']
        # Use yaml defined executable order, if defined
        if namespace.executables in self.internals:
            exec_order = self.internals[namespace.executables]

        builtin_objects = [self]
        all_builtins = [self.builtins]
        for mod_inst in self._modifier_instances:
            builtin_objects.append(mod_inst)
            all_builtins.append(mod_inst.builtins)

        all_executables = self.executables.copy()
        all_executables.update(self.custom_executables)

        executable_graph = ramble.graphs.ExecutableGraph(exec_order, all_executables,
                                                         builtin_objects, all_builtins,
                                                         self)

        # Perform executable injection
        if namespace.executable_injection in self.internals:
            for exec_injection in self.internals[namespace.executable_injection]:
                exec_name = exec_injection['name']
                order = 'before'
                if 'order' in exec_injection:
                    order = exec_injection['order']
                relative_to = None
                if 'relative_to' in exec_injection:
                    relative_to = exec_injection['relative_to']
                executable_graph.inject_executable(exec_name, order, relative_to)

        return executable_graph

    def _set_input_path(self):
        """Put input_path into self.variables[input_file] for add_expand_vars"""
        self._inputs_and_fetchers(self.expander.workload_name)

        for input_file, input_conf in self._input_fetchers.items():
            input_vars = {self.keywords.input_name: input_conf['input_name']}
            if not input_conf['expand']:
                input_vars[self.keywords.input_name] = input_file
            input_path = os.path.join(self.expander.workload_input_dir,
                                      self.expander.expand_var(input_conf['target_dir'],
                                                               extra_vars=input_vars))
            self.variables[input_conf['input_name']] = input_path

    def _set_default_experiment_variables(self):
        """Set default experiment variables (for add_expand_vars),
        if they haven't been set already"""
        # Set default experiment variables, if they haven't been set already
        var_sets = []
        if self.expander.workload_name in self.workload_variables:
            var_sets.append(self.workload_variables[self.expander.workload_name])

        for mod_inst in self._modifier_instances:
            var_sets.append(mod_inst.mode_variables())

        for var_set in var_sets:
            for var, conf in var_set.items():
                if var not in self.variables.keys():
                    self.variables[var] = conf['default']

        if self.expander.workload_name in self.environment_variables:
            wl_env_vars = self.environment_variables[self.expander.workload_name]

            for name, vals in wl_env_vars.items():

                action = vals['action']
                value = vals['value']

                for env_var_set in self._env_variable_sets:
                    if action in env_var_set:
                        if name not in env_var_set[action].keys():
                            env_var_set[action][name] = value

    def _define_commands(self, exec_graph):
        """Populate the internal list of commands based on executables

        Populates self._command_list with a list of the executable commands that
        should be executed by this experiment.
        """
        if len(self._command_list) > 0:
            return

        self._command_list = []

        # Inject all prepended chained experiments
        for chained_exp in self.chain_prepend:
            self._command_list.append(self.chain_commands[chained_exp])

        # ensure all log files are purged and set up
        logs = set()

        for exec_node in exec_graph.walk():
            if isinstance(exec_node.attribute, ramble.util.executable.CommandExecutable):
                exec_cmd = exec_node.attribute
                if exec_cmd.redirect:
                    logs.add(exec_cmd.redirect)

        for log in logs:
            self._command_list.append('rm -f "%s"' % log)
            self._command_list.append('touch "%s"' % log)

        for exec_node in exec_graph.walk():
            exec_vars = {'executable_name': exec_node.key}

            if isinstance(exec_node.attribute, ramble.util.executable.CommandExecutable):
                exec_vars.update(exec_node.attribute.variables)

            for mod in self._modifier_instances:
                if mod.applies_to_executable(exec_node.key):
                    exec_vars.update(mod.modded_variables(self))

            if isinstance(exec_node.attribute, ramble.util.executable.CommandExecutable):
                # Process directive defined executables
                base_command = exec_node.attribute.copy()
                pre_commands = []
                post_commands = []

                for mod in self._modifier_instances:
                    if mod.applies_to_executable(exec_node.key):
                        pre_cmd, post_cmd = mod.apply_executable_modifiers(exec_node.key,
                                                                           base_command,
                                                                           app_inst=self)
                        pre_commands.extend(pre_cmd)
                        post_commands.extend(post_cmd)

                command_configs = pre_commands.copy()
                command_configs.append(base_command)
                command_configs.extend(post_commands)

                for cmd_conf in command_configs:
                    mpi_cmd = ''
                    if cmd_conf.mpi:
                        mpi_cmd = ' ' + self.expander.expand_var('{mpi_command}', exec_vars) + ' '

                    redirect = ''
                    if cmd_conf.redirect:
                        out_log = self.expander.expand_var(cmd_conf.redirect, exec_vars)
                        output_operator = cmd_conf.output_capture
                        redirect = f' {output_operator} "{out_log}"'

                    for part in cmd_conf.template:
                        command_part = f'{mpi_cmd}{part}{redirect}'
                        self._command_list.append(self.expander.expand_var(command_part,
                                                                           exec_vars))

            else:  # All Builtins
                func = exec_node.attribute
                func_cmds = func()
                for cmd in func_cmds:
                    self._command_list.append(self.expander.expand_var(cmd, exec_vars))

        # Inject all appended chained experiments
        for chained_exp in self.chain_append:
            self._command_list.append(self.chain_commands[chained_exp])

    def _define_formatted_executables(self):
        """Define variables representing the formatted executables

        Process the formatted_executables definitions, and construct their
        variable definitions.

        Each formatted executable definition is injected as its own variable
        based on the formatting requested.
        """

        for var_name, formatted_conf in self._formatted_executables.items():
            if var_name in self.variables:
                raise FormattedExecutableError(
                    f'Formatted executable {var_name} defined, but variable '
                    'definition already exists.'
                )

            n_indentation = 0
            if namespace.indentation in formatted_conf:
                n_indentation = int(formatted_conf[namespace.indentation]) + 1

            prefix = ''
            if namespace.prefix in formatted_conf:
                prefix = formatted_conf[namespace.prefix]

            join_separator = '\n'
            if namespace.join_separator in formatted_conf:
                join_separator = formatted_conf[namespace.join_separator].replace(r'\n', '\n')

            indentation = ''
            for _ in range(0, n_indentation + 1):
                indentation += ' '

            formatted_str = ''
            for cmd in self._command_list:
                if formatted_str:
                    formatted_str += join_separator
                formatted_str += indentation + prefix + cmd

            self.variables[var_name] = formatted_str

    def _derive_variables_for_template_path(self, workspace):
        """Define variables for template paths (for add_expand_vars)"""
        for template_name, _ in workspace.all_templates():
            expand_path = os.path.join(
                self.expander.expand_var(f'{{experiment_run_dir}}'),  # noqa: F541
                template_name)
            self.variables[template_name] = expand_path

    def _validate_experiment(self):
        """Perform validation of an experiment before performing actions with it

        This function is an entry point to validate various aspects of an
        experiment definition before it is used. It is expected to raise errors
        when validation fails.
        """
        if self.expander.workload_name not in self.workloads:
            raise ApplicationError(f'Workload {self.expander.workload_name} is not defined '
                                   f'as a workload of application {self.name}.')

    def add_expand_vars(self, workspace):
        """Add application specific expansion variables

        Applications require several variables to be defined to function properly.
        This method defines these variables, including:
        - command: set to the commands needed to execute the experiment
        - spack_setup: set to an empty string, so spack applications can override this
        """
        if not self._vars_are_expanded:
            self._validate_experiment()
            exec_graph = self._get_executable_graph(self.expander.workload_name)
            self._set_default_experiment_variables()
            self._set_input_path()
            self._define_commands(exec_graph)
            self._define_formatted_executables()

            self._derive_variables_for_template_path(workspace)
            self._vars_are_expanded = True

    def _inputs_and_fetchers(self, workload=None):
        """Extract all inputs for a given workload

        Take a workload name and extract all inputs for the workload.
        If the workload is set to None, extract all inputs for all workloads.
        """

        if self._input_fetchers is not None:
            return

        self._input_fetchers = {}

        workload_names = [workload] if workload else self.workloads.keys()

        inputs = {}
        for workload_name in workload_names:
            workload = self.workloads[workload_name]

            for input_file in workload['inputs']:
                if input_file not in self.inputs:
                    logger.die(
                        f'Workload {workload_name} references a non-existent input file '
                        f'{input_file}.\n'
                        f'Make sure this input file is defined before using it in a workload.'
                    )

                input_conf = self.inputs[input_file].copy()

                # Expand input value as it may be a var
                expanded_url = self.expander.expand_var(input_conf['url'])
                input_conf['url'] = expanded_url

                fetcher = ramble.fetch_strategy.URLFetchStrategy(**input_conf)

                file_name = os.path.basename(input_conf['url'])
                if not fetcher.extension:
                    fetcher.extension = spack.util.compression.extension(file_name)

                file_name = file_name.replace(f'.{fetcher.extension}', '')

                namespace = f'{self.name}.{workload_name}'

                inputs[file_name] = {'fetcher': fetcher,
                                     'namespace': namespace,
                                     'target_dir': input_conf['target_dir'],
                                     'extension': fetcher.extension,
                                     'input_name': input_file,
                                     'expand': input_conf['expand']
                                     }
        self._input_fetchers = inputs

    register_phase('mirror_inputs', pipeline='mirror')

    def _mirror_inputs(self, workspace, app_inst=None):
        """Mirror application inputs

        Perform mirroring of inputs within this application class.
        """
        self._inputs_and_fetchers(self.expander.workload_name)

        for input_file, input_conf in self._input_fetchers.items():
            mirror_paths = ramble.mirror.mirror_archive_paths(
                input_conf['fetcher'], os.path.join(self.name, input_file))
            fetch_dir = os.path.join(workspace.input_mirror_path, self.name)
            fs.mkdirp(fetch_dir)
            stage = ramble.stage.InputStage(input_conf['fetcher'], name=input_conf['namespace'],
                                            path=fetch_dir, mirror_paths=mirror_paths, lock=False)

            stage.cache_mirror(workspace.input_mirror_cache, workspace.input_mirror_stats)

    register_phase('get_inputs', pipeline='setup')

    def _get_inputs(self, workspace, app_inst=None):
        """Download application inputs

        Download application inputs into the proper directory within the workspace.
        """
        workload_namespace = self.expander.workload_namespace

        self._inputs_and_fetchers(self.expander.workload_name)

        for input_file, input_conf in self._input_fetchers.items():
            if not workspace.dry_run:
                input_vars = {self.keywords.input_name: input_conf['input_name']}
                input_namespace = workload_namespace + '.' + input_file
                input_path = self.expander.expand_var(input_conf['target_dir'],
                                                      extra_vars=input_vars)
                input_tuple = ('input-file', input_path)

                # Skip inputs that have already been cached
                if workspace.check_cache(input_tuple):
                    continue

                mirror_paths = ramble.mirror.mirror_archive_paths(
                    input_conf['fetcher'], os.path.join(self.name, input_file))

                with ramble.stage.InputStage(input_conf['fetcher'], name=input_namespace,
                                             path=self.expander.workload_input_dir,
                                             mirror_paths=mirror_paths) \
                        as stage:
                    stage.set_subdir(input_path)
                    stage.fetch()
                    if input_conf['fetcher'].digest:
                        stage.check()
                    stage.cache_local()

                    if input_conf['expand']:
                        try:
                            stage.expand_archive()
                        except spack.util.executable.ProcessError:
                            pass

                workspace.add_to_cache(input_tuple)
            else:
                logger.msg(f'DRY-RUN: Would download {input_conf["fetcher"].url}')

    def _prepare_license_path(self, workspace):
        self.license_path = os.path.join(workspace.shared_license_dir, self.name)
        self.license_file = os.path.join(self.license_path, self.license_inc_name)

        fs.mkdirp(self.license_path)

    register_phase('license_includes', pipeline='setup')

    def _license_includes(self, workspace, app_inst=None):
        logger.debug("Writing License Includes")
        self._prepare_license_path(workspace)

        action_funcs = ramble.util.env.action_funcs
        config_scopes = ramble.config.scopes()
        shell = ramble.config.get('config:shell')
        var_set = set()
        for scope in config_scopes:
            license_conf = ramble.config.config.get_config('licenses',
                                                           scope=scope)
            if license_conf:
                app_licenses = license_conf[self.name] if self.name \
                    in license_conf else {}

                for action, conf in app_licenses.items():
                    (env_cmds, var_set) = action_funcs[action](conf,
                                                               var_set,
                                                               shell=shell)

                    with open(self.license_file, 'w+') as f:
                        for cmd in env_cmds:
                            if cmd:
                                f.write(cmd + '\n')

    register_phase('make_experiments', pipeline='setup', run_after=['get_inputs'])

    def _make_experiments(self, workspace, app_inst=None):
        """Create experiment directories

        Create the experiment this application encapsulates. This includes
        creating the experiment run directory, rendering the necessary
        templates, and injecting the experiment into the workspace all
        experiments file.
        """

        experiment_run_dir = self.expander.experiment_run_dir
        fs.mkdirp(experiment_run_dir)

        exec_vars = {}

        for mod in self._modifier_instances:
            exec_vars.update(mod.modded_variables(self))

        for template_name, template_conf in workspace.all_templates():
            expand_path = os.path.join(experiment_run_dir, template_name)
            logger.msg(f'Writing template {template_name} to {expand_path}')

            with open(expand_path, 'w+') as f:
                f.write(self.expander.expand_var(template_conf['contents'],
                                                 extra_vars=exec_vars))
            os.chmod(expand_path, stat.S_IRWXU | stat.S_IRWXG
                     | stat.S_IROTH | stat.S_IXOTH)

        experiment_script = workspace.experiments_script
        experiment_script.write(self.expander.expand_var('{batch_submit}\n'))
        self.set_status(status=experiment_status.SETUP)

    def _clean_hash_variables(self, workspace, variables):
        """Cleanup variables to hash before computing the hash

        Perform some general cleanup operations on variables
        before hashing, to help give useful hashes.
        """

        # Purge workspace name, as this shouldn't affect the experiments
        if 'workspace_name' in variables:
            del variables['workspace_name']

        # Remove the workspace path from variable definitions before hashing
        for var in variables:
            if isinstance(variables[var], six.string_types):
                variables[var] = variables[var].replace(workspace.root + os.path.sep, '')

    def populate_inventory(self, workspace, force_compute=False, require_exist=False):
        """Populate this experiment's hash inventory

        If an inventory file exists, read it first.
        If it does not exist, compute it using the internal information.

        If force_compute is set to true, always compute and never read.

        Args:
            force_compute: Boolean that allows forces the inventory to be computed instead of read
                           Used in pipelines that should create the inventory, instead of
                           consuming it.
        """

        experiment_run_dir = self.expander.experiment_run_dir
        inventory_file = os.path.join(experiment_run_dir, self._inventory_file_name)

        if os.path.exists(inventory_file) and not force_compute:
            with open(inventory_file, 'r') as f:
                self.hash_inventory = spack.util.spack_json.load(f)

        else:
            # Clean up variables before hashing
            vars_to_hash = self.variables.copy()
            self._clean_hash_variables(workspace, vars_to_hash)

            # Build inventory of attributes
            attributes_to_hash = [
                ('variables', vars_to_hash),
                ('modifiers', self.modifiers),
                ('chained_experiments', self.chained_experiments),
                ('internals', self.internals),
                ('env_vars', self._env_variable_sets),
            ]

            self.hash_inventory['application_definition'] = \
                ramble.util.hashing.hash_file(self._file_path)

            added_mods = set()
            for mod_inst in self._modifier_instances:
                if mod_inst.name not in added_mods:
                    self.hash_inventory['modifier_definitions'].append(
                        {
                            'name': mod_inst.name,
                            'digest': ramble.util.hashing.hash_file(mod_inst._file_path)
                        }
                    )
                    added_mods.add(mod_inst.name)

            for attr, attr_dict in attributes_to_hash:
                self.hash_inventory['attributes'].append(
                    {
                        'name': attr,
                        'digest': ramble.util.hashing.hash_json(attr_dict),
                    }
                )

            # Build inventory of workspace templates
            for template_name, template_conf in workspace.all_templates():
                self.hash_inventory['templates'].append(
                    {
                        'name': template_name,
                        'digest': template_conf['digest'],
                    }
                )

            # Build inventory of inputs
            self._inputs_and_fetchers(self.expander.workload_name)

            for input_file, input_conf in self._input_fetchers.items():
                if input_conf['fetcher'].digest:
                    self.hash_inventory['inputs'].append(
                        {
                            'name': input_conf['input_name'],
                            'digest': input_conf['fetcher'].digest
                        }
                    )
                else:
                    self.hash_inventory['inputs'].append(
                        {
                            'name': input_conf['input_name'],
                            'digest': ramble.util.hashing.hash_string(input_conf['fetcher'].url),
                        }
                    )

        self.experiment_hash = ramble.util.hashing.hash_json(self.hash_inventory)

    register_phase('write_inventory', pipeline='setup', run_after=['make_experiments'])

    def _write_inventory(self, workspace, app_inst=None):
        """Build and write an inventory of an experiment

        Write an inventory file describing all of the contents of this
        experiment.
        """

        experiment_run_dir = self.expander.experiment_run_dir
        inventory_file = os.path.join(experiment_run_dir, self._inventory_file_name)

        with open(inventory_file, 'w+') as f:
            spack.util.spack_json.dump(self.hash_inventory, f)

    register_phase('archive_experiments', pipeline='archive')

    def _archive_experiments(self, workspace, app_inst=None):
        """Archive an experiment directory

        Perform the archiving action on an experiment.
        This includes capturing:
        - Rendered templates within the experiment directory
        - All files that contain a figure of merit or success criteria
        - Any files that match an archive pattern
        """
        import glob
        experiment_run_dir = self.expander.experiment_run_dir
        ws_archive_dir = workspace.latest_archive_path

        archive_experiment_dir = experiment_run_dir.replace(workspace.root,
                                                            ws_archive_dir)

        fs.mkdirp(archive_experiment_dir)

        # Copy all of the templates to the archive directory
        for template_name, _ in workspace.all_templates():
            src = os.path.join(experiment_run_dir, template_name)
            if os.path.exists(src):
                shutil.copy(src, archive_experiment_dir)

        # Copy all figure of merit files
        criteria_list = workspace.success_list
        analysis_files, _, _ = self._analysis_dicts(criteria_list)
        for file, file_conf in analysis_files.items():
            if os.path.exists(file):
                shutil.copy(file, archive_experiment_dir)

        # Copy all archive patterns
        archive_patterns = set(self.archive_patterns.keys())
        for mod in self._modifier_instances:
            for pattern in mod.archive_patterns.keys():
                archive_patterns.add(pattern)

        for pattern in archive_patterns:
            exp_pattern = self.expander.expand_var(pattern)
            for file in glob.glob(exp_pattern):
                shutil.copy(file, archive_experiment_dir)

        for file_name in [self._inventory_file_name, self._status_file_name]:
            file = os.path.join(experiment_run_dir, file_name)
            if os.path.exists(file):
                shutil.copy(file, archive_experiment_dir)

    register_phase('prepare_analysis', pipeline='analyze')

    def _prepare_analysis(self, workspace, app_inst=None):
        """Prepapre experiment for analysis extraction

        This function performs any actions that are necessary before the
        figures of merit, and success criteria can be properly extracted.

        This function can be overridden at the application level to perform
        application specific processing of the output.
        """
        pass

    register_phase('analyze_experiments', pipeline='analyze', run_after=['prepare_analysis'])

    def _analyze_experiments(self, workspace, app_inst=None):
        """Perform experiment analysis.

        This method will build up the fom_values dictionary. Its structure is:

        fom_values[context][fom]

        A fom can show up in any number of explicit contexts (including zero).
        If the number of explicit contexts is zero, the fom is associated with
        the default '(null)' context.

        Success is determined at analysis time as well. This happens by checking if:
         - At least one FOM is extracted
         AND
         - Any defined success criteria pass

        Success criteria are defined within the application.py, but can also be
        injected in a workspace config.
        """

        if self.get_status() == experiment_status.UNKNOWN.name and not workspace.dry_run:
            logger.die(
                f'Workspace status is {self.get_status()}\n'
                'Make sure your workspace is fully setup with\n'
                '    ramble workspace setup'
            )

        def format_context(context_match, context_format):

            context_val = {}
            if isinstance(context_format, six.string_types):
                for group in string.Formatter().parse(context_format):
                    if group[1]:
                        context_val[group[1]] = context_match[group[1]]

            context_string = context_format.replace('{', '').replace('}', '') \
                + ' = ' + context_format.format(**context_val)
            return context_string

        fom_values = {}

        criteria_list = workspace.success_list

        files, contexts, foms = self._analysis_dicts(criteria_list)

        # Iterate over files. We already know they exist
        for file, file_conf in files.items():

            # Start with no active contexts in a file.
            active_contexts = {}
            logger.debug(f'Reading log file: {file}')

            with open(file, 'r') as f:
                for line in f.readlines():
                    logger.debug(f'Line: {line}')

                    for criteria in file_conf['success_criteria']:
                        logger.debug('Looking for criteria %s' % criteria)
                        criteria_obj = criteria_list.find_criteria(criteria)
                        if criteria_obj.passed(line, self):
                            criteria_obj.mark_found()

                    for context in file_conf['contexts']:
                        context_conf = contexts[context]
                        context_match = context_conf['regex'].match(line)

                        if context_match:
                            context_name = \
                                format_context(context_match,
                                               context_conf['format'])
                            logger.debug('Line was: %s' % line)
                            logger.debug(f' Context match {context} -- {context_name}')

                            active_contexts[context] = context_name

                            if context_name not in fom_values:
                                fom_values[context_name] = {}

                    for fom in file_conf['foms']:
                        logger.debug(f'  Testing for fom {fom}')
                        fom_conf = foms[fom]
                        fom_match = fom_conf['regex'].match(line)

                        if fom_match:
                            fom_vars = {}
                            for k, v in fom_match.groupdict().items():
                                fom_vars[k] = v
                            fom_name = self.expander.expand_var(fom, extra_vars=fom_vars)

                            if fom_conf['group'] in fom_conf['regex'].groupindex:
                                logger.debug(' --- Matched fom %s' % fom_name)
                                fom_contexts = []
                                if fom_conf['contexts']:
                                    for context in fom_conf['contexts']:
                                        context_name = active_contexts[context] \
                                            if context in active_contexts \
                                            else 'null'
                                        fom_contexts.append(context_name)
                                else:
                                    fom_contexts.append('null')

                                for context in fom_contexts:
                                    if context not in fom_values:
                                        fom_values[context] = {}
                                    fom_val = fom_match.group(fom_conf['group'])
                                    fom_values[context][fom_name] = {
                                        'value': fom_val,
                                        'units': fom_conf['units'],
                                        'origin': fom_conf['origin'],
                                        'origin_type': fom_conf['origin_type']
                                    }

        # Test all non-file based success criteria
        for criteria_obj in criteria_list.all_criteria():
            if criteria_obj.file is None:
                if criteria_obj.passed(app_inst=self, fom_values=fom_values):
                    criteria_obj.mark_found()

        exp_ns = self.expander.experiment_namespace
        self.results = {'name': exp_ns}

        success = False
        for fom in fom_values.values():
            for value in fom.values():
                if 'origin_type' in value and value['origin_type'] == 'application':
                    success = True
        success = success and criteria_list.passed()

        self.results['N_REPEATS'] = self.repeats.n_repeats
        self.results['EXPERIMENT_CHAIN'] = self.chain_order.copy()

        if success:
            self.set_status(status=experiment_status.SUCCESS)
        else:
            self.set_status(status=experiment_status.FAILED)

        self.results['RAMBLE_STATUS'] = self.get_status()

        if success or workspace.always_print_foms:

            self.results['TAGS'] = list(self.experiment_tags)

            # Add defined keywords as top level keys
            for key in self.keywords.keys:
                if self.keywords.is_key_level(key):
                    self.results[key] = self.expander.expand_var_name(key)

            self.results['RAMBLE_VARIABLES'] = {}
            self.results['RAMBLE_RAW_VARIABLES'] = {}
            for var, val in self.variables.items():
                self.results['RAMBLE_RAW_VARIABLES'][var] = val
                if var not in self.keywords.keys or not self.keywords.is_key_level(var):
                    self.results['RAMBLE_VARIABLES'][var] = self.expander.expand_var(val)

            self.results['CONTEXTS'] = []

            for context, fom_map in fom_values.items():
                context_map = {'name': context, 'foms': []}

                for fom_name, fom in fom_map.items():
                    fom_copy = fom.copy()
                    fom_copy['name'] = fom_name
                    context_map['foms'].append(fom_copy)

                if context == 'null':
                    self.results['CONTEXTS'].insert(0, context_map)
                else:
                    self.results['CONTEXTS'].append(context_map)

        workspace.append_result(self.results)

    def calculate_statistics(self, workspace):
        """Calculate statistics for results of repeated experiments

        When repeated experiments are used, this method aggregates the results of
        each experiment's repeats and calculates statistics for each numeric FOM.

        If a FOM is non-numeric, no calculations are performed.

        Statistics are injected into the results file under the base experiment
        namespace.
        """

        def is_numeric(value):
            """Returns true if a fom value is numeric"""

            try:
                float(value)
                return True
            except ValueError:
                return False

        if not self.repeats.is_repeat_base:
            return

        repeat_experiments = {}
        repeat_foms = {}
        first_repeat_exp = ''

        # repeat_experiments dict = {repeat_experiment_namespace: {dict}}
        # repeat_foms dict = {context: {(fom_name, units, origin, origin_type): [list of values]}}
        # origin_type is generated as 'summary::stat_name'

        base_exp_name = self.expander.experiment_name
        base_exp_namespace = self.expander.experiment_namespace

        # Create a list of all repeats by inserting repeat index
        for n in range(1, self.repeats.n_repeats + 1):
            if (base_exp_name in self.experiment_set.chained_experiments.keys()
                and base_exp_name not in self.experiment_set.experiments.keys()):
                insert_idx = base_exp_name.find('.chain')
                repeat_exp_namespace = base_exp_name[:insert_idx] + f'.{n}' \
                    + base_exp_name[insert_idx:]
            else:
                base_exp_namespace = self.expander.experiment_namespace
                repeat_exp_namespace = f'{base_exp_namespace}.{n}'
            repeat_experiments[repeat_exp_namespace] = {}
            repeat_experiments[repeat_exp_namespace]['base_exp'] = base_exp_namespace
            if n == 1:
                first_repeat_exp = repeat_exp_namespace

        # Create initial results dict since analysis pipeline was skipped for base exp
        self.results = {'name': base_exp_namespace}
        self.results['N_REPEATS'] = self.repeats.n_repeats
        self.results['EXPERIMENT_CHAIN'] = self.chain_order.copy()

        # If repeat_success_strict is true, one failed experiment will fail the whole set
        # and statistics will not be calculated
        # If repeat_success_strict is false, statistics will be calculated for all successful
        # experiments
        repeat_success = False
        exp_success = []
        for exp in repeat_experiments.keys():
            if exp in self.experiment_set.experiments.keys():
                exp_inst = self.experiment_set.experiments[exp]
            elif exp in self.experiment_set.chained_experiments.keys():
                exp_inst = self.experiment_set.chained_experiments[exp]
            else:
                continue

            exp_success.append(exp_inst.get_status())

        if workspace.repeat_success_strict:
            if experiment_status.FAILED.name in exp_success:
                repeat_success = False
            else:
                repeat_success = True
        else:
            if experiment_status.SUCCESS.name in exp_success:
                repeat_success = True
            else:
                repeat_success = False

        if repeat_success:
            self.set_status(status=experiment_status.SUCCESS)
        else:
            self.set_status(status=experiment_status.FAILED)

        self.results['RAMBLE_STATUS'] = self.get_status()

        if repeat_success or workspace.always_print_foms:
            logger.debug(f'Calculating statistics for {self.repeats.n_repeats} repeats of '
                         f'{base_exp_name}')
            self.results['RAMBLE_VARIABLES'] = {}
            self.results['RAMBLE_RAW_VARIABLES'] = {}
            for var, val in self.variables.items():
                self.results['RAMBLE_RAW_VARIABLES'][var] = val
                self.results['RAMBLE_VARIABLES'][var] = self.expander.expand_var(val)
            self.results['CONTEXTS'] = []

            results = []

            # Iterate through repeat experiment instances, extract foms, and aggregate them
            for exp in repeat_experiments.keys():
                if exp in self.experiment_set.experiments.keys():
                    exp_inst = self.experiment_set.experiments[exp]
                elif exp in self.experiment_set.chained_experiments.keys():
                    exp_inst = self.experiment_set.chained_experiments[exp]
                else:
                    continue

                # When strict success is off for repeats (loose success), skip failed exps
                if (not workspace.repeat_success_strict
                    and exp_inst.results['RAMBLE_STATUS'] == 'FAILED'):
                    continue

                if 'CONTEXTS' in exp_inst.results:
                    for context in exp_inst.results['CONTEXTS']:
                        context_name = context['name']

                        if context_name not in repeat_foms.keys():
                            repeat_foms[context_name] = {}

                        for foms in context['foms']:
                            fom_key = (foms['name'], foms['units'],
                                       foms['origin'], foms['origin_type'])

                            # Stats will not be calculated for non-numeric foms so they're skipped
                            if is_numeric(foms['value']):
                                if fom_key not in repeat_foms[context_name].keys():
                                    repeat_foms[context_name][fom_key] = []
                                repeat_foms[context_name][fom_key].append(float(foms['value']))

            # Iterate through the aggregated foms, calculate stats, and insert into results
            for context, fom_dict in repeat_foms.items():
                context_map = {'name': context, 'foms': []}

                for fom_key, fom_values in fom_dict.items():
                    fom_name = fom_key[0]
                    fom_units = fom_key[1]
                    fom_origin = fom_key[2]

                    calcs = []

                    for statistic in ramble.util.stats.all_stats:
                        calcs.append(statistic.report(fom_values, fom_units))

                    for calc in calcs:
                        fom_dict = {'value': calc[0], 'units': calc[1], 'origin': fom_origin,
                                    'origin_type': calc[2], 'name': fom_name}

                        context_map['foms'].append(fom_dict)

                results.append(context_map)

            if results:
                self.results['CONTEXTS'] = results

        workspace.insert_result(self.results, first_repeat_exp)

    def _new_file_dict(self):
        """Create a dictionary to represent a new log file"""
        return {
            'success_criteria': [],
            'contexts': [],
            'foms': []
        }

    def _analysis_dicts(self, criteria_list):
        """Extract files that need to be analyzed.

        Process figures_of_merit, and return the manipulated dictionaries
        to allow them to be extracted.

        Additionally, ensure the success criteria list is complete.

        Returns:
            files (dict): All files that need to be processed
            contexts (dict): Any contexts that have been defined
            foms (dict): All figures of merit that need to be extracted
        """

        files = {}
        contexts = {}
        foms = {}

        # Add the application defined criteria
        criteria_list.flush_scope('application_definition')

        success_lists = [
            ('application_definition', self.success_criteria),
        ]

        logger.debug(f' Number of modifiers are: {len(self._modifier_instances)}')
        for mod in self._modifier_instances:
            success_lists.append(('modifier_definition', mod.success_criteria))

        for success_scope, success_list in success_lists:
            for criteria, conf in success_list.items():
                if conf['mode'] == 'string':
                    criteria_list.add_criteria(success_scope, criteria,
                                               conf['mode'], re.compile(
                                                   self.expander.expand_var(conf['match'])
                                               ),
                                               conf['file'])

        criteria_list.add_criteria(scope='application_definition',
                                   name='_application_function',
                                   mode='application_function')

        # Extract file paths for all criteria
        for criteria in criteria_list.all_criteria():
            log_path = self.expander.expand_var(criteria.file)
            if log_path not in files and os.path.exists(log_path):
                files[log_path] = self._new_file_dict()

            if log_path in files:
                files[log_path]['success_criteria'].append(criteria.name)

        # Remap fom / context / file data
        # Could push this into the language features in the future
        fom_definitions = self.figures_of_merit.copy()
        for fom, fom_def in fom_definitions.items():
            fom_def['origin'] = self.name
            fom_def['origin_type'] = 'application'

        fom_contexts = self.figure_of_merit_contexts.copy()
        for mod in self._modifier_instances:
            fom_contexts.update(mod.figure_of_merit_contexts)

            mod_vars = mod.modded_variables(self)

            for fom, fom_def in mod.figures_of_merit.items():
                fom_definitions[fom] = {'origin': f'{mod}', 'origin_type': 'modifier'}
                for attr in fom_def.keys():
                    if isinstance(fom_def[attr], list):
                        fom_definitions[fom][attr] = fom_def[attr].copy()
                    else:
                        fom_definitions[fom][attr] = self.expander.expand_var(fom_def[attr],
                                                                              mod_vars)

        for fom, conf in fom_definitions.items():
            log_path = self.expander.expand_var(conf['log_file'])
            if log_path not in files and os.path.exists(log_path):
                files[log_path] = self._new_file_dict()

            if log_path in files:
                logger.debug('Log = %s' % log_path)
                logger.debug('Conf = %s' % conf)
                if conf['contexts']:
                    files[log_path]['contexts'].extend(conf['contexts'])
                files[log_path]['foms'].append(fom)

            foms[fom] = {
                'regex': re.compile(r'%s' % self.expander.expand_var(conf['regex'])),
                'contexts': [],
                'group': conf['group_name'],
                'units': conf['units'],
                'origin': conf['origin'],
                'origin_type': conf['origin_type']
            }
            if conf['contexts']:
                foms[fom]['contexts'].extend(conf['contexts'])
                for context in conf['contexts']:
                    regex_str = \
                        self.expander.expand_var(fom_contexts[context]['regex'])
                    format_str = \
                        fom_contexts[context]['output_format']
                    contexts[context] = {
                        'regex': re.compile(r'%s' % regex_str),
                        'format': format_str
                    }

        return files, contexts, foms

    def read_status(self):
        """Read status from an experiment's status file, if possible.

        Set this experiment's status based on the status file in the experiment
        run directory, if it exists. If it doesn't exist, set its status to
        experiment_status.UNKNOWN
        """
        status_path = os.path.join(
            self.expander.expand_var_name(self.keywords.experiment_run_dir),
            self._status_file_name
        )

        if os.path.isfile(status_path):
            with open(status_path, 'r') as f:
                status_data = spack.util.spack_json.load(f)
            self.variables[self.keywords.experiment_status] = \
                status_data[self.keywords.experiment_status]
        else:
            self.set_status(experiment_status.UNKNOWN)

    def set_status(self, status=experiment_status.UNKNOWN):
        """Set the status of this experiment"""
        self.variables[self.keywords.experiment_status] = status.name

    def get_status(self):
        """Get the status of this experiment"""
        return self.variables[self.keywords.experiment_status]

    register_phase('write_status', pipeline='analyze', run_after=['analyze_experiments'])
    register_phase('write_status', pipeline='setup', run_after=['make_experiments'])

    def _write_status(self, workspace, app_inst=None):
        """Phase to write an experiment's ramble_status.json file"""

        status_data = {}
        status_data[self.keywords.experiment_status] = \
            self.expander.expand_var_name(self.keywords.experiment_status)

        exp_dir = self.expander.expand_var_name(self.keywords.experiment_run_dir)

        status_path = os.path.join(
            exp_dir,
            self._status_file_name
        )

        if os.path.exists(exp_dir):
            with open(status_path, 'w+') as f:
                spack.util.spack_json.dump(status_data, f)

    register_builtin('env_vars', required=True)

    def env_vars(self):
        command = []
        # ensure license variables are set / modified
        # Process one scope at a time, to ensure
        # highest-precedence scopes are processed last
        config_scopes = ramble.config.scopes()
        shell = ramble.config.get('config:shell')

        action_funcs = ramble.util.env.action_funcs

        for scope in config_scopes:
            license_conf = ramble.config.config.get_config('licenses',
                                                           scope=scope)
            if license_conf:
                if self.name in license_conf:
                    app_licenses = license_conf[self.name]
                    if app_licenses:
                        # Append logic to source file which contains the exports
                        command.append(f". {{license_input_dir}}/{self.license_inc_name}")

        # Process environment variable actions
        for env_var_set in self._env_variable_sets:
            for action, conf in env_var_set.items():
                (env_cmds, _) = action_funcs[action](conf,
                                                     set(),
                                                     shell=shell)

                for cmd in env_cmds:
                    if cmd:
                        command.append(cmd)

        for mod_inst in self._modifier_instances:
            for action, conf in mod_inst.all_env_var_modifications():
                (env_cmds, _) = action_funcs[action](conf,
                                                     set(),
                                                     shell=shell)

                for cmd in env_cmds:
                    if cmd:
                        command.append(cmd)

        return command

    def evaluate_success(self):
        """Hook for applications to evaluate custom success criteria

        Expected to perform analysis and return either true or false.
        """

        return True


class ApplicationError(RambleError):
    """
    Exception that is raised by applications
    """


class ExecutableNameError(RambleError):
    """
    Exception raised when a name collision in executables happens
    """


class FormattedExecutableError(ApplicationError):
    """
    Exception raise when there are issues defining formatted executables
    """


class PhaseCycleDetectedError(ApplicationError):
    """
    Exception raised when a cycle is detected while ordering phases
    """


class InvalidPhaseError(ApplicationError):
    """
    Exception raised when a phase is used but not defined
    """


class ChainCycleDetectedError(ApplicationError):
    """
    Exception raised when a cycle is detected in a defined experiment chain
    """


class InvalidChainError(ApplicationError):
    """
    Exception raised when a invalid chained experiment is defined
    """

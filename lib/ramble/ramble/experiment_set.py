# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from enum import Enum
import os
import math
import fnmatch

import ramble.expander
from ramble.expander import Expander
from ramble.namespace import namespace
import ramble.repository
import ramble.workspace
import ramble.keywords
import ramble.error
import ramble.renderer
import ramble.util.matrices
from ramble.util.logger import logger
import ramble.context

import spack.util.naming


class ExperimentSet(object):
    """Class to represent a full set of experiments

    This class contains logic to take sets of variable definitions and generate
    experiments from the variable hierarchy.

    Experiments are housed in the internal self.experiments dictionary. Keys of
    this dictionary are experiment names, while values are application
    instances.
    """

    # In order of lowest to highest precedence
    _contexts = Enum('contexts', ['global_conf', 'base', 'workspace',
                                  'application', 'workload', 'experiment',
                                  'required'])

    def __init__(self, workspace):
        self.keywords = ramble.keywords.keywords
        """Create experiment set class"""
        self.experiments = {}
        self.experiment_order = []
        self.chained_experiments = {}
        self.chained_order = []
        self._workspace = workspace
        self._context = {}

        for context in self._contexts:
            self._context[context] = ramble.context.Context()

        self.read_config_vars(workspace)

        # Set all workspace variables as base variables.
        workspace_context = ramble.context.Context()
        workspace_context.context_name = workspace.name
        workspace_context.variables = workspace.get_workspace_vars()
        workspace_context.env_variables = workspace.get_workspace_env_vars()
        workspace_context.formatted_executables = workspace.get_workspace_formatted_executables()
        workspace_context.internals = workspace.get_workspace_internals()
        workspace_context.modifiers = workspace.get_workspace_modifiers()
        workspace_context.zips = workspace.get_workspace_zips()

        try:
            self.keywords.check_reserved_keys(workspace_context.variables)
        except ramble.keywords.RambleKeywordError as e:
            raise RambleVariableDefinitionError(
                f'Workspace variable error: {e}'
            )

        self._set_context(self._contexts.workspace, workspace_context)

        # Set some base variables from the workspace definition.
        self.set_base_var(self.keywords.log_dir, workspace.log_dir)
        self.set_base_var(self.keywords.env_name,
                          Expander.expansion_str(self.keywords.application_name))

    def read_config_vars(self, workspace):
        global_context = ramble.context.Context()
        global_context.context_name = self._contexts.global_conf.name
        global_context.variables = self.get_config_vars(workspace)
        global_context.env_variables = self.get_config_env_vars(workspace)
        global_context.n_repeats = ramble.config.get('config:n_repeats')
        self._set_context(self._contexts.global_conf,
                          global_context)

    def get_config_vars(self, workspace):
        conf = ramble.config.config.get_config('config')
        if conf and namespace.variables in conf:
            site_vars = conf[namespace.variables]
            return site_vars
        return None

    def get_config_env_vars(self, workspace):
        conf = ramble.config.config.get_config('config')
        if conf and namespace.env_var in conf:
            site_env_vars = conf[namespace.env_var]
            return site_env_vars
        return None

    def set_base_var(self, var, val):
        """Set a base variable definition"""
        self._context[self._contexts.base].variables[var] = val

    def set_required_var(self, var, val):
        """Set a required variable definition"""
        self._context[self._contexts.required].variables[var] = val

    def _set_context(self, context, in_context):
        """Abstraction method to set context attributes"""
        if context not in self._contexts:
            raise RambleVariableDefinitionError(
                f'Context {context} is not a valid context.'
            )

        self._context[context] = in_context

    def set_application_context(self, app_context):
        """Set up current application context"""

        try:
            self.keywords.check_reserved_keys(app_context.variables)
        except ramble.keywords.RambleKeywordError as e:
            raise RambleVariableDefinitionError(
                f'In application {app_context.context_name}: {e}'
            )

        self._set_context(self._contexts.application, app_context)

    def set_workload_context(self, workload_context):
        """Set up current workload context"""

        try:
            self.keywords.check_reserved_keys(workload_context.variables)
        except ramble.keywords.RambleKeywordError as e:
            namespace = f'{self.application_namespace}.{workload_context.context_name}'
            raise RambleVariableDefinitionError(
                f'In workload {namespace}: {e}'
            )

        self._set_context(self._contexts.workload, workload_context)

    def set_experiment_context(self, experiment_context):
        """Set up current experiment context"""

        try:
            self.keywords.check_reserved_keys(experiment_context.variables)
        except ramble.keywords.RambleKeywordError as e:
            namespace = f'{self.workload_namespace}.{experiment_context.templates}'
            raise RambleVariableDefinitionError(
                f'In experiment {namespace}: {e}'
            )

        self._set_context(self._contexts.experiment, experiment_context)
        self._ingest_experiments()

    @property
    def application_namespace(self):
        """Property to return application namespace (application name)"""
        if self._context[self._contexts.application].context_name:
            return self._context[self._contexts.application].context_name
        return None

    @property
    def workload_namespace(self):
        """Property to return workload namespace

        Workload namespaces are of the form: application_name.workload_name
        """
        app_ns = self.application_namespace
        wl_ns = self._context[self._contexts.workload].context_name

        if app_ns and wl_ns:
            return f'{app_ns}.{wl_ns}'

        return None

    @property
    def experiment_namespace(self):
        """Property to return experiment namespace

        Experiment namespaces are of the form: application_name.workload_name.experiment_name
        """
        wl_ns = self.workload_namespace
        exp_ns = self._context[self._contexts.experiment].context_name

        if wl_ns and exp_ns:
            return f'{wl_ns}.{exp_ns}'
        return None

    def _compute_mpi_vars(self, expander, variables):
        """Compute required MPI variables

        Perform computation of required MPI variables, including:
        - n_ranks
        - n_nodes
        - processes_per_node
        - n_threads
        """
        n_ranks = variables[self.keywords.n_ranks] if self.keywords.n_ranks in \
            variables.keys() else None
        ppn = variables[self.keywords.processes_per_node] if self.keywords.processes_per_node \
            in variables.keys() else None
        n_nodes = variables[self.keywords.n_nodes] if self.keywords.n_nodes in \
            variables.keys() else None
        n_threads = variables[self.keywords.n_threads] if self.keywords.n_threads in \
            variables.keys() else None

        if n_ranks:
            n_ranks = int(expander.expand_var(n_ranks))

        if ppn:
            ppn = int(expander.expand_var(ppn))

        if n_nodes:
            n_nodes = int(expander.expand_var(n_nodes))

        if n_threads:
            n_threads = int(expander.expand_var(n_threads))

        if n_ranks and ppn:
            test_n_nodes = math.ceil(int(n_ranks) / int(ppn))

            if n_nodes and n_nodes < test_n_nodes:
                logger.error(f'n_nodes in {self.experiment_namespace} is {n_nodes} '
                             f'and should be {test_n_nodes}')
            elif not n_nodes:
                logger.debug(f'Defining n_nodes in {self.experiment_namespace}')
                variables[self.keywords.n_nodes] = test_n_nodes
        elif n_ranks and n_nodes:
            ppn = math.ceil(int(n_ranks) / int(n_nodes))
            logger.debug(f'Defining processes_per_node in {self.experiment_namespace}')
            variables[self.keywords.processes_per_node] = ppn
        elif ppn and n_nodes:
            n_ranks = ppn * n_nodes
            logger.debug(f'Defining n_ranks in {self.experiment_namespace}')
            variables[self.keywords.n_ranks] = n_ranks
        elif not n_nodes:
            variables[self.keywords.n_nodes] = 1

        if not n_threads:
            variables[self.keywords.n_threads] = 1

    def _prepare_experiment(self, exp_template_name, variables, context, repeats):
        """Prepare an experiment instance

        Create an experiment instance based on the input variables, context,
        repeats, and template name.

        Args:
            exp_template_name (str): Template name for experiments
            variables (dict): Dictionary of variables for this experiment
            context (Context): Context object for this experiment
            repeats (Repeats): Repeats object for this experiment

        Returns:
            (Application): Instance of an application class for this experiment
        """
        variables[self.keywords.env_path] = \
            os.path.join(self._workspace.software_dir,
                         Expander.expansion_str(self.keywords.env_name) + '.' +
                         Expander.expansion_str(self.keywords.workload_name))

        experiment_suffix = ''
        # After generating the base experiment, append the index to repeat experiments
        if repeats.repeat_index:
            experiment_suffix = f'.{repeats.repeat_index}'

        expander = ramble.expander.Expander(variables, self)
        self._compute_mpi_vars(expander, variables)
        final_app_name = expander.expand_var_name(self.keywords.application_name,
                                                  allow_passthrough=False)
        final_wl_name = expander.expand_var_name(self.keywords.workload_name,
                                                 allow_passthrough=False)
        final_exp_name = expander.expand_var(exp_template_name + experiment_suffix,
                                             allow_passthrough=False)

        variables[self.keywords.experiment_template_name] = (exp_template_name
                                                             + experiment_suffix)
        variables[self.keywords.application_name] = final_app_name
        variables[self.keywords.workload_name] = final_wl_name
        variables[self.keywords.experiment_name] = final_exp_name
        variables[self.keywords.experiment_index] = len(self.experiments) + 1

        experiment_namespace = expander.experiment_namespace
        variables[self.keywords.experiment_namespace] = experiment_namespace

        variables[self.keywords.log_file] = os.path.join('{experiment_run_dir}',
                                                         '{experiment_name}.out')

        variables[self.keywords.simplified_application_namespace] = \
            spack.util.naming.simplify_name(
                expander.expand_var_name(
                    self.keywords.application_namespace
                )
        )
        variables[self.keywords.simplified_workload_namespace] = \
            spack.util.naming.simplify_name(
                expander.expand_var_name(
                    self.keywords.workload_namespace
                )
        )
        variables[self.keywords.simplified_experiment_namespace] = \
            spack.util.naming.simplify_name(
                expander.expand_var_name(
                    self.keywords.experiment_namespace
                )
        )

        app_inst = ramble.repository.get(final_app_name).copy()
        app_inst.set_variables(variables, self)
        app_inst.set_env_variable_sets(context.env_variables)
        app_inst.set_internals(context.internals)
        app_inst.set_template(context.is_template)
        app_inst.repeats = repeats
        app_inst.set_chained_experiments(context.chained_experiments)
        app_inst.set_modifiers(context.modifiers)
        app_inst.set_tags(context.tags)
        app_inst.set_formatted_executables(context.formatted_executables)
        app_inst.read_status()

        return app_inst

    def _ingest_experiments(self):
        """Ingest experiments based on the current context.

        Merge all contexts, and render individual experiments. Track these
        experiments within this experiment set.

        Args:
            None

        Returns:
            None
        """

        no_var_contexts = [self._contexts.global_conf,
                           self._contexts.base, self._contexts.required]
        final_context = ramble.context.Context()

        for context in self._contexts:
            final_context.merge_context(self._context[context])

        for context in self._contexts:
            if context not in no_var_contexts:
                var_name = f'{context.name}_name'
                if self._context[context].context_name not in final_context.variables:
                    final_context.variables[var_name] = self._context[context].context_name

        # Set namespaces
        final_context.variables[self.keywords.application_namespace] = self.application_namespace
        final_context.variables[self.keywords.workload_namespace] = self.workload_namespace
        final_context.variables[self.keywords.experiment_namespace] = self.experiment_namespace

        # Set required variables for directories.
        final_context.variables[self.keywords.application_run_dir] = \
            os.path.join(self._workspace.experiment_dir,
                         Expander.expansion_str(self.keywords.application_name))
        final_context.variables[self.keywords.application_input_dir] = \
            os.path.join(self._workspace.input_dir,
                         Expander.expansion_str(self.keywords.application_name))

        final_context.variables[self.keywords.workload_run_dir] = \
            os.path.join(Expander.expansion_str(self.keywords.application_run_dir),
                         Expander.expansion_str(self.keywords.workload_name))
        final_context.variables[self.keywords.workload_input_dir] = \
            os.path.join(Expander.expansion_str(self.keywords.application_input_dir),
                         Expander.expansion_str(self.keywords.workload_name))

        final_context.variables[self.keywords.license_input_dir] = \
            os.path.join(self._workspace.shared_license_dir,
                         Expander.expansion_str(self.keywords.application_name))

        final_context.variables[self.keywords.experiment_run_dir] = \
            os.path.join(Expander.expansion_str(self.keywords.workload_run_dir),
                         Expander.expansion_str(self.keywords.experiment_name))

        experiment_template_name = final_context.variables[self.keywords.experiment_name]

        renderer = ramble.renderer.Renderer()

        render_group = ramble.renderer.RenderGroup('experiment', 'create')
        render_group.variables = final_context.variables
        render_group.zips = final_context.zips
        render_group.matrices = final_context.matrices
        render_group.n_repeats = final_context.n_repeats
        render_group.used_variables = set()

        excluded_experiments = set()
        if final_context.exclude:
            exclude_group = ramble.renderer.RenderGroup('experiment', 'exclude')
            exclude_group.copy_contents(render_group)
            perform_explicit_exclude = \
                exclude_group.from_dict(experiment_template_name,
                                        final_context.exclude)

            if perform_explicit_exclude:
                for exclude_exp_vars, _ in renderer.render_objects(exclude_group, remove=False):
                    expander = ramble.expander.Expander(exclude_exp_vars, self)
                    self._compute_mpi_vars(expander, exclude_exp_vars)
                    exclude_exp_name = expander.expand_var(experiment_template_name,
                                                           allow_passthrough=False)
                    excluded_experiments.add(exclude_exp_name)

        exclude_where = []
        if final_context.exclude:
            if namespace.where in final_context.exclude:
                exclude_where = final_context.exclude[namespace.where]

        tracking_group = ramble.renderer.RenderGroup('experiment', 'create')
        tracking_group.variables = final_context.variables
        tracking_group.zips = final_context.zips
        tracking_group.matrices = final_context.matrices
        tracking_group.n_repeats = final_context.n_repeats
        tracking_group.used_variables = set()

        used_variables = set()
        for tracking_vars, repeats in \
                renderer.render_objects(render_group, exclude_where=exclude_where,
                                        remove=False, fatal=False):
            app_inst = self._prepare_experiment(experiment_template_name,
                                                tracking_vars, final_context, repeats)

            final_exp_name = app_inst.expander.expand_var_name(self.keywords.experiment_namespace)

            exp_used_variables = app_inst.build_used_variables(self._workspace)
            used_variables = used_variables.union(exp_used_variables)
        render_group.used_variables = used_variables.copy()

        rendered_experiments = set()
        for experiment_vars, repeats in \
                renderer.render_objects(render_group, exclude_where=exclude_where):
            app_inst = self._prepare_experiment(experiment_template_name, experiment_vars,
                                                final_context, repeats)

            final_exp_name = app_inst.expander.expand_var_name(self.keywords.experiment_name)
            final_exp_namespace = \
                app_inst.expander.expand_var_name(self.keywords.experiment_namespace)

            # Skip explicitly excluded experiments
            if final_exp_name not in excluded_experiments:
                logger.debug(f'   Final name: {final_exp_namespace}')

                if final_exp_namespace in rendered_experiments:
                    logger.die(f'Experiment {final_exp_namespace} is not unique.')

                try:
                    self.keywords.check_required_keys(experiment_vars)
                except ramble.keywords.RambleKeywordError as e:
                    raise RambleVariableDefinitionError(
                        f'In experiment {final_exp_namespace}: {e}'
                    )

                rendered_experiments.add(final_exp_namespace)
                self.experiments[final_exp_namespace] = app_inst
                self.experiment_order.append(final_exp_namespace)

    def build_experiment_chains(self):
        base_experiments = self.experiment_order.copy()

        for experiment in base_experiments:
            instance = self.experiments[experiment]
            instance.create_experiment_chain(self._workspace)

    def all_experiment_tags(self):
        """Aggregate all tags from experiments in this experiment set

        Returns:
            (set): A set of all tags from the experiment set.
        """
        all_tags = set()
        for _, inst, _ in self.all_experiments():
            if inst.experiment_tags:
                for tag in inst.experiment_tags:
                    all_tags.add(tag)
        return all_tags

    def all_experiments(self):
        """Iterator over all experiments in this set"""
        count = 1

        for exp, inst in self.experiments.items():
            if inst.is_actionable():
                yield exp, inst, count
                count += 1

        for exp, inst in self.chained_experiments.items():
            if inst.is_actionable():
                yield exp, inst, count
                count += 1

    def num_experiments(self):
        """Return the number of total experiments in this set"""
        count = 0
        for _, _, _ in self.all_experiments():
            count += 1
        return count

    def num_filtered_experiments(self, filters):
        """Return the number of filtered experiments in this set"""

        return sum(1 for _ in self.filtered_experiments(filters))

    def filtered_experiments(self, filters):
        """Return a filtered set of all experiments based on a logical expression

        Exclusion takes overrides inclusion. If conflicting filters are
        provided which both include, and exclude the same experiment, the
        experiment will be excluded.

        Args:
            expression: A logical expression to evaluate, with each experiment
        Yields:
            exp: The name of the experiment, if expression results in True
            inst: An application instance representing the experiment
        """

        for exp, inst, idx in self.all_experiments():
            active = True

            if filters.include_where:
                for expression in filters.include_where:
                    if not inst.expander.evaluate_predicate(expression):
                        active = False

            if filters.exclude_where:
                for expression in filters.exclude_where:
                    if inst.expander.evaluate_predicate(expression):
                        active = False

            if filters.tags:
                if not inst.has_tags(filters.tags):
                    active = False

            if active and inst.is_actionable():
                yield exp, inst, idx

    def add_chained_experiment(self, name, instance):
        if name in self.chained_experiments.keys():
            raise RambleExperimentSetError('Cannot add already defined chained ' +
                                           f'experiment {name} to this experiment set.')
        self.chained_experiments[name] = instance
        self.chained_order.append(name)

    def search_primary_experiments(self, pattern):
        """Search primary experiments using a glob syntax.

        NOTE: This does not search experiments defined in an experiment chain
        """
        return fnmatch.filter(self.experiment_order, pattern)

    def get_experiment(self, experiment):
        if experiment in self.experiments.keys():
            return self.experiments[experiment]
        if experiment in self.chained_experiments.keys():
            return self.chained_experiments[experiment]
        return None

    def get_var_from_experiment(self, experiment, variable):
        """Lookup a variable in a given experiment

        Does not error if invalid values are passed in, to allow @ symbol to
        pass through to rendered content.

        Args:
            experiment: A fully qualified experiment name (application.workload.experiment)
            variable: Name of variable to look up
        """

        if experiment not in self.experiments.keys():
            return None

        exp_app = self.experiments[experiment]

        return exp_app.expander.expand_var(variable)


class RambleExperimentSetError(ramble.error.RambleError):
    """Super class for all experiment set errors"""


class RambleVariableDefinitionError(RambleExperimentSetError):
    """Error when a ramble variable definition is invalid"""

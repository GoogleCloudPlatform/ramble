# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from enum import Enum
import os
import itertools
import math

import llnl.util.tty as tty

import ramble.expander
from ramble.expander import Expander
import ramble.repository
import ramble.workspace
import ramble.keywords
import ramble.error


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

    keywords = ramble.keywords.keywords

    def __init__(self, workspace):
        """Create experiment set class"""
        self.experiments = {}
        self._workspace = workspace

        self._env_variables = {}
        self._variables = {}
        self._context_names = {}

        for context in self._contexts:
            self._context_names[context] = None
            self._env_variables[context] = None
            self._variables[context] = None

        self._variables[self._contexts.base] = {}
        self._variables[self._contexts.required] = {}

        self._matrices = {
            self._contexts.experiment: None
        }

        self.read_config_vars(workspace)

        # Set all workspace variables as base variables.
        workspace_vars = workspace.get_workspace_vars()
        workspace_env_vars = workspace.get_workspace_env_vars()

        try:
            self.keywords.check_reserved_keys(workspace_vars)
        except ramble.keywords.RambleKeywordError as e:
            raise RambleVariableDefinitionError(
                f'Workspace variable error: {e}'
            )

        self._set_context(self._contexts.workspace,
                          workspace.name,
                          workspace_vars,
                          workspace_env_vars)

        # Set some base variables from the workspace definition.
        self.set_base_var(self.keywords.mpi_command, workspace.mpi_command)
        self.set_base_var(self.keywords.log_dir, workspace.log_dir)
        self.set_base_var(self.keywords.batch_submit, workspace.batch_submit)
        self.set_base_var(self.keywords.spec_name,
                          Expander.expansion_str(self.keywords.application_name))

    def read_config_vars(self, workspace):
        site_vars = self.get_config_vars(workspace)
        site_env_vars = self.get_config_env_vars(workspace)
        site_name = self._contexts.global_conf.name
        self._set_context(self._contexts.global_conf,
                          site_name,
                          site_vars,
                          site_env_vars)

    def get_config_vars(self, workspace):
        conf = ramble.config.config.get_config('config')
        if conf and ramble.workspace.namespace.variables in conf:
            site_vars = conf[ramble.workspace.namespace.variables]
            return site_vars
        return None

    def get_config_env_vars(self, workspace):
        conf = ramble.config.config.get_config('config')
        if conf and ramble.workspace.namespace.env_var in conf:
            site_env_vars = conf[ramble.workspace.namespace.env_var]
            return site_env_vars
        return None

    def set_base_var(self, var, val):
        """Set a base variable definition"""
        self._variables[self._contexts.base][var] = val

    def set_required_var(self, var, val):
        """Set a required variable definition"""
        self._variables[self._contexts.required][var] = val

    def _set_context(self, context, name, variables, env_variables):
        """Abstraction method to set context attributes"""
        if context not in self._contexts:
            raise RambleVariableDefinitionError(
                f'Context {context} is not a valid context.'
            )

        self._context_names[context] = name
        self._variables[context] = variables
        self._env_variables[context] = env_variables

    def set_application_context(self, application_name,
                                application_variables,
                                application_env_variables):
        """Set up current application context"""

        try:
            self.keywords.check_reserved_keys(application_variables)
        except ramble.keywords.RambleKeywordError as e:
            raise RambleVariableDefinitionError(
                f'In application {application_name}: {e}'
            )

        self._set_context(self._contexts.application, application_name,
                          application_variables, application_env_variables)

    def set_workload_context(self, workload_name,
                             workload_variables,
                             workload_env_variables):
        """Set up current workload context"""

        try:
            self.keywords.check_reserved_keys(workload_variables)
        except ramble.keywords.RambleKeywordError as e:
            namespace = f'{self.application_namespace}.{workload_name}'
            raise RambleVariableDefinitionError(
                f'In workload {namespace}: {e}'
            )

        self._set_context(self._contexts.workload, workload_name,
                          workload_variables, workload_env_variables)

    def set_experiment_context(self, experiment_template,
                               experiment_variables,
                               experiment_env_variables,
                               experiment_matrices):
        """Set up current experiment context"""

        try:
            self.keywords.check_reserved_keys(experiment_variables)
        except ramble.keywords.RambleKeywordError as e:
            namespace = f'{self.workload_namespace}.{experiment_template}'
            raise RambleVariableDefinitionError(
                f'In experiment {namespace}: {e}'
            )

        self._set_context(self._contexts.experiment, experiment_template,
                          experiment_variables, experiment_env_variables)

        self._matrices[self._contexts.experiment] = experiment_matrices
        self._ingest_experiments()

    @property
    def application_namespace(self):
        """Property to return application namespace (application name)"""
        if self._context_names[self._contexts.application]:
            return self._context_names[self._contexts.application]
        return None

    @property
    def workload_namespace(self):
        """Property to return workload namespace

        Workload namespaces are of the form: application_name.workload_name
        """
        app_ns = self.application_namespace
        wl_ns = self._context_names[self._contexts.workload]

        if app_ns and wl_ns:
            return f'{app_ns}.{wl_ns}'

        return None

    @property
    def experiment_namespace(self):
        """Property to return experiment namespace

        Experiment namespaces are of the form: application_name.workload_name.experiment_name
        """
        wl_ns = self.workload_namespace
        exp_ns = self._context_names[self._contexts.experiment]

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
                tty.error('n_nodes in %s is %s and should be %s' %
                          (self.experiment_namespace, n_nodes,
                           test_n_nodes))
            elif not n_nodes:
                tty.debug('Defining n_nodes in %s' %
                          self.experiment_namespace)
                variables[self.keywords.n_nodes] = test_n_nodes
        elif n_ranks and n_nodes:
            ppn = math.ceil(int(n_ranks) / int(n_nodes))
            tty.debug('Defining processes_per_node in %s' %
                      self.experiment_namespace)
            variables[self.keywords.processes_per_node] = ppn
        elif ppn and n_nodes:
            n_ranks = ppn * n_nodes
            tty.debug('Defining n_ranks in %s' %
                      self.experiment_namespace)
            variables[self.keywords.n_ranks] = n_ranks
        elif not n_nodes:
            variables[self.keywords.n_nodes] = 1

        if not n_threads:
            variables[self.keywords.n_threads] = 1

    def _ingest_experiments(self):
        """Ingest experiments based on the current context.

        Interally collects all matrix and vector variables.

        Matrices are processed first.

        Vectors in the same matrix are crossed, sibling matrices are zipped.
        All matrices are required to result in the same number of elements, but
        not be the same shape.

        Matrix elements are only allowed to be the names of variables. These
        variables are required to be vectors.

        After matrices are processed, any remaining vectors are zipped
        together. All vectors are required to be of the same size.

        The resulting zip of vectors is then crossed with all of the matrices
        to build a final list of experiments.

        After collecting the matrices, this method modifies generates new
        experiments and injects them into the self.experiments dictionary.

        Inputs:
            - None
        Returns:
            - None
        """

        context_variables = {}
        ordered_env_variables = []

        for context in self._contexts:
            if context in self._variables and self._variables[context]:
                context_variables.update(self._variables[context])
            if context in self._env_variables and self._env_variables[context]:
                ordered_env_variables.append(self._env_variables[context])

        for context in self._contexts:
            var_name = f'{context.name}_name'
            context_variables[var_name] = self._context_names[context]

        # Set namespaces
        context_variables['application_namespace'] = self.application_namespace
        context_variables['workload_namespace'] = self.workload_namespace
        context_variables['experiment_namespace'] = self.experiment_namespace

        # Set required variables for directories.
        context_variables[self.keywords.application_run_dir] = \
            os.path.join(self._workspace.experiment_dir,
                         Expander.expansion_str(self.keywords.application_name))
        context_variables[self.keywords.application_input_dir] = \
            os.path.join(self._workspace.input_dir,
                         Expander.expansion_str(self.keywords.application_name))

        context_variables[self.keywords.workload_run_dir] = \
            os.path.join(Expander.expansion_str(self.keywords.application_run_dir),
                         Expander.expansion_str(self.keywords.workload_name))
        context_variables[self.keywords.workload_input_dir] = \
            os.path.join(Expander.expansion_str(self.keywords.application_input_dir),
                         Expander.expansion_str(self.keywords.workload_name))

        context_variables[self.keywords.experiment_run_dir] = \
            os.path.join(Expander.expansion_str(self.keywords.workload_run_dir),
                         Expander.expansion_str(self.keywords.experiment_name))

        experiment_template_name = context_variables[self.keywords.experiment_name]
        new_experiments = []
        matrix_experiments = []

        if self._matrices[self._contexts.experiment]:
            """ Matrix syntax is:
               matrix:
               - <var1>
               - <var2>
               - [1, 2, 3, 4] # inline vector
               matrices:
               - matrix_a:
                 - <var1>
                 - <var2>
               - matrix:b:
                 - <var_3>
                 - <var_4>

                 Matrices consume vector variables.
            """

            # Perform some error checking
            last_size = -1
            matrix_vars = set()
            matrix_vectors = []
            matrix_variables = []
            for matrix in self._matrices[self._contexts.experiment]:
                matrix_size = 1
                vectors = []
                variable_names = []
                for var in matrix:
                    if var in matrix_vars:
                        tty.die('Variable %s has been used in multiple matrices.\n' % var
                                + 'Ensure each variable is only used once across all matrices')
                    matrix_vars.add(var)

                    if var not in context_variables:
                        tty.die(f'In experiment {context_variables["experiment_name"]}'
                                + f' variable {var} has not been defined yet.')

                    if not isinstance(context_variables[var], list):
                        tty.die(f'In experiment {context_variables["experiment_name"]}'
                                + f' variable {var} does not refer to a vector.')

                    matrix_size = matrix_size * len(context_variables[var])

                    vectors.append(context_variables[var])
                    variable_names.append(var)

                    # Remove the variable, so it's not proccessed as a vector anymore.
                    del context_variables[var]

                if last_size == -1:
                    last_size = matrix_size

                if last_size != matrix_size:
                    tty.die('Matrices defined in experiment '
                            + f'{context_variables["experiment_name"]}'
                            + ' do not result in the same number of elements.')

                matrix_vectors.append(vectors)
                matrix_variables.append(variable_names)

            # Create the empty initial dictionairies
            matrix_experiments = []
            for _ in range(matrix_size):
                matrix_experiments.append({})

            # Generate all of the exp var dicts
            for names, vectors in zip(matrix_variables, matrix_vectors):
                for exp_idx, entry in enumerate(itertools.product(*vectors)):
                    for name_idx, name in enumerate(names):
                        matrix_experiments[exp_idx][name] = entry[name_idx]

        # After matrices have been processed, extract any remaining vector variables
        vector_vars = {}

        # Extract vector variables
        max_vector_size = 0
        for var, val in context_variables.items():
            if isinstance(val, list):
                vector_vars[var] = val.copy()
                max_vector_size = max(len(val), max_vector_size)

        if vector_vars:
            # Check that sizes are the same
            for var, val in vector_vars.items():
                if len(val) != max_vector_size:
                    tty.die(f'Size of vector {var} is not'
                            + ' the same as max %s' % len(val)
                            + f'. In experiment {context_variables["experiment_name"]}.')

            # Iterate over the vector length, and set the value in the
            # experiment dict to the index value.
            for i in range(0, max_vector_size):
                exp_vars = {}
                for var, val in vector_vars.items():
                    exp_vars[var] = val[i]

                if matrix_experiments:
                    for matrix_experiment in matrix_experiments:
                        for var, val in matrix_experiment.items():
                            exp_vars[var] = val

                        new_experiments.append(exp_vars.copy())
                else:
                    new_experiments.append(exp_vars.copy())

        elif matrix_experiments:
            new_experiments = matrix_experiments
        else:
            # Ensure at least one experiment is rendered, if everything was a scalar
            new_experiments.append({})

        rendered_experiments = set()
        for exp in new_experiments:
            tty.debug('Rendering experiment:')
            for var, val in exp.items():
                context_variables[var] = val
            context_variables[self.keywords.spack_env] = \
                os.path.join(self._workspace.software_dir,
                             Expander.expansion_str(self.keywords.spec_name) + '.' +
                             Expander.expansion_str(self.keywords.workload_name))

            experiment_vars = context_variables.copy()

            expander = ramble.expander.Expander(experiment_vars, self)
            self._compute_mpi_vars(expander, experiment_vars)
            final_app_name = expander.expand_var(
                Expander.expansion_str(self.keywords.application_name))
            final_wl_name = expander.expand_var(
                Expander.expansion_str(self.keywords.workload_name))
            final_exp_name = expander.expand_var(experiment_template_name)

            experiment_vars[self.keywords.application_name] = final_app_name
            experiment_vars[self.keywords.workload_name] = final_wl_name
            experiment_vars[self.keywords.experiment_name] = final_exp_name

            experiment_namespace = expander.experiment_namespace

            log_file = expander.expand_var(
                os.path.join(Expander.expansion_str(self.keywords.experiment_run_dir),
                             Expander.expansion_str(self.keywords.experiment_name) + '.out'))
            experiment_vars['log_file'] = log_file

            tty.debug('   Exp vars: %s' % exp)
            tty.debug('   Final name: %s' % final_exp_name)

            if final_exp_name in rendered_experiments:
                tty.die('Experiment %s is not unique.' % final_exp_name)
            rendered_experiments.add(final_exp_name)

            try:
                self.keywords.check_required_keys(experiment_vars)
            except ramble.keywords.RambleKeywordError as e:
                raise RambleVariableDefinitionError(
                    f'In experiment {self.experiment_namespace}: {e}'
                )

            app_inst = ramble.repository.get(final_app_name)
            app_inst.set_variables(experiment_vars, self)
            app_inst.set_env_variable_sets(ordered_env_variables)
            app_inst.add_expand_vars(self._workspace)

            self.experiments[experiment_namespace] = app_inst

    def all_experiments(self):
        """Iteartor over all experiments in this set"""
        for exp, inst in self.experiments.items():
            yield exp, inst

    def get_experiment(self, experiment):
        if experiment in self.experiments.keys():
            return self.experiments[experiment]
        return None

    def get_var_from_experiment(self, experiment, variable):
        """Lookup a variable in a given experiment

        Does not error if invalid values are passed in, to allow @ symbol to
        pass through to rendered content.

        Args:
          experiment: A fully qualified experiment name (application.workload.experiment)
          varialbe: Name of variable to look up
        """

        if experiment not in self.experiments.keys():
            return None

        exp_app = self.experiments[experiment]

        return exp_app.expander.expand_var(variable)


class RambleExperimentSetError(ramble.error.RambleError):
    """Super class for all experiment set errors"""


class RambleVariableDefinitionError(RambleExperimentSetError):
    """Error when a ramble variable definition is invalid"""

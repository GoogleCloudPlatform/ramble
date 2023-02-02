# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
import math
import string
import ast
import six
import operator
import itertools

import llnl.util.tty as tty

import ramble.error

supported_math_operators = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow:
    operator.pow, ast.BitXor: operator.xor, ast.USub: operator.neg
}


class ExpansionDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


class Expander(object):
    """A class that will track and expand keyword arguments

    This class will track variables and their definitions, to allow for
    expansion within string.

    The variables can come from workspace variables, software stack variables,
    and experiment variables.

    Additionally, math will be evaluated as part of expansion.
    """

    app_name_key = 'application_name'
    app_run_dir_key = 'application_run_dir'
    app_input_dir_key = 'application_input_dir'

    wl_name_key = 'workload_name'
    wl_run_dir_key = 'workload_run_dir'
    wl_input_dir_key = 'workload_input_dir'
    spack_key = 'spack_env'

    exp_name_key = 'experiment_name'
    exp_run_dir_key = 'experiment_run_dir'

    ranks_key = 'n_ranks'
    ppn_key = 'processes_per_node'
    nodes_key = 'n_nodes'
    threads_key = 'n_threads'

    mpi_key = 'mpi_command'
    batch_submit_key = 'batch_submit'
    spec_name_key = 'spec_name'

    log_dir_key = 'log_dir'
    log_file_key = 'log_file'
    err_file_key = 'err_file'

    def __init__(self, workspace):
        self.current_level = 'base'
        self._workspace = workspace

        self._expansion_dict = None

        self.workspace_vars = self._workspace.get_workspace_vars().copy()

        self.application_vars = None
        self.workload_vars = None
        self.experiment_vars = None
        self.experiment_matrices = None

        self.workspace_env_vars = self._workspace.get_workspace_env_vars()
        self.workspace_env_vars = self.workspace_env_vars.copy() if \
            self.workspace_env_vars else None

        self.application_env_vars = None
        self.workload_env_vars = None
        self.experiment_env_vars = None

        self.base_vars = {}
        self.package_paths = {}
        self.set_var(self.log_dir_key, self._workspace.log_dir)
        self.set_var(self.mpi_key, self._workspace.mpi_command)
        self.set_var(self.batch_submit_key,
                     self._workspace.batch_submit)

    def get_level_vars(self, level=None):
        cur_level = self.current_level
        if level:
            cur_level = level

        if cur_level == 'application':
            return self.application_vars
        elif cur_level == 'workload':
            return self.workload_vars
        elif cur_level == 'experiment':
            return self.experiment_vars
        else:  # Default to returning the base_vars dict
            return self.base_vars

    def set_var(self, var, val, level=None):
        level_vars = self.get_level_vars(level)

        if level_vars is None:
            tty.die('Level variables for %s not defined yet' % level)

        level_vars[var] = val
        self._expansion_dict = None

    def remove_var(self, var, level=None):
        level_vars = self.get_level_vars(level)

        if var in level_vars:
            del level_vars[var]

        self._expansion_dict = None

    def get_var(self, var, level=None):
        level_vars = self.get_level_vars(level)

        if var in level_vars:
            return level_vars[var]

        return None

    def set_package_path(self, package, path):
        self.package_paths['%s' % package] = path
        self._expansion_dict = None

    def remove_package_path(self, package):
        key = '%s_path' % package
        if key in self.package_paths:
            del self.package_paths[key]
        self._expansion_dict = None

    def get_package_path(self, package):
        key = '%s_path' % package
        if key in self.package_paths:
            return self.package_paths[key]
        return None

    def set_application(self, app_name):
        tty.debug('Expander: Setting app name %s' % app_name)
        self.flush_context()
        self.set_var(self.app_name_key, app_name)
        self.set_var(self.app_run_dir_key,
                     os.path.join(self._workspace.experiment_dir, app_name))

        self.set_var(self.app_input_dir_key,
                     os.path.join(self._workspace.input_dir, app_name))

        # The default spec name used is the same as the application name
        self.set_var(self.spec_name_key, app_name, level='base')

    @property
    def application_name(self):
        app_name = self._find_key(self.app_name_key)

        if app_name:
            return self.expand_var(app_name)
        return None

    @property
    def application_run_dir(self):
        app_dir = self._find_key(self.app_run_dir_key)

        if app_dir:
            return self.expand_var(app_dir)
        return None

    @property
    def application_input_dir(self):
        app_input_dir = self._find_key(self.app_input_dir_key)

        if app_input_dir:
            return self.expand_var(app_input_dir)
        return None

    def set_workload(self, wl_name):
        tty.debug('Expander: Setting wl name %s' % wl_name)
        if not self.application_name:
            raise ApplicationNotDefinedError('Application is not ' +
                                             'set correctly')

        self.set_var(self.wl_name_key, wl_name)
        self.set_var(self.wl_run_dir_key,
                     os.path.join(self.application_run_dir,
                                  self.workload_name))

        self.set_var(self.wl_input_dir_key,
                     os.path.join(self.application_input_dir,
                                  self.workload_name))

        self.remove_var(self.exp_name_key)
        self.remove_var(self.exp_run_dir_key)
        self.workload_vars = None
        self.experiment_vars = None

    @property
    def workload_name(self):
        wl_name = self._find_key(self.wl_name_key)

        if wl_name:
            return self.expand_var(wl_name)
        return None

    @property
    def workload_run_dir(self):
        wl_run_dir = self._find_key(self.wl_run_dir_key)

        if wl_run_dir:
            return self.expand_var(wl_run_dir)
        return None

    @property
    def workload_input_dir(self):
        wl_input_dir = self._find_key(self.wl_input_dir_key)

        if wl_input_dir:
            return self.expand_var(wl_input_dir)
        return None

    @property
    def workload_namespace(self):
        app_name = self.application_name
        wl_name = self.workload_name
        if app_name and wl_name:
            return '%s.%s' % (app_name, wl_name)
        return None

    @property
    def spec_namespace(self):
        app_name = self.expand_var('{spec_name}')
        wl_name = self.workload_name
        if app_name and wl_name:
            return '%s.%s' % (app_name, wl_name)
        return None

    def set_experiment(self, exp_name):
        tty.debug('Expander: Setting exp name %s' % exp_name)
        if not self.workload_name:
            raise WorkloadNotDefinedError('Workload is not set correctly.')

        self.set_var(self.exp_name_key, exp_name)

    """Finalize the setup of this experiment

    Perform the last steps of setting up an experiment.

    Compute the mpi variables that are required, and construct the experiment name,
    run directory, and log file paths.

    Inputs:
        None
    Returns:
        None
    """
    def _finalize_experiment(self):
        self._compute_mpi_vars()

        # Remove potentially generated experiment name
        self.remove_var(self.exp_name_key, level='experiment')

        # Generate a new experiment name, from the template.
        # Name template would be stored in base_vars, while
        # generated name is stored in experiment_vars
        self.set_var(self.exp_name_key, self.expand_var('{' + self.exp_name_key + '}'),
                     level='experiment')

        self.set_var(self.exp_run_dir_key,
                     os.path.join(self.workload_run_dir, self.experiment_name))

        self.set_var(self.log_file_key,
                     os.path.join(self.experiment_run_dir,
                                  '%s.out' % self.experiment_name))

        self.set_var(self.err_file_key,
                     os.path.join(self.experiment_run_dir,
                                  '%s.err' % self.experiment_name))

    """Render experiments by processing vector and matrix variables.

    Interally collects all matrix and vector variables.

    Before processing vectors and matrices, pull out vector spec_names, if they exist.
    These are crossed with the remaining experiments.

    Matrices are processed second.
    Vectors in the same matrix are crossed, sibling matrices are zipped.
    All matrices are required to result in the same number of elements, but not
    be the same shape.
    Matrix elements are only allowed to be the names of variables. These variables
    are required to be vectors.

    After matrices are processed, any remaining vectors are zipped together.
    All vectors are required to be of the same size.

    The resulting zip of vectors is then crossed with all of the matrices to
    build a final list of experiments.

    After collecting the matrices, this method modifies the internal expander
    data structures, and yields nothing. This allows the experiments to be
    iterated over without having to perform the expansion again.

        Inputs:
            - extra_vars: (Dict) Extra variables to use when expanding variables
        Returns:
            - Nothing.
    """
    def rendered_experiments(self, extra_vars=None):
        all_expansions = self.get_expansion_dict(extra_vars)

        experiments = []
        matrix_experiments = []

        if self.experiment_matrices:
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
            for matrix in self.experiment_matrices:
                matrix_size = 1
                vectors = []
                variable_names = []
                for var in matrix:
                    if var in matrix_vars:
                        tty.die('Variable %s has been used in multiple matrices.\n' % var
                                + 'Ensure each variable is only used once across all matrices')
                    matrix_vars.add(var)

                    if var not in all_expansions:
                        tty.die('In experiment %s' % self.experiment_name
                                + ' variable %s has not been defined yet.' % var)

                    if not isinstance(all_expansions[var], list):
                        tty.die('In experiment %s' % self.experiment_name
                                + ' variable %s does not refer to a vector.' % var)

                    matrix_size = matrix_size * len(all_expansions[var])

                    tty.debug('MATRIX USING VAR: %s' % var)
                    vectors.append(all_expansions[var])
                    variable_names.append(var)

                    # Remove the variable, so it's not proccessed as a vector anymore.
                    del all_expansions[var]

                if last_size == -1:
                    last_size = matrix_size

                if last_size != matrix_size:
                    tty.die('Matrices defined in experiment %s do not ' % self.experiment_name
                            + 'result in the same number of elements.')

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
        for var, val in all_expansions.items():
            if isinstance(val, list):
                vector_vars[var] = val.copy()
                max_vector_size = max(len(val), max_vector_size)

        if vector_vars:
            # Check that sizes are the same
            for var, val in vector_vars.items():
                if len(val) != max_vector_size:
                    tty.die('Size of vector %s is not' % var
                            + ' the same as max %s' % len(val)
                            + '. In experiment %s' % self.experiment_name)

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

                        experiments.append(exp_vars.copy())
                else:
                    experiments.append(exp_vars.copy())

        elif matrix_experiments:
            experiments = matrix_experiments
        else:
            # Ensure at least one experiment is rendered, if everything was a scalar
            experiments.append({})

        rendered_experiments = set()
        for exp in experiments:
            tty.debug('Rendering experiment:')
            for var, val in exp.items():
                self.set_var(var, val, level='experiment')
            self.set_var(self.spack_key,
                         os.path.join(self._workspace.software_dir,
                                      '%s.%s' % ('{spec_name}', all_expansions[self.wl_name_key])),
                         level='experiment')

            self._finalize_experiment()
            final_exp_name = self.expand_var('{' + self.exp_name_key + '}')
            tty.debug('   Exp vars: %s' % exp)
            tty.debug('   Final name: %s' % final_exp_name)

            if final_exp_name in rendered_experiments:
                tty.die('Experiment %s is not unique.' % final_exp_name)
            rendered_experiments.add(final_exp_name)

            yield

    def set_application_env_vars(self, application_env_vars):
        if application_env_vars:
            self.application_env_vars = application_env_vars.copy()
        else:
            self.application_env_vars = None
        self.workload_env_vars = None
        self.experiment_env_vars = None

    def set_workload_env_vars(self, workload_env_vars):
        if workload_env_vars:
            self.workload_env_vars = workload_env_vars.copy()
        else:
            self.workload_env_vars = None
        self.experiment_env_vars = None

    def set_experiment_env_vars(self, experiment_env_vars):
        if experiment_env_vars:
            self.experiment_env_vars = experiment_env_vars.copy()
        else:
            self.experiment_env_vars = None

    def all_env_var_sets(self):
        env_vars = [self.workspace_env_vars,
                    self.application_env_vars,
                    self.workload_env_vars,
                    self.experiment_env_vars]

        for var_set in env_vars:
            if var_set and len(var_set.keys()):
                yield var_set

    def set_application_vars(self, application_vars):
        self._expansion_dict = None
        if application_vars:
            self.application_vars = application_vars.copy()
        else:
            self.application_vars = None
        self.workload_vars = None
        self.experiment_vars = None

    def set_workload_vars(self, workload_vars):
        self._expansion_dict = None
        if workload_vars:
            self.workload_vars = workload_vars.copy()
        else:
            self.workload_vars = None
        self.experiment_vars = None

    def set_experiment_vars(self, experiment_vars):
        self._expansion_dict = None
        if experiment_vars:
            self.experiment_vars = experiment_vars.copy()
        else:
            self.experiment_vars = None

    def set_experiment_matrices(self, experiment_matrices):
        self._expansion_dict = None
        if experiment_matrices:
            tty.debug('Setting matrices: %s' % experiment_matrices)
            self.experiment_matrices = experiment_matrices.copy()
        else:
            self.experiment_matrices = None

    def unset_mpi_vars(self):
        self.remove_var(self.nodes_key, level='experiment')
        self.remove_var(self.threads_key, level='experiment')
        self.remove_var(self.ranks_key, level='experiment')
        self.remove_var(self.ppn_key, level='experiment')
        self.remove_var(self.nodes_key, level='experiment')

    def _compute_mpi_vars(self):
        n_ranks = self._find_key(self.ranks_key)
        ppn = self._find_key(self.ppn_key)
        n_nodes = self._find_key(self.nodes_key)
        n_threads = self._find_key(self.threads_key)

        all_expansions = self.get_expansion_dict()

        if n_ranks:
            n_ranks = int(self.expand_var(n_ranks,
                                          all_expansions=all_expansions))

        if ppn:
            ppn = int(self.expand_var(ppn,
                                      all_expansions=all_expansions))

        if n_nodes:
            n_nodes = int(self.expand_var(n_nodes,
                                          all_expansions=all_expansions))

        if n_threads:
            n_threads = int(self.expand_var(n_threads,
                                            all_expansions=all_expansions))

        if n_ranks and ppn:
            test_n_nodes = math.ceil(int(n_ranks) / int(ppn))

            if n_nodes and n_nodes < test_n_nodes:
                tty.error('n_nodes in %s is %s and should be %s' %
                          (self.experiment_namespace, n_nodes,
                           test_n_nodes))
            elif not n_nodes:
                tty.debug('Defining n_nodes in %s' %
                          self.experiment_namespace)
                self.experiment_vars[self.nodes_key] = test_n_nodes
        elif n_ranks and n_nodes:
            ppn = math.ceil(int(n_ranks) / int(n_nodes))
            tty.debug('Defining processes_per_node in %s' %
                      self.experiment_namespace)
            self.experiment_vars[self.ppn_key] = ppn
        elif ppn and n_nodes:
            n_ranks = ppn * n_nodes
            tty.debug('Defining n_ranks in %s' %
                      self.experiment_namespace)
            self.experiment_vars[self.ranks_key] = n_ranks
        elif not n_nodes:
            self.experiment_vars[self.nodes_key] = 1

        if not n_threads:
            self.experiment_vars[self.threads_key] = 1

    def _find_key(self, key):
        if self.experiment_vars and key in self.experiment_vars:
            return self.experiment_vars[key]
        elif self.workload_vars and key in self.workload_vars:
            return self.workload_vars[key]
        elif self.application_vars and key in self.application_vars:
            return self.application_vars[key]
        elif self.workspace_vars and key in self.workspace_vars:
            return self.workspace_vars[key]
        elif self.package_paths and key in self.package_paths:
            return self.package_paths[key]
        elif self.base_vars and key in self.base_vars:
            return self.base_vars[key]
        else:
            return None

    @property
    def n_ranks(self):
        found = self._find_key('n_ranks')
        return int(found) if found else found

    @property
    def processes_per_node(self):
        found = self._find_key('processes_per_node')
        return int(found) if found else found

    @property
    def n_nodes(self):
        found = self._find_key('n_nodes')
        return int(found) if found else found

    @property
    def experiment_name(self):
        exp_name = self._find_key(self.exp_name_key)

        if exp_name:
            return self.expand_var(exp_name)
        return None

    @property
    def experiment_run_dir(self):
        exp_run_dir = self._find_key(self.exp_run_dir_key)

        if exp_run_dir:
            return self.expand_var(exp_run_dir)
        return None

    @property
    def experiment_namespace(self):
        app_name = self.application_name
        wl_name = self.workload_name
        exp_name = self.experiment_name
        if app_name and wl_name and exp_name:
            return '%s.%s.%s' % (app_name,
                                 wl_name,
                                 exp_name)
        return None

    def flush_context(self):
        self.remove_var(self.app_name_key)
        self.remove_var(self.app_run_dir_key)
        self.remove_var(self.app_input_dir_key)

        self.remove_var(self.wl_name_key)
        self.remove_var(self.wl_run_dir_key)
        self.remove_var(self.wl_input_dir_key)

        self.remove_var(self.exp_name_key)
        self.remove_var(self.exp_run_dir_key)

        self.pacakge_vars = {}
        self.application_vars = None
        self.workload_vars = None
        self.experiment_vars = None
        self.experiment_matrices = None
        self._expansion_dict = None

        self.application_env_vars = None
        self.workload_env_vars = None
        self.experiment_env_vars = None

    def get_expansion_dict(self, extra_vars=None):
        """Return a dict of all vars that can be used for expansions"""
        if not self._expansion_dict:
            expansions = self.base_vars.copy()
            if self.package_paths:
                expansions.update(self.package_paths)
            if self.workspace_vars:
                expansions.update(self.workspace_vars)
            if self.application_vars:
                expansions.update(self.application_vars)
            if self.workload_vars:
                expansions.update(self.workload_vars)
            if self.experiment_vars:
                expansions.update(self.experiment_vars)

            # Cache expansion dict up to here. The builtin expansion dict should not
            # contain extra_vars
            self._expansion_dict = expansions.copy()
        else:
            expansions = self._expansion_dict.copy()

        if extra_vars:
            expansions.update(extra_vars)

        return expansions

    def all_vars(self, extra_vars=None):
        """Return a dict containing all expanded variables"""

        expansions = self.get_expansion_dict(extra_vars)

        var_dict = {}

        for var, val in expansions.items():
            expanded_val = self.expand_var(val, all_expansions=expansions)
            var_dict[var] = expanded_val
        return var_dict

    def expand_var(self, var, extra_vars=None, all_expansions=None):
        """Perform expansion of a string

        Expand a string by building up a dict of all
        expansion variables.
        """
        if not all_expansions:
            expansions = self.get_expansion_dict(extra_vars)
        else:
            expansions = all_expansions

        expanded = self._partial_expand(expansions, str(var))

        if self._fully_expanded(expanded):
            try:
                math_ast = ast.parse(str(expanded), mode='eval')
                evaluated = self.eval_math(math_ast.body)
                expanded = evaluated
            except MathEvaluationError:
                pass
            except SyntaxError:
                pass

        return str(expanded).lstrip()

    def _all_keywords(self, in_str):
        if isinstance(in_str, six.string_types):
            for keyword in string.Formatter().parse(in_str):
                if keyword[1]:
                    yield keyword[1]

    def _fully_expanded(self, in_str):
        for kw in self._all_keywords(in_str):
            return False
        return True

    def eval_math(self, node):
        """Evaluate math from parsing the AST

        Does not assume a specific type of operands.
        Some operators will generate floating point, while
        others will generate integers (if the inputs are integers).
        """
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            left_eval = self.eval_math(node.left)
            right_eval = self.eval_math(node.right)
            op = supported_math_operators[type(node.op)]
            return op(left_eval, right_eval)
        elif isinstance(node, ast.UnaryOp):
            operand = self.eval_math(node.operand)
            op = supported_math_operators[type(node.op)]
            return op(operand)
        else:
            raise MathEvaluationError('Invalid node')

    def _partial_expand(self, expansion_vars, in_str):
        """Perform expansion of a string with some variables

        args:
          expansion_vars (dict): Variables to perform expansion with
          in_str (str): Input template string to expand

        returns:
          in_str (str): Expanded version of input string
        """

        exp_dict = ExpansionDict()
        if isinstance(in_str, six.string_types):
            for kw in self._all_keywords(in_str):
                if kw in expansion_vars:
                    exp_dict[kw] = \
                        self._partial_expand(expansion_vars,
                                             expansion_vars[kw])

            for kw, val in exp_dict.items():
                if self._fully_expanded(val):
                    try:
                        math_ast = ast.parse(str(val), mode='eval')
                        evaluated = self.eval_math(math_ast.body)
                        exp_dict[kw] = evaluated
                    except MathEvaluationError:
                        pass
                    except SyntaxError:
                        pass

            return in_str.format_map(exp_dict)
        return in_str


class ExpanderError(ramble.error.RambleError):
    """Raised when an error happens within an expander"""


class MathEvaluationError(ExpanderError):
    """Raised when an error happens while evaluating math during
    expansion
    """


class ApplicationNotDefinedError(ExpanderError):
    """Raised when an application is not defined properly"""


class WorkloadNotDefinedError(ExpanderError):
    """Raised when a workload is not defined properly"""


class ExperimentNotDefinedError(ExpanderError):
    """Raised when an experiment is not defined properly"""

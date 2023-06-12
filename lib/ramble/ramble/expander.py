# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import string
import ast
import six
import operator

import llnl.util.tty as tty

import ramble.error
import ramble.keywords

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

    _keywords = ramble.keywords.keywords

    def __init__(self, variables, experiment_set):
        self._variables = variables

        self._experiment_set = experiment_set

        self._application_name = None
        self._workload_name = None
        self._experiment_name = None

        self._application_namespace = None
        self._workload_namespace = None
        self._experiment_namespace = None
        self._env_namespace = None

        self._application_input_dir = None
        self._workload_input_dir = None

        self._application_run_dir = None
        self._workload_run_dir = None
        self._experiment_run_dir = None

    @property
    def application_name(self):
        if not self._application_name:
            var = self.expansion_str(self._keywords.application_name)
            self._application_name = self.expand_var(var)

        return self._application_name

    @property
    def workload_name(self):
        if not self._workload_name:
            var = self.expansion_str(self._keywords.workload_name)
            self._workload_name = self.expand_var(var)

        return self._workload_name

    @property
    def experiment_name(self):
        if not self._experiment_name:
            var = self.expansion_str(self._keywords.experiment_name)
            self._experiment_name = self.expand_var(var)

        return self._experiment_name

    @property
    def application_namespace(self):
        if not self._application_namespace:
            self._application_namespace = self.application_name

        return self._application_namespace

    @property
    def workload_namespace(self):
        if not self._workload_namespace:
            self._workload_namespace = '%s.%s' % (self.application_name,
                                                  self.workload_name)

        return self._workload_namespace

    @property
    def experiment_namespace(self):
        if not self._experiment_namespace:
            self._experiment_namespace = '%s.%s.%s' % (self.application_name,
                                                       self.workload_name,
                                                       self.experiment_name)

        return self._experiment_namespace

    @property
    def env_namespace(self):
        if not self._env_namespace:
            var = self.expansion_str(self._keywords.env_name) + \
                '.' + self.expansion_str(self._keywords.workload_name)
            self._env_namespace = self.expand_var(var)

        return self._env_namespace

    @property
    def application_input_dir(self):
        if not self._application_input_dir:
            var = self.expansion_str(self._keywords.application_input_dir)
            self._application_input_dir = self.expand_var(var)

        return self._application_input_dir

    @property
    def workload_input_dir(self):
        if not self._workload_input_dir:
            var = self.expansion_str(self._keywords.workload_input_dir)
            self._workload_input_dir = self.expand_var(var)

        return self._workload_input_dir

    @property
    def application_run_dir(self):
        if not self._application_run_dir:
            var = self.expansion_str(self._keywords.application_run_dir)
            self._application_run_dir = self.expand_var(var)

        return self._application_run_dir

    @property
    def workload_run_dir(self):
        if not self._workload_run_dir:
            var = self.expansion_str(self._keywords.workload_run_dir)
            self._workload_run_dir = self.expand_var(var)

        return self._workload_run_dir

    @property
    def experiment_run_dir(self):
        if not self._experiment_run_dir:
            var = self.expansion_str(self._keywords.experiment_run_dir)
            self._experiment_run_dir = self.expand_var(var)

        return self._experiment_run_dir

    def expand_var(self, var, extra_vars=None, allow_passthrough=True):
        """Perform expansion of a string

        Expand a string by building up a dict of all
        expansion variables.

        Args:
        - var: String variable to expand
        - extra_vars: Variable definitions to use with highest precedence
        - allow_passthrough: Whether the string is allowed to have
                             keywords after expansion
        """

        expansions = self._variables
        if extra_vars:
            expansions = self._variables.copy()
            expansions.update(extra_vars)

        expanded = self._partial_expand(expansions, str(var), allow_passthrough=allow_passthrough)

        if self._fully_expanded(expanded):
            try:
                math_ast = ast.parse(str(expanded), mode='eval')
                evaluated = self.eval_math(math_ast.body)
                expanded = evaluated
            except MathEvaluationError as e:
                tty.debug(e)
            except SyntaxError:
                pass
        elif not allow_passthrough:
            tty.debug('Passthrough expansion not allowed.')
            tty.debug('    Variable definitions are: {str(self._variables)}')
            raise ExpanderError(f'Expander was unable to fully expand "{var}", '
                                'and is not allowed to passthrough undefined variables.')

        return str(expanded).lstrip()

    @staticmethod
    def expansion_str(in_str):
        l_delimiter = '{'
        r_delimiter = '}'
        return f'{l_delimiter}{in_str}{r_delimiter}'

    def _all_keywords(self, in_str):
        """Iterator for all keyword arguments in a string

        Args:
        - in_str (string): Input string to detect keywords from

        Yields:
        - Each keyword argument in in_str
        """
        if isinstance(in_str, six.string_types):
            for keyword in string.Formatter().parse(in_str):
                if keyword[1]:
                    yield keyword[1]

    def _fully_expanded(self, in_str):
        """Test if a string is fully expanded

        Args:
        - in_str (string): Input string to test as expanded

        Returns boolean. True if `in_str` contains no keywords, false if a
        keyword is detected.
        """
        for kw in self._all_keywords(in_str):
            return False
        return True

    def _partial_expand(self, expansion_vars, in_str, allow_passthrough=True):
        """Perform expansion of a string with some variables

        args:
          expansion_vars (dict): Variables to perform expansion with
          in_str (str): Input template string to expand
          allow_passthrough (bool): Define if variables are allowed to passthrough
                                    without being expanded.

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

            passthrough_vars = {}
            for kw, val in exp_dict.items():
                if self._fully_expanded(val):
                    try:
                        math_ast = ast.parse(str(val), mode='eval')
                        evaluated = self.eval_math(math_ast.body)
                        exp_dict[kw] = evaluated
                    except MathEvaluationError as e:
                        tty.debug(e)
                    except SyntaxError:
                        pass
                elif not allow_passthrough:
                    tty.deubg(f'Expansion stack errors: attempted to expand "{kw}" = "{val}"')
                else:
                    for kw in self._all_keywords(val):
                        passthrough_vars[kw] = '{' + kw + '}'
            exp_dict.update(passthrough_vars)

            return in_str.format_map(exp_dict)
        return in_str

    def eval_math(self, node):
        """Evaluate math from parsing the AST

        Does not assume a specific type of operands.
        Some operators will generate floating point, while
        others will generate integers (if the inputs are integers).
        """
        if isinstance(node, ast.Num):
            return self._ast_num(node)
        elif isinstance(node, ast.Constant):
            return self._ast_constant(node)
        elif isinstance(node, ast.Name):
            return self._ast_name(node)
        elif isinstance(node, ast.Attribute):
            return self._ast_attr(node)
        elif isinstance(node, ast.Compare):
            return self._eval_comparisons(node)
        elif isinstance(node, ast.BinOp):
            return self._eval_binary_ops(node)
        elif isinstance(node, ast.UnaryOp):
            return self._eval_unary_ops(node)
        else:
            node_type = str(type(node))
            raise MathEvaluationError(f'Unsupported math AST node {node_type}:\n' +
                                      f'\t{node.__dict__}')

    # Ast logic helper methods
    def __raise_syntax_error(self, node):
        node_type = str(type(node))
        raise RambleSyntaxError(f'Syntax error while processing {node_type} node:\n' +
                                f'{node.__dict__}')

    def _ast_num(self, node):
        """Handle a number node in the ast"""
        return node.n

    def _ast_constant(self, node):
        """Handle a constant node in the ast"""
        return node.value

    def _ast_name(self, node):
        """Handle a name node in the ast"""
        return node.id

    def _ast_attr(self, node):
        """Handle an attribute node in the ast"""
        if isinstance(node.value, ast.Attribute):
            base = self._ast_attr(node.value)
        elif isinstance(node.value, ast.Name):
            base = self._ast_name(node.value)
        else:
            self.__raise_syntax_error(node)

        val = f'{base}.{node.attr}'
        return val

    def _eval_comparisons(self, node):
        """Handle a comparison node in the ast"""

        # Extract In nodes, and call their helper
        if len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
            return self._eval_comp_in(node)
        return node

    def _eval_comp_in(self, node):
        """Handle in nodes in the ast

        Perform extraction of `<variable> in <experiment>` syntax.

        Raises an exception if the experiment does not exist.
        """
        if isinstance(node.left, ast.Name):
            var_name = self._ast_name(node.left)
            if isinstance(node.comparators[0], ast.Attribute):
                namespace = self.eval_math(node.comparators[0])
                val = self._experiment_set.get_var_from_experiment(namespace,
                                                                   self.expansion_str(var_name))
                if not val:
                    raise RambleSyntaxError(f'{namespace} does not exist in: ' +
                                            f'"{var_name} in {namespace}"')
                    self.__raise_syntax_error(node)
                return val
        self.__raise_syntax_error(node)

    def _eval_binary_ops(self, node):
        """Evaluate binary operators in the ast

        Extract the binary operator, and evaluate it.
        """
        try:
            left_eval = self.eval_math(node.left)
            right_eval = self.eval_math(node.right)
            op = supported_math_operators[type(node.op)]
            return op(left_eval, right_eval)
        except TypeError:
            raise SyntaxError('Unsupported operand type in binary operator')
        except KeyError:
            raise SyntaxError('Unsupported binary operator')

    def _eval_unary_ops(self, node):
        """Evaluate unary operators in the ast

        Extract the unary operator, and evaluate it.
        """
        try:
            operand = self.eval_math(node.operand)
            op = supported_math_operators[type(node.op)]
            return op(operand)
        except TypeError:
            raise SyntaxError('Unsupported operand type in unary operator')
        except KeyError:
            raise SyntaxError('Unsupported unary operator')


class ExpanderError(ramble.error.RambleError):
    """Raised when an error happens within an expander"""


class MathEvaluationError(ExpanderError):
    """Raised when an error happens while evaluating math during
    expansion
    """


class RambleSyntaxError(ExpanderError):
    """Raised when a syntax error happens within variable definitions"""


class ApplicationNotDefinedError(ExpanderError):
    """Raised when an application is not defined properly"""


class WorkloadNotDefinedError(ExpanderError):
    """Raised when a workload is not defined properly"""


class ExperimentNotDefinedError(ExpanderError):
    """Raised when an experiment is not defined properly"""

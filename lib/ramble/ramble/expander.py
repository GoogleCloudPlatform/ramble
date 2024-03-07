# Copyright 2022-2024 Google LLC
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
import math
import random

import ramble.error
import ramble.keywords
from ramble.util.logger import logger

import spack.util.naming

supported_math_operators = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow:
    operator.pow, ast.BitXor: operator.xor, ast.USub: operator.neg,
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Gt: operator.gt,
    ast.GtE: operator.ge, ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.And: operator.and_, ast.Or: operator.or_, ast.Mod: operator.mod
}

supported_scalar_function_pointers = {
    'str': str,
    'int': int,
    'float': float,
    'max': max,
    'min': min,
    'ceil': math.ceil,
    'floor': math.floor,
    'randrange': random.randrange,
    'randint': random.randint,
    'simplify_str': spack.util.naming.simplify_name
}

supported_list_function_pointers = {
    'range': range,
}


formatter = string.Formatter()


class ExpansionDelimiter(object):
    """Class representing the delimiters for ramble expansion strings"""
    left = '{'
    right = '}'
    escape = '\\'


class VformatDelimiter(object):
    """Class representing the delimiters for the string.Formatter class"""
    left = '{'
    right = '}'


class ExpansionNode(object):
    """Class representing a node in a ramble expansion graph"""

    def __init__(self, left_idx, right_idx):
        self.left = left_idx
        self.right = right_idx
        self.children = []
        self.idx = None
        self.contents = None
        self.value = None
        self.root = None

    def __str__(self):
        lines = []
        lines.append('   Node:')
        lines.append(f'      Indices: ({self.left}, {self.right})')
        lines.append(f'      Num Children: ({len(self.children)})')
        lines.append(f'      Contents: "{self.contents}"')
        lines.append(f'      Value: "{self.value}"')
        lines.append(f'      Is root: "{self is self.root}"')
        return '\n'.join(lines)

    def relative_indices(self, relative_to):
        """Compute node indices relative to another node

        Args:
            relative_to (node): node to shift current node's indices relative to

        Returns:
            (tuple) indices of shifted match set
        """
        return (self.left - relative_to.left, self.right - relative_to.left)

    def add_children(self, children):
        """Add children to this node

        Args:
            children (node, or list): nodes to adds as children of self
        """
        if isinstance(children, list):
            self.children.extend(children)
        else:
            self.children.append(children)

    def define_value(self, expansion_dict, allow_passthrough=True,
                     expansion_func=str, evaluation_func=eval,
                     no_expand_vars=set()):
        """Define the value for this node.

        Construct the value of self. This builds up a string representation of
        self, and performs evaluation and formatting of the resulting string.
        This includes extracting the values of the children nodes, and
        replacing their values in the proper positions in self's string.

        Stores the resulting value in self.value

        Args:
            expansion_dict (dict): variable definitions to use for expanding
            detected matches
            allow_passthrough (bool): if true, expansion is allowed to fail. if
            false, failed expansion raises an error.
            expansion_func (func): function to use for expansion of nested
            variable definitions
            evaluation_func (func): function to use for evaluating math of strings
            no_expand_vars (set): set of variable names that should never be expanded
        """
        if self.contents is not None:
            parts = []
            last_idx = 0
            for child in self.children:
                child_indices = child.relative_indices(self)
                parts.append(self.contents[last_idx:child_indices[0]])
                parts.append(str(child.value))
                last_idx = child_indices[1] + 1

            if last_idx != len(self.contents):
                parts.append(self.contents[last_idx:])

            if self != self.root:
                replaced_contents = ''.join(parts)

                # Special case '{}'
                if len(replaced_contents) == 2:
                    self.value = '{}'
                    return

                format_kw = replaced_contents[1:-1]
                kw_parts = format_kw.split(':')
                required_passthrough = False

                if kw_parts[0] in expansion_dict:
                    # Exit expansion for variables defined as no_expand
                    if kw_parts[0] in no_expand_vars:
                        self.value = expansion_dict[kw_parts[0]]
                        return
                    else:
                        self.value = expansion_func(expansion_dict,
                                                    expansion_dict[kw_parts[0]],
                                                    allow_passthrough=allow_passthrough)
                else:
                    self.value = kw_parts[0]
                    required_passthrough = True

                # Evaluation should go here
                try:
                    old_value = self.value
                    self.value = evaluation_func(self.value)
                    if old_value != self.value:
                        required_passthrough = False
                except SyntaxError:
                    pass

                # If we had a format spec, add it
                if len(kw_parts) > 1:
                    kw_dict = {'value': self.value}
                    format_str = f'value:{kw_parts[1]}'
                    try:
                        self.value = formatter.vformat(VformatDelimiter.left +
                                                       format_str +
                                                       VformatDelimiter.right,
                                                       [], kw_dict)
                        required_passthrough = False
                    except ValueError:
                        self.value += f':{kw_parts[1]}'
                    except KeyError:
                        self.value += f':{kw_parts[1]}'

                if required_passthrough:
                    self.value = f'{{{self.value}}}'
                    if not allow_passthrough:
                        raise_passthrough_error(self.contents, self.value)
            else:
                replaced_contents = ''.join(parts)
                try:
                    self.value = evaluation_func(replaced_contents)
                except SyntaxError:
                    self.value = replaced_contents

                # Replace escaped curly braces with curly braces
                if isinstance(self.value, six.string_types):
                    self.value = self.value.replace('\\{', '{').replace('\\}', '}')


class ExpansionGraph(object):
    """Class representing a graph of ExpansionNodes"""

    def __init__(self, in_str):
        self.str = in_str
        self.root = ExpansionNode(0, len(in_str) - 1)
        self.root.contents = in_str
        self.root.root = self.root

        opened = []
        children = []
        escaped = False
        for i, c in enumerate(self.str):
            if c == ExpansionDelimiter.left and not escaped:
                opened.append(i)
                children.append([])
            elif c == ExpansionDelimiter.right and len(opened) > 0 and not escaped:
                left_idx = opened.pop()
                right_idx = i

                cur_match = ExpansionNode(left_idx, right_idx)
                cur_match.add_children(children.pop())
                cur_match.contents = self.str[left_idx:right_idx + 1]  # Define contents
                cur_match.root = self.root

                if len(opened) > 0:
                    children[-1].append(cur_match)
                else:
                    self.root.add_children(cur_match)
            elif c == '\n':  # Don't expand across new lines
                opened = []

            if c == ExpansionDelimiter.escape:
                escaped = True
            elif escaped:
                escaped = False

        if len(opened) > 0:
            self.root.add_children(children.pop())

    def walk(self, in_node=None):
        """Perform a DFS walk of the nodes in the graph

        Args:
            in_node (ExpansionNode): node to begin the walk from, if not set uses self.root

        Yields:
            (ExpansionNode): nodes following a DFS traversal of the graph
        """
        cur_node = in_node
        if cur_node is None:
            cur_node = self.root

        for child in cur_node.children:
            yield from self.walk(in_node=child)

        yield cur_node

    def __str__(self):
        lines = []
        lines.append(f'Processing string: {self.str}')
        for node in self.walk():
            lines.append((f'{node}'))
        return '\n'.join(lines)


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
    def __init__(self, variables, experiment_set, no_expand_vars=set()):

        self._keywords = ramble.keywords.keywords

        self._variables = variables
        self._no_expand_vars = no_expand_vars

        self._experiment_set = experiment_set

        self._application_name = None
        self._workload_name = None
        self._experiment_name = None

        self._application_namespace = None
        self._workload_namespace = None
        self._experiment_namespace = None
        self._env_namespace = None
        self._env_path = None

        self._application_input_dir = None
        self._workload_input_dir = None
        self._license_input_dir = None

        self._application_run_dir = None
        self._workload_run_dir = None
        self._experiment_run_dir = None

    def add_no_expand_var(self, var: str):
        """Add a new variable to the no expand set

        Args:
            var (str): Variable that should not expand
        """
        self._no_expand_vars.add(var)

    def set_no_expand_vars(self, no_expand_vars):
        self._no_expand_vars = no_expand_vars.copy()

    def copy(self):
        return Expander(self._variables.copy(), self._experiment_set)

    @property
    def application_name(self):
        if not self._application_name:
            self._application_name = self.expand_var_name(self._keywords.application_name)

        return self._application_name

    @property
    def workload_name(self):
        if not self._workload_name:
            self._workload_name = self.expand_var_name(self._keywords.workload_name)

        return self._workload_name

    @property
    def experiment_name(self):
        if not self._experiment_name:
            self._experiment_name = self.expand_var_name(self._keywords.experiment_name)

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
    def env_path(self):
        if not self._env_path:
            var = self.expansion_str(self._keywords.env_path)
            self._env_path = self.expand_var(var)

        return self._env_path

    @property
    def application_input_dir(self):
        if not self._application_input_dir:
            self._application_input_dir = \
                self.expand_var_name(self._keywords.application_input_dir)

        return self._application_input_dir

    @property
    def workload_input_dir(self):
        if not self._workload_input_dir:
            self._workload_input_dir = self.expand_var_name(self._keywords.workload_input_dir)

        return self._workload_input_dir

    @property
    def license_input_dir(self):
        if not self._license_input_dir:
            self._license_input_dir = self.expand_var_name(self._keywords.license_input_dir)

        return self._license_input_dir

    @property
    def application_run_dir(self):
        if not self._application_run_dir:
            self._application_run_dir = self.expand_var_name(self._keywords.application_run_dir)

        return self._application_run_dir

    @property
    def workload_run_dir(self):
        if not self._workload_run_dir:
            self._workload_run_dir = self.expand_var_name(self._keywords.workload_run_dir)

        return self._workload_run_dir

    @property
    def experiment_run_dir(self):
        if not self._experiment_run_dir:
            self._experiment_run_dir = self.expand_var_name(self._keywords.experiment_run_dir)

        return self._experiment_run_dir

    def expand_lists(self, var):
        """Expand a variable into a list if possible

        If expanding a variable would generate a list, this function will
        return a list. If any error case happens, this function will return
        the unmodified input value.

        NOTE: This function is generally called early in the expansion. This allows
        lists to be generated before rendering experiments, but does not support
        pulling a list from a different experiment.
        """
        try:
            math_ast = ast.parse(str(var), mode='eval')
            value = self.eval_math(math_ast.body)
            if isinstance(value, list):
                return value
            return var
        except MathEvaluationError:
            return var
        except AttributeError:
            return var
        except ValueError:
            return var
        except SyntaxError:
            return var

    def expand_var_name(self, var_name, extra_vars=None, allow_passthrough=True):
        """Convert a variable name to an expansion string, and expand it

        Take a variable name (var) and convert it to an expansion string by
        calling the expansion_str function. Pass the expansion string into
        expand_var, and return the result.

        Args:
            var_name: String name of variable to expand
            extra_vars: Variable definitions to use with highest precedence
            allow_passthrough: Whether the string is allowed to have keywords
                               after expansion
        """
        return self.expand_var(self.expansion_str(var_name),
                               extra_vars=extra_vars,
                               allow_passthrough=allow_passthrough)

    def expand_var(self, var, extra_vars=None, allow_passthrough=True):
        """Perform expansion of a string

        Expand a string by building up a dict of all
        expansion variables.

        Args:
            var: String variable to expand
            extra_vars: Variable definitions to use with highest precedence
            allow_passthrough: Whether the string is allowed to have keywords
                               after expansion
        """

        passthrough_setting = allow_passthrough

        # If disable_passthrough is set, override allow_passthrough from caller
        if ramble.config.get('config:disable_passthrough'):
            passthrough_setting = False

        logger.debug(f'BEGINNING OF EXPAND_VAR STACK ON {var}')
        expansions = self._variables
        if extra_vars:
            expansions = self._variables.copy()
            expansions.update(extra_vars)

        try:
            value = self._partial_expand(expansions,
                                         str(var),
                                         allow_passthrough=passthrough_setting).lstrip()
        except RamblePassthroughError as e:
            if not passthrough_setting:
                raise RambleSyntaxError(f'Encountered a passthrough error while expanding {var}\n'
                                        f'{e}')

        logger.debug(f'END OF EXPAND_VAR STACK {value}')
        return value

    def evaluate_predicate(self, in_str, extra_vars=None):
        """Evaluate a predicate by expanding and evaluating math contained in a string

        Args:
            in_str: String representing predicate that should be evaluated
            extra_vars: Variable definitions to use with highest precedence

        Returns:
            boolean: True or False, based on the evaluation of in_str
        """

        evaluated = self.expand_var(in_str, extra_vars=extra_vars, allow_passthrough=False)

        if not isinstance(evaluated, six.string_types):
            logger.die('Logical compute failed to return a string')

        if evaluated == 'True':
            return True
        elif evaluated == 'False':
            return False
        else:
            logger.die(f'When evaluating {in_str}, evaluate_predicate returned '
                       f'a non-boolean string: "{evaluated}"')

    @staticmethod
    def expansion_str(in_str):
        return f'{ExpansionDelimiter.left}{in_str}{ExpansionDelimiter.right}'

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

        if isinstance(in_str, six.string_types):
            str_graph = ExpansionGraph(in_str)
            for node in str_graph.walk():
                node.define_value(expansion_vars,
                                  allow_passthrough=allow_passthrough,
                                  expansion_func=self._partial_expand,
                                  evaluation_func=self.perform_math_eval,
                                  no_expand_vars=self._no_expand_vars)

            return str(str_graph.root.value)

        return str(in_str)

    def perform_math_eval(self, in_str):
        """Attempt to evaluate in_str

        Args:
            in_str (str): string representing math to attempt to evaluate

        Returns:
            (str) either the evaluation of in_str (if successful) or in_str
            unmodified (if unsuccessful)

        """
        try:
            math_ast = ast.parse(in_str, mode='eval')
            out_str = self.eval_math(math_ast.body)
            return out_str
        except MathEvaluationError as e:
            logger.debug(f'   Math input is: "{in_str}"')
            logger.debug(e)

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
        # TODO: Remove when we drop support for 3.6
        # DEPRECATED: Remove due to python 3.8
        # See: https://docs.python.org/3/library/ast.html#node-classes
        elif isinstance(node, ast.Str):
            return node.s
        elif isinstance(node, ast.Attribute):
            return self._ast_attr(node)
        elif isinstance(node, ast.Compare):
            return self._eval_comparisons(node)
        elif isinstance(node, ast.BoolOp):
            return self._eval_bool_op(node)
        elif isinstance(node, ast.BinOp):
            return self._eval_binary_ops(node)
        elif isinstance(node, ast.UnaryOp):
            return self._eval_unary_ops(node)
        elif isinstance(node, ast.Call):
            return self._eval_function_call(node)
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

    def _eval_function_call(self, node):
        """Handle a subset of function call nodes in the ast"""

        args = []
        kwargs = {}
        for arg in node.args:
            args.append(self.eval_math(arg))
        for kw in node.keywords:
            kwargs[self.eval_math(kw.arg)] = self.eval_math(kw.value)

        if node.func.id in supported_scalar_function_pointers.keys():
            func = supported_scalar_function_pointers[node.func.id]
            return func(*args, **kwargs)
        elif node.func.id in supported_list_function_pointers.keys():
            func = supported_list_function_pointers[node.func.id]
            return list(func(*args, **kwargs))
        elif node.func.id == 'replace':
            return str(args[0]).replace(*args[1:], **kwargs)
        else:
            raise MathEvaluationError(f'Undefined function {node.func.id} used.\n'
                                      'returning unexapanded string')

    def _eval_bool_op(self, node):
        """Handle a boolean operator node in the ast"""
        try:
            op = supported_math_operators[type(node.op)]

            result = self.eval_math(node.values[0])

            for value in node.values[1:]:
                result = op(result, self.eval_math(value))

            return result

        except TypeError:
            raise SyntaxError('Unsupported operand type in boolean operator')
        except KeyError:
            raise SyntaxError('Unsupported boolean operator')

    def _eval_comparisons(self, node):
        """Handle a comparison node in the ast"""

        # Extract In nodes, and call their helper
        if len(node.ops) == 1 and isinstance(node.ops[0], ast.In):
            return self._eval_comp_in(node)

        # Try to evaluate the comparison logic, if not return the node as is.
        try:
            cur_left = self.eval_math(node.left)

            op = supported_math_operators[type(node.ops[0])]
            cur_right = self.eval_math(node.comparators[0])

            result = op(cur_left, cur_right)

            if len(node.ops) > 1:
                cur_left = cur_right
                for comp, right in zip(node.ops, node.comparators)[1:]:
                    op = supported_math_operators[type(comp)]
                    cur_right = self.eval_math(right)

                    result = result and op(cur_left, cur_right)

                    cur_left = cur_right
            return result
        except TypeError:
            raise SyntaxError('Unsupported operand type in binary comparison operator')
        except KeyError:
            raise SyntaxError('Unsupported binary comparison operator')

    def _eval_comp_in(self, node):
        """Handle in nodes in the ast

        Perform extraction of `<variable> in <experiment>` syntax.
        Raises an exception if the experiment does not exist.

        Also, evaluated `<value> in [list, of, values]` syntax.
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
        elif isinstance(node.left, ast.Constant):
            lhs_value = self.eval_math(node.left)

            found = False
            for comp in node.comparators:
                if isinstance(comp, ast.List):
                    for elt in comp.elts:
                        rhs_value = self.eval_math(elt)
                        if lhs_value == rhs_value:
                            found = True
            return found

        self.__raise_syntax_error(node)

    def _eval_binary_ops(self, node):
        """Evaluate binary operators in the ast

        Extract the binary operator, and evaluate it.
        """
        try:
            left_eval = self.eval_math(node.left)
            right_eval = self.eval_math(node.right)
            op = supported_math_operators[type(node.op)]
            if isinstance(left_eval, six.string_types) or isinstance(right_eval, six.string_types):
                raise SyntaxError('Unsupported operand type in binary operator')
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
            if isinstance(operand, six.string_types):
                raise SyntaxError('Unsupported operand type in unary operator')
            op = supported_math_operators[type(node.op)]
            return op(operand)
        except TypeError:
            raise SyntaxError('Unsupported operand type in unary operator')
        except KeyError:
            raise SyntaxError('Unsupported unary operator')


def raise_passthrough_error(in_str, out_str):
    """Raise an error when passthrough is disabled but variables are not all expanded"""

    logger.debug(f'Expansion stack errors: attempted to expand '
                 f'"{in_str}"')
    logger.debug(f'  As: {out_str}')
    raise RamblePassthroughError('Error Stack:\n'
                                 f'Input: "{in_str}"\n'
                                 f'Output: "{out_str}"\n')


class ExpanderError(ramble.error.RambleError):
    """Raised when an error happens within an expander"""


class MathEvaluationError(ExpanderError):
    """Raised when an error happens while evaluating math during
    expansion
    """


class RambleSyntaxError(ExpanderError):
    """Raised when a syntax error happens within variable definitions"""


class RamblePassthroughError(ExpanderError):
    """Raised when passthrough is disabled and variables fail to expand"""


class ApplicationNotDefinedError(ExpanderError):
    """Raised when an application is not defined properly"""


class WorkloadNotDefinedError(ExpanderError):
    """Raised when a workload is not defined properly"""


class ExperimentNotDefinedError(ExpanderError):
    """Raised when an experiment is not defined properly"""

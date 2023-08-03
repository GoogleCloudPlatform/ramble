# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import itertools

import llnl.util.tty as tty

import ramble.error
import ramble.expander
from ramble.namespace import namespace

import ramble.util.matrices


class RenderGroup(object):
    _obj_types = ['experiment', 'package', 'environment']
    _actions = ['create', 'exclude']

    def __init__(self, obj_type=None, action='create'):
        """Constructor for a RenderGroup.

        Create a RenderGroup object, defining several the input to
        a Renderer object.
        """
        if obj_type == 'experiment':
            self.object = 'experiment'
            self.objects = 'experiments'
            self.context = "experiment_name"
        elif obj_type == 'package':
            self.object = 'package'
            self.objects = 'packages'
            self.context = 'package_name'
        elif obj_type == 'environment':
            self.object = 'environment'
            self.objects = 'environments'
            self.context = 'environment_name'
        else:
            tty.die(f'Object type {obj_type} is not valid to render.\n' +
                    f'Valid options are: {self._obj_types}')

        if action not in self._actions:
            tty.die(f'Action {action} is not valid to render.\n' +
                    f'Valid options are: {self._actions}')
        self.action = action

        self.variables = {}
        self.zips = {}
        self.matrices = []

    def copy_contents(self, in_group):
        """Copy contents of in_group into self"""

        if in_group.variables:
            self.variables.update(in_group.variables)

        if in_group.zips:
            self.zips.update(in_group.zips)

        if in_group.matrices:
            self.matrices.extend(in_group.matrices)

    def from_dict(self, name_template, in_dict):
        """Extract RenderGroup definitions from a dictionary

        Dictionaries should follow the below format:

        in_dict = {
            'variables': {},
            'zips': {},
            'matrix': [],
            'matrices': {} or [],
        }

        Args:
            name_template: The name template for the objects this group represents
            in_dict: A dictionary representing the group definitions

        Returns:
            boolean: True if anything was extracted from the dictionary
        """

        extracted = False

        if namespace.variables in in_dict:
            self.variables.update(in_dict[namespace.variables])
            extracted = True

        if namespace.zips in in_dict:
            self.zips.update(in_dict[namespace.zips])
            extracted = True

        self.matrices = ramble.util.matrices.extract_matrices(f'{self.action} {self.object}',
                                                              name_template,
                                                              in_dict)

        if len(self.matrices) > 0:
            extracted = True

        return extracted


class Renderer(object):
    def render_objects(self, render_group, exclude_where=None):
        """Render objects based on the input variables and matrices

        Internally collects all matrix and vector variables.

        First, zips are created. Zips extract vector variables, and group them
        into a higher level name.

        Next, matrices are processed. Matrices consume vector variables, or
        explicit zips.

        Vectors in the same matrix are crossed, sibling matrices are zipped.
        All matrices are required to result in the same number of elements, but
        not be the same shape.

        Matrix elements are only allowed to be the names of variables. These
        variables are required to be vectors.

        After matrices are processed, any remaining vectors are zipped
        together. All vectors are required to be of the same size.

        The resulting zip of vectors is then crossed with all of the matrices
        to build a final list of objects.

        After processing the expansion logic, this function yields a dictionary
        of variable definitions, one for each object that would be rendered.

        Returns:
            Yield a dictionary of variables for single object definition
        """
        variables = render_group.variables
        zips = render_group.zips
        matrices = render_group.matrices

        object_variables = {}
        expander = ramble.expander.Expander(variables, None)

        # Expand all variables that generate lists
        for name, unexpanded in variables.items():
            value = expander.expand_lists(unexpanded)
            object_variables[name] = value

        new_objects = []
        defined_zips = {}
        consumed_zips = set()
        matrix_objects = []

        if zips:
            zipped_vars = set()

            for zip_group, group_def in zips.items():
                # Create a new defined zip
                defined_zips[zip_group] = {'vars': {}, 'length': 0}
                cur_zip = defined_zips[zip_group]
                for var_name in group_def:
                    # Ensure the variable is defined
                    if var_name not in object_variables:
                        tty.die(f'An undefined variable {var_name} is defined in zip {zip_group}')

                    if var_name in zipped_vars:
                        tty.die(f'Variable {var_name} is used across multiple zips.\n'
                                'Ensure it is only used in a single zip')

                    if not isinstance(object_variables[var_name], list):
                        tty.die(f'Variable {var_name} in zip {zip_group} '
                                'does not refer to a vector.')

                    if len(object_variables[var_name]) == 0:
                        tty.die(f'Variable {var_name} in zip {zip_group} '
                                'has an invalid length of 0')

                    # Validate the length of the variables is the same
                    cur_len = len(object_variables[var_name])
                    if cur_zip['length'] == 0:
                        cur_zip['length'] = cur_len
                    elif cur_len != cur_zip['length']:
                        tty.die(f'Variable {var_name} in zip {zip_group}\n'
                                f'has a length of {cur_len} which differs from\n'
                                f'the current max of {cur_zip["length"]}')

                    # Add variable to the zip, and remove from the definitions
                    zipped_vars.add(var_name)
                    cur_zip['vars'][var_name] = object_variables[var_name]
                    del object_variables[var_name]

        if matrices:
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
            for matrix in matrices:
                matrix_size = 1
                vectors = []
                zips = []
                variable_names = []
                for var in matrix:
                    if var in matrix_vars:
                        tty.die(f'Variable {var} has been used in multiple matrices.\n'
                                + 'Ensure each variable is only used once across all matrices')
                    matrix_vars.add(var)

                    if var in object_variables:
                        if not isinstance(object_variables[var], list):
                            err_context = object_variables[render_group.context]
                            tty.die(f'In {render_group.object} {err_context}'
                                    + f' variable {var} does not refer to a vector.')

                        matrix_size = matrix_size * len(object_variables[var])
                        vectors.append(object_variables[var])
                        variable_names.append(var)

                        # Remove the variable, so it's not processed as a vector anymore.
                        del object_variables[var]

                    elif var in defined_zips:
                        zip_len = defined_zips[var]['length']
                        idx_vector = [i for i in range(0, zip_len)]

                        matrix_size = matrix_size * zip_len
                        vectors.append(idx_vector)
                        variable_names.append(var)
                    else:
                        err_context = object_variables[render_group.context]
                        tty.die(f'In {render_group.object} {err_context}'
                                + f' variable or zip {var} has not been defined yet.')

                if last_size == -1:
                    last_size = matrix_size

                if last_size != matrix_size:
                    err_context = object_variables[render_group.context]
                    tty.die(f'Matrices defined in {render_group.object} {err_context}'
                            + ' do not result in the same number of elements.')

                matrix_vectors.append(vectors)
                matrix_variables.append(variable_names)

            # Create the empty initial dictionairies
            matrix_objects = []
            for _ in range(matrix_size):
                matrix_objects.append({})

            # Generate all of the obj var dicts
            for names, vectors in zip(matrix_variables, matrix_vectors):
                for obj_idx, entry in enumerate(itertools.product(*vectors)):
                    for name_idx, name in enumerate(names):
                        if name in defined_zips.keys():
                            # Replace the zip name with the constituent variables
                            for zip_var in defined_zips[name]['vars']:
                                matrix_objects[obj_idx][zip_var] = \
                                    defined_zips[name]['vars'][zip_var][entry[name_idx]]

                            # Consume the defined zip
                            consumed_zips.add(name)
                        else:
                            matrix_objects[obj_idx][name] = entry[name_idx]

        # Remove all consumed zips and return all remaining zipped variables
        # back to real vector definitions
        if defined_zips:
            if consumed_zips:
                for zip_group in consumed_zips:
                    if zip_group in defined_zips:
                        del defined_zips[zip_group]

            for zip_name in defined_zips:
                for var, val in defined_zips[zip_name]['vars'].items():
                    object_variables[var] = val

        # After matrices have been processed, extract any remaining vector variables
        vector_vars = {}

        # Extract vector variables
        max_vector_size = 0
        for var, val in object_variables.items():
            if isinstance(val, list):
                vector_vars[var] = val.copy()
                max_vector_size = max(len(val), max_vector_size)

        if vector_vars:
            # Check that sizes are the same
            for var, val in vector_vars.items():
                if len(val) != max_vector_size:
                    err_context = object_variables[render_group.context]
                    tty.die(f'Size of vector {var} is not'
                            + f' the same as max {max_vector_size}'
                            + f'. In {render_group.object} {err_context}.')

            # Iterate over the vector length, and set the value in the
            # object dict to the index value.
            for i in range(0, max_vector_size):
                obj_vars = {}
                for var, val in vector_vars.items():
                    obj_vars[var] = val[i]

                if matrix_objects:
                    for matrix_object in matrix_objects:
                        for var, val in matrix_object.items():
                            obj_vars[var] = val

                        new_objects.append(obj_vars.copy())
                else:
                    new_objects.append(obj_vars.copy())

        elif matrix_objects:
            new_objects = matrix_objects
        else:
            # Ensure at least one object is rendered, if everything was a scalar
            new_objects.append({})

        where_expander = ramble.expander.Expander(object_variables, None)

        for obj in new_objects:
            tty.debug(f'Rendering {render_group.object}:')
            for var, val in obj.items():
                object_variables[var] = val

            keep_object = True
            if exclude_where:
                for where in exclude_where:
                    evaluated = where_expander.expand_var(where)
                    if evaluated == 'True':
                        keep_object = False

            if keep_object:
                yield object_variables.copy()


class RambleRendererError(ramble.error.RambleError):
    """Class for all renderer errors"""

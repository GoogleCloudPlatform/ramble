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


class Renderer(object):
    def __init__(self, obj_type=None):
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
                    'Valid options are: "experiment"')

    def render_objects(self, variables, matrices=None):
        """Render objects based on the input variabls and matrices

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
        to build a final list of objects.

        After collecting the matrices, this method modifies generates new
        objects and injects them into the self.objects dictionary.

        Inputs:
            - None
        Returns:
            - A single object definition, through a yield
        """
        object_variables = variables.copy()
        new_objects = []
        matrix_objects = []

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
                variable_names = []
                for var in matrix:
                    if var in matrix_vars:
                        tty.die(f'Variable {var} has been used in multiple matrices.\n'
                                + 'Ensure each variable is only used once across all matrices')
                    matrix_vars.add(var)

                    if var not in object_variables:
                        err_context = object_variables[self.context]
                        tty.die(f'In {self.object} {err_context}'
                                + f' variable {var} has not been defined yet.')

                    if not isinstance(object_variables[var], list):
                        err_context = object_variables[self.context]
                        tty.die(f'In {self.object} {err_context}'
                                + f' variable {var} does not refer to a vector.')

                    matrix_size = matrix_size * len(object_variables[var])

                    vectors.append(object_variables[var])
                    variable_names.append(var)

                    # Remove the variable, so it's not proccessed as a vector anymore.
                    del object_variables[var]

                if last_size == -1:
                    last_size = matrix_size

                if last_size != matrix_size:
                    err_context = object_variables[self.context]
                    tty.die(f'Matrices defined in {self.object} {err_context}'
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
                        matrix_objects[obj_idx][name] = entry[name_idx]

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
                    err_context = object_variables[self.context]
                    tty.die(f'Size of vector {var} is not'
                            + f' the same as max {len(val)}'
                            + f'. In {self.object} {err_context}.')

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

        for obj in new_objects:
            tty.debug(f'Rendering {self.object}:')
            for var, val in obj.items():
                object_variables[var] = val

            yield object_variables.copy()


class RambleRendererError(ramble.error.RambleError):
    """Class for all renderer errors"""

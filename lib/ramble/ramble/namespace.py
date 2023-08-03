# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


class namespace:
    """Class of namespace variables"""
    # For experiments
    ramble = 'ramble'
    application_dir = 'application_directories'
    application = 'applications'
    workload = 'workloads'
    experiment = 'experiments'
    success = 'success_criteria'
    internals = 'internals'
    custom_executables = 'custom_executables'
    executables = 'executables'
    env_var = 'env_vars'
    packages = 'packages'
    environments = 'environments'
    template = 'template'
    chained_experiments = 'chained_experiments'
    modifiers = 'modifiers'

    # For rendering objects
    variables = 'variables'
    zips = 'zips'
    matrices = 'matrices'
    matrix = 'matrix'
    exclude = 'exclude'
    where = 'where'

    # For software definitions
    spack = 'spack'
    external_env = 'external_spack_env'

    # v2 configs
    packages = 'packages'
    environments = 'environments'
    spack_spec = 'spack_spec'
    compiler_spec = 'compiler_spec'
    compiler = 'compiler'

# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


class namespace:
    """Class of namespace variables"""

    # For experiments
    ramble = "ramble"
    application = "applications"
    workload = "workloads"
    experiment = "experiments"
    success = "success_criteria"
    internals = "internals"
    custom_executables = "custom_executables"
    executables = "executables"
    executable_injection = "executable_injection"
    env_var = "env_vars"
    packages = "packages"
    environments = "environments"
    template = "template"
    chained_experiments = "chained_experiments"
    modifiers = "modifiers"
    tags = "tags"
    n_repeats = "n_repeats"
    formatted_executables = "formatted_executables"

    # For chained experiments
    command = "command"
    inherit_variables = "inherit_variables"

    # For rendering objects
    variables = "variables"
    variants = "variants"
    zips = "zips"
    matrices = "matrices"
    matrix = "matrix"
    exclude = "exclude"
    where = "where"

    # For software definitions
    software = "software"
    external_env = "external_env"

    # v2 configs
    packages = "packages"
    environments = "environments"
    pkg_spec = "pkg_spec"
    compiler_spec = "compiler_spec"
    compiler = "compiler"

    # For formatted executables
    indentation = "indentation"
    prefix = "prefix"
    join_separator = "join_separator"
    commands = "commands"

    # For variants
    package_manager = "package_manager"

    metadata = "metadata"

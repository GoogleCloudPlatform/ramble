# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class {class_name}({base_class}):
    """Starter template for {name} application.

    TODO: Add description of the application and link to official site:
    Official Website: https://example.com
    """

    name = "{name}"
    maintainers = {maintainers}
    tags = {tags}

    # Define compiler and software dependencies
    # define_compiler("gcc")
    # software_spec("example-pkg", pkg_spec="example-pkg@1.0")

    # Define executable command template
    # executable("run_example", "example-bin {{options}}", redirect="{{log_file}}")

    # Define workload
    # workload("test_wl", executables=["run_example"])

    # Define figure of merit (FOM) stubs
    # figure_of_merit(
    #     "FOM Name",
    #     log_file="{{log_file}}",
    #     regex=r"Result:\s+(?P<val>[0-9\.]+)",
    #     group="val",
    #     units="seconds",
    # )

# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class PipTest(ExecutableApplication):
    """This is an example application that will run a python import"""

    name = "pip-test"

    tags("test-app")

    software_spec(
        "requests",
        pkg_spec="requests>=2.31.0",
        package_manager="pip",
    )

    software_spec(
        "semver",
        pkg_spec="semver",
        package_manager="pip",
    )

    required_package("semver", package_manager="pip")

    executable(
        "import",
        'python -c "import requests"; echo "return code is $?"',
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    workload("import", executable="import")

    figure_of_merit(
        "return_code",
        fom_regex=r"return code is (?P<code>[0-9]+)\s*",
        group_name="code",
        units="",
    )

    success_criteria(
        "pip_test_import_success",
        mode="fom_comparison",
        fom_name="return_code",
        formula="{value} == 0",
    )

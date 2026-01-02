# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Template(ExecutableApplication):
    """An app for testing object templates."""

    name = "template"

    executable(
        "foo",
        template=["bash {bar}", "echo {test}", "echo {expansion_test_path}"],
    )

    workload("test_template", executable="foo")

    workload_variable(
        "hello_name",
        default="world",
        description="hello name",
        workload="test_template",
    )

    register_template(
        name="bar",
        src_path="bar.tpl",
        dest_path="bar.sh",
        # The `dynamic_hello_world` will be overridden by `_bar_vars`
        extra_vars={
            "dynamic_var1": "foobar",
            "dynamic_hello_world": "not_exist",
        },
        extra_vars_func="bar_vars",
    )

    def _bar_vars(self):
        expander = self.expander
        val = expander.expand_var('"hello {hello_name}"')
        return {"dynamic_hello_world": val}

    register_template(
        name="bar2",
        src_path="bar.tpl",
    )

    register_template(
        name="test",
        src_path="script.sh",
        dest_path="$workspace_shared/script.sh",
        output_perm="755",
    )

    # Setup to test the path expansion for both src and dest
    workload_variable(
        "src_script_path",
        default="$workspace_configs/execute_experiment.tpl",
        description="source path of the template",
        workload="test_template",
    )

    register_template(
        name="expansion_test_path",
        src_path="{src_script_path}",
        dest_path="{experiment_run_dir}/expansion_script.sh",
    )

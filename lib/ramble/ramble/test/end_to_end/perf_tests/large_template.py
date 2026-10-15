# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os

import pytest

import ramble.repository
from ramble.main import RambleCommand

pytestmark = pytest.mark.usefixtures(
    "mutable_config", "mutable_mock_workspace_path", "mutable_mock_apps_repo"
)

workspace = RambleCommand("workspace")


@pytest.mark.perf
def test_large_template_expansion(
    make_workspace_from_config, mutable_mock_apps_repo, tmpdir, ramble_benchmark
):
    # Define a mock template app in a temporary repo
    repo_dir = tmpdir.mkdir("mock_repo")
    with open(os.path.join(str(repo_dir), "repo.yaml"), "w", encoding="utf-8") as f:
        f.write("repo:\n  namespace: mock_repo\n")

    app_dir = repo_dir.mkdir("applications").mkdir("template")
    with open(os.path.join(str(app_dir), "application.py"), "w", encoding="utf-8") as f:
        f.write("""
from ramble.appkit import *

class Template(ExecutableApplication):
    name = "template"
    executable("foo", template=["echo {expansion_test_path}"])
    workload("test_template", executable="foo")
    workload_variable("src_script_path",
                      default="$workspace_configs/execute_experiment.tpl",
                      workload="test_template")
    register_template(name="expansion_test_path",
                      src_path="{src_script_path}",
                      dest_path="{experiment_run_dir}/expansion_script.sh")
""")

    repo = ramble.repository.Repo(
        str(repo_dir), object_type=ramble.repository.ObjectTypes.applications
    )
    mutable_mock_apps_repo.put_first(repo)

    # Create a large template with math and non-math statements
    n_lines = 20000
    template_lines = []
    for i in range(n_lines):
        if i % 3 == 0:
            # Math statement
            template_lines.append(f"Math statement {i}: {{{i}+{i}}}")
        elif i % 3 == 1:
            # Variable statement
            template_lines.append(f"Variable statement {i}: {{var1}} {{var2}}")
        else:
            # Non-math statement
            template_lines.append(f"Non-math statement {i}: just some text with index {i}")

    template_content = "\n".join(template_lines)
    template_filename = "large_template.tpl"

    test_config = f"""
ramble:
  variables:
    mpi_command: ''
    batch_submit: '{{execute_experiment}}'
    processes_per_node: 1
    n_nodes: 1
    var1: value1
    var2: value2
    src_script_path: $workspace_configs/{template_filename}
  applications:
    template:
      workloads:
        test_template:
          experiments:
            test: {{}}
"""
    ws, ws_name = make_workspace_from_config(test_config)

    template_path = os.path.join(ws.config_dir, template_filename)

    with open(template_path, "w+", encoding="utf-8") as f:
        f.write(template_content)

    # Run workspace setup to trigger template expansion
    ramble_benchmark(workspace, "setup", "--dry-run", global_args=["-w", ws_name])

    # Verify the expanded file exists and has correct content
    run_dir = os.path.join(ws.experiment_dir, "template", "test_template", "test")
    expanded_path = os.path.join(run_dir, "expansion_script.sh")

    assert os.path.isfile(expanded_path)

    # Check a few lines to ensure expansion worked
    with open(expanded_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
        assert len(lines) == n_lines
        assert "Math statement 0: 0" == lines[0]
        assert "Variable statement 1: value1 value2" == lines[1]
        assert "Non-math statement 2: just some text with index 2" == lines[2]
        assert "Math statement 3: 6" == lines[3]

        # Check the last line
        i = n_lines - 1
        if i % 3 == 0:
            expected_last_line = f"Math statement {i}: {i + i}"
        elif i % 3 == 1:
            expected_last_line = f"Variable statement {i}: value1 value2"
        else:
            expected_last_line = f"Non-math statement {i}: just some text with index {i}"
        assert expected_last_line == lines[-1]

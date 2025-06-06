# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class WhenDirectives(ExecutableApplication):
    name = "when-directives"

    executable("test_exec", "echo '{test_variable}'", use_mpi=False)

    workload("test_wl", executable="test_exec")

    with default_args(workload="test_wl"):
        workload_variable(
            "test_variable",
            default="Test",
            description="Variable to print for testing",
        )

    # For register_phase()
    variant(
        "register_phase_when",
        default=False,
        values=[True, False],
        description="Register additional phase using when",
    )

    with when("+register_phase_when"):
        register_phase(
            "test_phase",
            pipeline="setup",
            run_before=["get_inputs"],
        )

    def _test_phase(self, workspace, app_inst):
        print("Test Phase")

    # For figure_of_merit() and figure_of_merit_context()
    variant(
        "register_fom_when",
        default=False,
        values=[True, False],
        description="Register figure of merit using when",
    )

    variant(
        "register_fom_context_when",
        default=False,
        values=[True, False],
        description="Register figure of merit context using when",
    )

    variant(
        "register_duplicate_name_fom_when",
        default=False,
        values=[True, False],
        description="Register figure of merit context using when",
    )

    log_file = "{experiment_run_dir}/test.out"
    always_on_fom_regex = (
        r".*(?P<context>test always)\s+(?P<always_fom>[0-9]+\.[0-9]+)"
    )
    fom_context_when_regex = r"(?P<when_context>test when context)\s+(?P<when_context_fom>[0-9]+\.[0-9]+).*"
    addtl_fom_regex = (
        r"test when fom\s+(?P<when_fom>[0-9]+\.[0-9]+).*"
        r"test always\s+(?P<always_when>[0-9]+)"
    )

    figure_of_merit_context(
        "always_context", regex=always_on_fom_regex, output_format="{context}"
    )

    figure_of_merit(
        "test_always_on_fom",
        fom_regex=always_on_fom_regex,
        group_name="always_fom",
        units="",
        log_file=log_file,
        contexts=["always_context"],
    )

    with when("+register_fom_context_when"):
        figure_of_merit_context(
            "test_context_when",
            regex=fom_context_when_regex,
            output_format="test when",
        )

        figure_of_merit(
            "test_fom",
            fom_regex=fom_context_when_regex,
            group_name="when_context_fom",
            units="",
            log_file=log_file,
            contexts=["test_context_when"],
        )

        figure_of_merit(
            "test_always_on_fom",
            fom_regex=addtl_fom_regex,
            group_name="always_when",
            units="integer",
            log_file=log_file,
            contexts=["test_context_when"],
        )

    with when("+register_fom_when"):
        figure_of_merit(
            "test_fom_when",
            fom_regex=addtl_fom_regex,
            group_name="when_fom",
            units="",
            log_file=log_file,
            contexts=["test_context_when"],
        )

    # For success_criteria()
    variant(
        "success_criteria_when",
        default=False,
        values=[True, False],
        description="Register success criteria using when",
    )

    success_criteria(
        "test_success_criteria_when",
        mode="string",
        match=r".*THIS TEXT NOT IN OUT FILE.*",
        when=["+success_criteria_when"],
    )

    # For register_template()
    variant(
        "register_template_when",
        default=False,
        values=[True, False],
        description="Register template using when",
    )

    register_template(
        "test_template_when",
        src_path="$workspace_shared/test_template.tpl",
        dest_path="test_template",
        when=["+register_template_when"],
    )

    # For register_builtin()
    variant(
        "register_builtin_when",
        default=False,
        values=[True, False],
        description="Register builtin using when",
    )

    register_builtin(
        "test_builtin_when", required=True, when=["+register_builtin_when"]
    )

    def test_builtin_when(self):
        return ['echo "when-builtin"']

    # For executable()
    variant(
        "executable_when",
        default=False,
        values=[True, False],
        description="Register executable using when",
    )

    variant(
        "executable_error_when",
        default=False,
        values=[True, False],
        description="Register executable with overlapping when condition",
    )

    executable(
        "test_exec_def_when",
        "echo 'executable version1'",
        use_mpi=False,
        when=["~executable_when"],
    )

    executable(
        "test_exec_def_when",
        "echo 'executable version2'",
        use_mpi=False,
        when=["+executable_when"],
    )

    executable(
        "test_exec_skipped",
        "echo 'skipped-executable'",
        use_mpi=False,
        when=["+executable_when"],
    )

    executable(
        "test_exec_def_when",
        "echo 'this should error when active",
        use_mpi=False,
        when=["+executable_error_when"],
    )

    workload(
        "exec_when_wl",
        executables=["test_exec", "test_exec_skipped", "test_exec_def_when"],
    )

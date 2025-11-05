# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.pkgmankit import *


class Info(PackageManagerBase):
    """Mock package manager to test info command. Should include all directives."""

    name = "info"

    # Shared language directives
    maintainers("maintainername")

    tags("tag1", "tag2")

    variant(
        "variant_name",
        default="variant_default",
        values=["variant_default", "a_variant_val"],
        description="A variant",
    )

    variant(
        "turn_on_required_directives",
        default=False,
        values=[True, False],
        description="Keep required directives off by default for testing",
    )

    variable(
        "obj_var_name",
        default="default_obj_val",
        description="An obj var",
        when=["variant_name=a_variant_val"],
    )

    environment_variable(
        "ENV_VAR_NAME",
        value="ENVVARVAL",
        description="test var",
    )

    required_variable(
        "required_var_name",
        description="A required var",
        when=["+turn_on_required_directives"],
    )

    archive_pattern("{experiment_run_dir}/archive_test.*")

    figure_of_merit_context(
        "fom_context", regex=r"fom context regex.*", output_format="{test}"
    )

    figure_of_merit(
        "fom_name",
        fom_regex=r"fom regex.*",
        group_name="test",
        units="s",
    )

    define_compiler("gcc12", pkg_spec="gcc@12.2.0")

    software_spec(
        "info-app",
        pkg_spec="info-app@5.0",
        compiler="gcc12",
    )

    package_manager_config(
        "config_name",
        "config:true",
        when="package_manager=info",
    )

    required_package(
        "info-app-dep",
        when=["package_manager=info", "+turn_on_required_directives"],
    )

    success_criteria(
        "success_criteria_name",
        mode="string",
        match=r"fom: test",
        file="log.file",
    )

    register_builtin("builtin_name", required=True)

    def builtin_name():
        return 'echo "builtin"'

    register_phase(
        "after_make_experiments",
        pipeline="setup",
        run_after=["make_experiments"],
    )

    def _after_make_experiments(self, workspace, app_inst=None):
        logger.all_msg("Inside a phase: after_make_experiments")

    target_shells("bash")

    register_template(
        "template_name",
        src_path="$workspace_shared/test_template.tpl",
        dest_path="test_template",
        when=["+register_template_when"],
    )

    formatted_executable(
        "formatted_exec_name",
        prefix="",
        indentation="4",
        commands=["{unformatted_batch_command}"],
    )

    register_validator(
        name="validator_name",
        predicate="{n_nodes} == 1",
        message=("Give me a node, Vasili. One node only, please"),
        fail_on_invalid=False,
    )

    # Package manager language
    package_manager_variable(
        "pm_var_name",
        default="default_pm_var_val",
        description="A PM variable",
    )

    package_manager_family("info-package-manager")

    def get_package_list(self, workspace):
        del workspace
        return []

    def package_name_from_spec(self, spec: str) -> str:
        return spec

    def environment_load_commands(self) -> List[str]:
        return []

    def environment_unload_commands(self) -> List[str]:
        return []

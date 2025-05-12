# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import os
import re

from ramble.appkit import *
from ramble.base_app.builtin.py_nemo import BasePyNemo

from spack.util.path import canonicalize_path

class PyNemo2(BasePyNemo):
    """A scalable generative AI framework built for researchers and
    developers working on Large Language Models, Multimodal, and
    Speech AI (Automatic Speech Recognition and Text-to-Speech)

    NeMo 2.0 requires NeMo container version >= 24.12.
    """

    name = "py-nemo-2"

    maintainers("duncanspani")

    tags("ml-framework", "machine-learning")

    # Add Nemo 2.0 config to archive.
    archive_pattern("{experiment_run_dir}/{nemo_config_name}/*")

    executable(
        "setup_transformer_cache",
        'bash -c "python3 -c \'from transformers import AutoTokenizer; AutoTokenizer.from_pretrained(\\"gpt2\\")\'"',
        use_mpi=True,
    )

    executable(
        "pretraining_exec",
        'bash -c "cd /opt/NeMo; git rev-parse HEAD; '
        "{custom_injected_string}; "
        'python3 -u {experiment_run_dir}/{nemo_config_name};"',
        use_mpi=True,
    )

    workload(
        "pretraining",
        executables=[
            "setup_transformer_cache",
            "pretraining_exec",
        ],
    )

    workload_group("all_workloads", workloads=["pretraining"])
    workload_group("pretraining", workloads=["pretraining"])

    workload_variable(
        "nemo_config_dir_path",
        default="",
        description="Path to Nemo 2.0 python config to be used.",
        workload_group="pretraining",
    )
    workload_variable(
        "nemo_config_name",
        default="",
        description="Name of NeMo 2.0 config under {nemo_config_dir_path}.",
        workload_group="pretraining",
    )

    workload_variable(
        "results_mount",
        default="{experiment_run_dir}:{experiment_run_dir}",
        description="Container mount for results data",
        workload_group="pretraining",
    )
    environment_variable(
        "NEMO_CONTAINER_MOUNTS",
        value="{results_mount}",
        description="All container mounts in an environment variable",
        workload_group="pretraining",
    )
    workload_variable(
        "container_mounts",
        default="{results_mount}",
        description="All container mounts in a ramble variable",
        workload_group="pretraining",
    )

    register_phase(
        "copy_config", pipeline="setup", run_after=["make_experiments"]
    )

    def _copy_config(self, workspace, app_inst):
        """Copies user provided NeMo 2.0 python config to the experiment's
        run directory."""

        source_path = get_file_path(
            canonicalize_path(
                os.path.join(
                    self.expander.expand_var_name("nemo_config_dir_path"),
                    self.expander.expand_var_name("nemo_config_name"),
                )
            ),
            workspace,
        )

        if not os.path.exists(source_path):
            return

        dest_path = os.path.join(
            app_inst.expander.expand_var_name("experiment_run_dir"),
            app_inst.expander.expand_var_name("nemo_config_name"),
        )

        self.expander.flush_used_variable_stage()

        with open(source_path) as f:
            content = f.read()

        with open(dest_path, "w+") as f:
            f.write(app_inst.expander.expand_var(content))

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

import ruamel.yaml as yaml
import spack.util.spack_yaml as syaml

import ramble.util.yaml_generation

from spack.util.path import canonicalize_path


class PyNemo(ExecutableApplication):
    """A scalable generative AI framework built for researchers and
    developers working on Large Language Models, Multimodal, and
    Speech AI (Automatic Speech Recognition and Text-to-Speech)

    model.ffn_hidden_size gets a default value of {4*{model.hidden_size}} if it
    can not be cast to an integer from the default config.
    """

    name = "py-nemo"

    maintainers("douglasjacobsen")

    tags("ml-framework", "machine-learning")

    archive_pattern("{experiment_run_dir}/{nemo_generated_config_name}")

    executable(
        "setup_transformer_cache",
        'bash -c "python3 -c \'from transformers import AutoTokenizer; AutoTokenizer.from_pretrained(\\"gpt2\\")\'"',
        use_mpi=True,
    )

    executable(
        "pretraining_exec",
        'bash -c "cd /opt/NeMo; git rev-parse HEAD; '
        "{custom_injected_string}; "
        "python3 -u /opt/NeMo/examples/nlp/language_modeling/megatron_gpt_pretraining.py "
        '--config-path={nemo_generated_config_path} --config-name={nemo_generated_config_name}"',
        use_mpi=True,
    )

    executable(
        "create_logs", "mkdir {exp_manager.explicit_log_dir}", use_mpi=False
    )

    input_file(
        "nemo_fetched_config",
        url="https://raw.githubusercontent.com/NVIDIA/NeMo-Framework-Launcher/refs/tags/{nemo_launcher_tag}/launcher_scripts/conf/{nemo_stage}/{nemo_model}/{nemo_config_name}.yaml",
        expand=False,
        target_dir="{model_inputs}",
        description="Base config for NeMo experiments",
    )

    workload(
        "pretraining",
        executables=[
            "create_logs",
            "setup_transformer_cache",
            "pretraining_exec",
        ],
        inputs=["nemo_fetched_config"],
    )

    default_config_string = "{default_config_value}"

    workload_group("all_workloads", workloads=["pretraining"])
    workload_group("pretraining", workloads=["pretraining"])
    all_workloads = ["pretraining"]

    workload_variable(
        "custom_injected_string",
        default="tail /dev/null",
        description="Custom string to inject before execution NeMo workload",
        workload_group="all_workloads",
    )

    workload_variable(
        "model_inputs",
        default="{workload_input_dir}/{nemo_stage}/{nemo_model}",
        description="NeMo model input directory",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_container_version",
        default="24.07",
        description="Version for NeMo container",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_launcher_tag",
        default="24.07",
        description="Tag of NeMo-Framework-Launcher repo to extract inputs from",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_stage",
        default="training",
        description="Stage to run in NeMo",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_model",
        default="gpt3",
        description="Model to run in NeMo",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_config_name",
        default="5b",
        description="Configuration name to run in NeMo. This is the name of the input "
        + "yaml file without the extension. e.g. 5b.yaml -> 5b, while "
        + "mixtral_8x22b.yaml -> mixtral_8x22b",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_base_config",
        default="{nemo_fetched_config}",
        description="Path to base config used for generating experiments. "
        + "Defaults to the fetched input, but can refer to a provided input.",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_generated_config_name",
        default="nemo.yaml",
        description="Name of nemo config file",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_generated_config_path",
        default="{experiment_run_dir}",
        description="Path where nemo config file is contained",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_remove_variables",
        default=[],
        description="Name of variables to remove from the base nemo config",
        workload_group="all_workloads",
    )

    workload_variable(
        "cuda_visible_devices",
        default="0,1,2,3,4,5,6,7",
        description="Comma delimited list of CUDA device IDs.",
        workload_group="all_workloads",
    )
    environment_variable(
        "CUDA_VISIBLE_DEVICES",
        value="{cuda_visible_devices}",
        description="Comma delimited list of CUDA device IDs",
        workloads=all_workloads,
    )

    workload_variable(
        "transformers_offline",
        default="0",
        description="Whether transformers are offline (0) or not (1)",
        workload_group="all_workloads",
    )
    environment_variable(
        "TRANSFORMERS_OFFLINE",
        value="{transformers_offline}",
        description="Whether transformers are offline (0) or not (1)",
        workloads=all_workloads,
    )

    workload_variable(
        "torch_nccl_avoid_record_streams",
        default="1",
        description="Avoid (1) recording streams for Torch NCCL, or not (0)",
        workload_group="all_workloads",
    )
    environment_variable(
        "TORCH_NCCL_AVOID_RECORD_STREAMS",
        value="{torch_nccl_avoid_record_streams}",
        description="Avoid (1) recording streams for Torch NCCL, or not (0)",
        workloads=all_workloads,
    )

    workload_variable(
        "nccl_nvls_enable",
        default="0",
        description="Enable (1) NCCL NVLS or not (0)",
        workload_group="all_workloads",
    )
    environment_variable(
        "NCCL_NVLS_ENABLE",
        value="{nccl_nvls_enable}",
        description="Enable (1) NCCL NVLS or not (0)",
        workloads=all_workloads,
    )

    workload_variable(
        "results_mount",
        default="{experiment_run_dir}:{experiment_run_dir}",
        description="Container mount for results data",
        workload_group="all_workloads",
    )
    workload_variable(
        "logs_mount",
        default="{exp_manager.explicit_log_dir}:{exp_manager.explicit_log_dir}",
        description="Container mount for results data",
        workload_group="all_workloads",
    )
    environment_variable(
        "NEMO_CONTAINER_MOUNTS",
        value="{logs_mount},{results_mount}",
        description="All container mounts in an environment variable",
        workloads=all_workloads,
    )
    workload_variable(
        "container_mounts",
        default="{logs_mount},{results_mount}",
        description="All container mounts in a ramble variable",
        workload_group="all_workloads",
    )

    environment_variable(
        "NEMO_HOST_VARS",
        value="TRANSFORMERS_OFFLINE,TORCH_NCCL_AVOID_RECORD_STREAMS,NCCL_NVLS_ENABLE,CUDA_VISIBLE_DEVICES",
        description="Host variables for NeMo",
        workloads=all_workloads,
    )

    # Run parameters
    workload_variable(
        "run.name",
        default="{nemo_model}_{nemo_config_name}",
        description="Name of run",
        workload_group="all_workloads",
    )
    workload_variable(
        "run.results_dir",
        default="{experiment_run_dir}",
        description="Experiment results directory",
        workload_group="all_workloads",
    )
    workload_variable(
        "run.time_limit",
        default="6-00:00:00",
        description="Experiment time limit",
        workload_group="all_workloads",
    )
    workload_variable(
        "run.dependency",
        default="singleton",
        description="Experiment dependency type",
        workload_group="all_workloads",
    )

    # Trainer parameters
    workload_variable(
        "trainer.num_nodes",
        default="{n_nodes}",
        description="Number of nodes",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.devices",
        default="{gpus_per_node}",
        description="Number of devices per node",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.accelerator",
        default="gpu",
        description="Accelerator to use as device",
        workload_group="pretraining",
    )

    # Exp manager parameters
    workload_variable(
        "exp_manager.explicit_log_dir",
        default="{experiment_run_dir}/nemo_logs",
        description="Log directory for exp manager",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.exp_dir",
        default=None,
        description="Experiment directory for exp manager",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.name",
        default="{nemo_stage}_{nemo_model}_{nemo_config_name}",
        description="Exp manager name",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.wandb_logger_kwargs.project",
        default="nemo_{nemo_model}",
        description="wandb logger project",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.wandb_logger_kwargs.name",
        default="{nemo_model}_{nemo_config_name}",
        description="wandb logger name",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.checkpoint_callback_params.model_parallel_size",
        default="{model.tensor_model_parallel_size}*{model.pipeline_model_parallel_size}",
        description="Parallel size",
        workload_group="pretraining",
    )

    workload_variable(
        "processed_log_file",
        default="{experiment_run_dir}/processed_{experiment_name}.out",
        description="Path to store processed NeMo output",
        workload_group="pretraining",
    )

    final_epoch_regex = (
        r"Epoch (?P<epoch_id>[0-9]+):\s+:\s+(?P<pct_complete>[0-9]+)%.*\s+"
        + r"(?P<step_idx>[0-9]+)\/(?P<max_itr>[0-9]+) \[(?P<elapsed_time>[0-9]+:[0-9]+)<"
        + r"(?P<remaining_time>[0-9]+:[0-9]+),(\s+v_num=(?P<v_num>.*),)* reduced_train_loss="
        + r"(?P<reduced_train_loss>[0-9]+\.[0-9]+), global_step=(?P<global_step>[0-9]+\.[0-9]+), "
        + r"consumed_samples=(?P<consumed_samples>[0-9]+\.[0-9]+), train_step_timing in s="
        + r"(?P<train_step_timing>[0-9]+\.[0-9]+)(, val_loss=(?P<val_loss>[0-9]+\.[0-9]+))*\]"
    )

    figure_of_merit(
        "Final Epoch ID",
        fom_regex=final_epoch_regex,
        group_name="epoch_id",
        log_file="{processed_log_file}",
    )
    figure_of_merit(
        "Final Step ID",
        fom_regex=final_epoch_regex,
        group_name="step_idx",
        log_file="{processed_log_file}",
    )
    figure_of_merit(
        "Final Elapsed Time",
        fom_regex=final_epoch_regex,
        group_name="elapsed_time",
        log_file="{processed_log_file}",
    )
    figure_of_merit(
        "Final Elapsed Seconds",
        fom_regex=r"Elapsed seconds: (?P<seconds>[0-9]+)",
        group_name="seconds",
        log_file="{experiment_run_dir}/elapsed_seconds",
    )
    figure_of_merit(
        "Final Remaining Time",
        fom_regex=final_epoch_regex,
        group_name="remaining_time",
        log_file="{processed_log_file}",
    )
    figure_of_merit(
        "Final Step Timing",
        fom_regex=final_epoch_regex,
        group_name="train_step_timing",
        log_file="{processed_log_file}",
    )

    per_epoch_regex = (
        r"Epoch (?P<epoch_id>[0-9]+):\s+:\s+(?P<pct_complete>[0-9]+)%.*\s+"
        + r"(?P<step_idx>[0-9]+)/(?P<max_itr>[0-9]+) \[(?P<elapsed_time>[0-9:]+)<"
        + r"(?P<remaining_time>[0-9:]+).*"
    )

    epoch_context_name = "Epoch ID - Step ID"
    figure_of_merit_context(
        epoch_context_name,
        regex=per_epoch_regex,
        output_format="{epoch_id}-{step_idx}/{max_itr}",
    )
    figure_of_merit(
        "Epoch ID",
        fom_regex=per_epoch_regex,
        group_name="epoch_id",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "Percent Complete",
        fom_regex=per_epoch_regex,
        group_name="pct_complete",
        units="%",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "Step ID",
        fom_regex=per_epoch_regex,
        group_name="step_idx",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "Elapsed Time",
        fom_regex=per_epoch_regex,
        group_name="elapsed_time",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "Remaining Time",
        fom_regex=per_epoch_regex,
        group_name="remaining_time",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "v_num",
        fom_regex=r"Epoch.*v_num=(?P<v_num>\S+)[,\]]",
        group_name="v_num",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "reduced_train_loss",
        fom_regex=r"Epoch.*reduced_train_loss=(?P<reduced_train_loss>[0-9\.]+)[,\]]",
        group_name="reduced_train_loss",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "global_step",
        fom_regex=r"Epoch.*global_step=(?P<global_step>[0-9\.]+)[,\]]",
        group_name="global_step",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "consumed_samples",
        fom_regex=r"Epoch.*consumed_samples=(?P<consumed_samples>[0-9\.]+)[,\]]",
        group_name="consumed_samples",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "train_step_timing",
        fom_regex=r"Epoch.*train_step_timing in s=(?P<train_step_time>[0-9\.]+)[,\]]",
        group_name="train_step_time",
        units="s",
        log_file="{processed_log_file}",
        contexts=[epoch_context_name],
    )

    success_criteria(
        "training-complete",
        mode="string",
        match=".*`Trainer.fit` stopped: `max_steps=.*` reached.",
        file="{processed_log_file}",
    )

    register_phase(
        "ingest_default_configs",
        pipeline="setup",
        run_before=["make_experiments"],
    )

    def _ingest_default_configs(self, workspace, app_inst):
        """Read config options from nemo_base_config, and define any that were
        not defined in the input ramble.yaml or workload definition."""

        base_config = get_file_path(
            canonicalize_path(
                self.expander.expand_var_name("nemo_base_config")
            ),
            workspace,
        )

        # Avoid problems with missing base config files
        if not os.path.exists(base_config):
            return

        config_data = ramble.util.yaml_generation.read_config_file(base_config)

        for option_name in ramble.util.yaml_generation.all_config_options(
            config_data
        ):
            if option_name not in self.variables:
                value = ramble.util.yaml_generation.get_config_value(
                    config_data, option_name
                )

                self.define_variable(option_name, value)

        # Ensure a default for ffn_hidden_size if not already set, and not an integer.
        ffn_hidden_size = ramble.util.yaml_generation.get_config_value(
            config_data, "model.ffn_hidden_size"
        )
        try:
            ffn_hidden_size = int(ffn_hidden_size)
        except ValueError:
            logger.warn(
                "NeMo attribute model.ffn_hidden_size can not be cast to an integer. "
                "Replacing with '{4*{model.hidden_size}}' to ensure this experiment runs."
            )
            ffn_hidden_size = "{4*{model.hidden_size}}"
        self.define_variable("model.ffn_hidden_size", ffn_hidden_size)

    register_phase(
        "write_config", pipeline="setup", run_after=["make_experiments"]
    )

    def _write_config(self, workspace, app_inst):
        base_config = get_file_path(
            canonicalize_path(
                self.expander.expand_var_name("nemo_base_config")
            ),
            workspace,
        )

        # Avoid errors for missing base config files
        if not os.path.exists(base_config):
            return

        # Remove all variables that should be removed
        remove_vars = self.expander.expand_var_name(
            "nemo_remove_variables", merge_used_stage=False, typed=True
        )
        self.expander.flush_used_variable_stage()

        config_data = ramble.util.yaml_generation.read_config_file(base_config)

        ramble.util.yaml_generation.apply_default_config_values(
            config_data, self, self.default_config_string
        )

        # Set config options in config_data
        for var_name in self.variables:
            if "." in var_name and len(var_name.split(".")) > 1:
                var_val = self.expander.expand_var(
                    self.expander.expansion_str(var_name), typed=True
                )

                # Convert any invalid tuples back to their default strings.
                if isinstance(var_val, tuple):
                    var_val = self.expander.expand_var(
                        self.expander.expansion_str(var_name)
                    )
                elif isinstance(var_val, list):
                    for i in range(0, len(var_val)):
                        var_val[i] = self.expander.expand_var(
                            var_val[i], typed=True
                        )

                ramble.util.yaml_generation.set_config_value(
                    config_data, var_name, var_val, force=True
                )

        # Remove requested options
        for var_name in remove_vars:
            if "." in var_name and len(var_name.split(".")) > 1:
                ramble.util.yaml_generation.remove_config_value(
                    config_data, var_name
                )

        config_path = canonicalize_path(
            os.path.join(
                self.expander.expand_var("{nemo_generated_config_path}"),
                self.expander.expand_var("{nemo_generated_config_name}"),
            )
        )

        # Ensure all instances of ${data_dir} are replaced correctly
        config_str = yaml.dump(
            config_data,
            default_flow_style=False,
            width=syaml.maxint,
            Dumper=syaml.OrderedLineDumper,
        )

        config_str = config_str.replace(
            "${data_dir}",
            self.expander.expand_var("{workload_input_dir}/data"),
        )
        with open(config_path, "w+") as f:
            f.write(config_str)

    register_phase(
        "preprocess_log",
        pipeline="analyze",
        run_before=["analyze_experiments"],
    )

    def _preprocess_log(self, workspace, app_inst):
        log_file = get_file_path(
            canonicalize_path(self.expander.expand_var_name("log_file")),
            workspace,
        )

        elapsed_s = 0

        final_regex = re.compile(self.final_epoch_regex)

        if os.path.exists(log_file):
            with open(log_file, "r", encoding="ISO-8859-1") as f:
                data = f.read()

            processed_log = self.expander.expand_var(
                "{experiment_run_dir}/processed_{experiment_name}.out"
            )

            with open(processed_log, "w+") as f:
                f.write(
                    data.replace("\x13", "\n")
                    .replace("\x96\x88", "")
                    .replace("â", "")
                )

            with open(processed_log) as f:
                for line in f.readlines():
                    m = final_regex.match(line)

                    if m:
                        timestamp = m.group("elapsed_time")

                        time_parts = timestamp.split(":")

                        part_s = 0
                        mult = 1
                        for part in reversed(time_parts):
                            part_s += int(part) * mult
                            mult = mult * 60
                        elapsed_s += part_s

            sec_file_path = self.expander.expand_var(
                "{experiment_run_dir}/elapsed_seconds"
            )
            with open(sec_file_path, "w+") as f:
                f.write(f"Elapsed seconds: {elapsed_s}")

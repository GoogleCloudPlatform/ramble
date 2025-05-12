import os
import re

from ramble.appkit import *
from spack.util.path import canonicalize_path


class BasePyNemo(ExecutableApplication):
    """Define a base class for PyNemo applications."""

    tags("ml-framework", "machine-learning")

    workload_group("pretraining", workloads=[])

    workload_variable(
        "custom_injected_string",
        default="tail /dev/null",
        description="Custom string to inject before execution NeMo workload",
        workload_group="pretraining",
    )
    workload_variable(
        "nemo_container_version",
        default="24.07",
        description="Version for NeMo container",
        workload_group="pretraining",
    )
    workload_variable(
        "nemo_stage",
        default="training",
        description="Stage to run in NeMo",
        workload_group="pretraining",
    )
    workload_variable(
        "cuda_visible_devices",
        default="0,1,2,3,4,5,6,7",
        description="Comma delimited list of CUDA device IDs.",
        workload_group="pretraining",
    )
    #environment_variable(
    #    "CUDA_VISIBLE_DEVICES",
    #    value="{cuda_visible_devices}",
    #    description="Comma delimited list of CUDA device IDs",
    #    workload_group="pretraining",
    #)
    workload_variable(
        "transformers_offline",
        default="0",
        description="Whether transformers are offline (0) or not (1)",
        workload_group="pretraining",
    )
    #environment_variable(
    #    "TRANSFORMERS_OFFLINE",
    #    value="{transformers_offline}",
    #    description="Whether transformers are offline (0) or not (1)",
    #    workload_group="pretraining",
    #)
    workload_variable(
        "torch_nccl_avoid_record_streams",
        default="1",
        description="Avoid (1) recording streams for Torch NCCL, or not (0)",
        workload_group="pretraining",
    )
    #environment_variable(
    #    "TORCH_NCCL_AVOID_RECORD_STREAMS",
    #    value="{torch_nccl_avoid_record_streams}",
    #    description="Avoid (1) recording streams for Torch NCCL, or not (0)",
    #    workload_group="pretraining",
    #)
    workload_variable(
        "nccl_nvls_enable",
        default="0",
        description="Enable (1) NCCL NVLS or not (0)",
        workload_group="pretraining",
    )
    #environment_variable(
    #    "NCCL_NVLS_ENABLE",
    #    value="{nccl_nvls_enable}",
    #    description="Enable (1) NCCL NVLS or not (0)",
    #    workload_group="pretraining",
    #)
    workload_variable(
        "results_mount",
        default="{experiment_run_dir}:{experiment_run_dir}",
        description="Container mount for results data",
        workload_group="pretraining",
    )
    #environment_variable(
    #    "NEMO_CONTAINER_MOUNTS",
    #    value="{results_mount}",
    #    description="All container mounts in an environment variable",
    #    workload_group="pretraining",
    #)
    workload_variable(
        "container_mounts",
        default="{results_mount}",
        description="All container mounts in a ramble variable",
        workload_group="pretraining",
    )
    #environment_variable(
    #    "NEMO_HOST_VARS",
    #    value="TRANSFORMERS_OFFLINE,TORCH_NCCL_AVOID_RECORD_STREAMS,NCCL_NVLS_ENABLE,CUDA_VISIBLE_DEVICES",
    #    description="Host variables for NeMo",
    #    workload_group="pretraining",
    #)
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
        r"Epoch (?P<epoch_id>[0-9]+)(:\s+)+(?P<pct_complete>[0-9]+)%.*\s+"
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

    per_step_regex = (
        r"Training epoch\s(?P<epoch>[e0-9\.\-]+),\s.*iteration\s(?P<iteration>[e0-9\/\.\-]+)"
        r"[\s|]+lr:\s(?P<learning_rate>[e0-9\.\-]+)[\s|]+"
        r"global_batch_size:\s(?P<global_batch_size>[e0-9\.\-]+)"
        r"[\s|]+global_step:\s(?P<global_step>[e0-9\.\-]+)"
        r"[\s|]+reduced_train_loss:\s(?P<reduced_train_loss>[e0-9\.\-]+)"
        r"[\s|]+train_step_timing in s:\s(?P<train_step_timing>[e0-9\.\-]+)"
    )
    step_context_name = "Global Step ID"
    figure_of_merit_context(
        step_context_name,
        regex=per_step_regex,
        output_format="{global_step}",
    )
    figure_of_merit(
        "epoch",
        fom_regex=per_step_regex,
        group_name="epoch",
        log_file="{processed_log_file}",
        contexts=[step_context_name],
    )
    figure_of_merit(
        "iteration",
        fom_regex=per_step_regex,
        group_name="iteration",
        log_file="{processed_log_file}",
        contexts=[step_context_name],
    )
    figure_of_merit(
        "learning_rate",
        fom_regex=per_step_regex,
        group_name="learning_rate",
        log_file="{processed_log_file}",
        contexts=[step_context_name],
    )
    figure_of_merit(
        "reduced_train_loss",
        fom_regex=per_step_regex,
        group_name="reduced_train_loss",
        log_file="{processed_log_file}",
        contexts=[step_context_name],
    )
    figure_of_merit(
        "global_step",
        fom_regex=per_step_regex,
        group_name="global_step",
        log_file="{processed_log_file}",
        contexts=[step_context_name],
    )
    figure_of_merit(
        "train_step_timing",
        fom_regex=per_step_regex,
        group_name="train_step_timing",
        units="s",
        log_file="{processed_log_file}",
        contexts=[step_context_name],
    )

    success_criteria(
        "training-complete",
        mode="string",
        match=".*?`Trainer.fit` stopped: `max_steps=.*?` reached.",
        file="{processed_log_file}",
    )

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
            with open(log_file, encoding="ISO-8859-1") as f:
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

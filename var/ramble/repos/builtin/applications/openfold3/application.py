# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class Openfold3(ExecutableApplication):
    """OpenFold3 is a PyTorch reproduction of AlphaFold 3 and AlphaFold 2,
    highly optimized for fast protein structure prediction.
    """

    name = "openfold3"

    tags("bioinformatics", "machine-learning", "protein-folding", "hpc")

    maintainers("rfbgo")

    # Define pip software requirement
    with when("package_manager_family=pip"):
        software_spec(
            "torch",
            pkg_spec="torch",
        )
        software_spec(
            "deepspeed",
            pkg_spec="deepspeed",
        )
        software_spec(
            "nvidia-cutlass",
            pkg_spec="nvidia-cutlass",
        )
        software_spec(
            "openfold3",
            pkg_spec="openfold3",
        )
        required_package("torch")
        required_package("deepspeed")
        required_package("nvidia-cutlass")
        required_package("openfold3")

    # Pre-trained model checkpoint for OpenFold3
    input_file(
        "openfold3_ptm_weights",
        url="https://openfold3-data.s3.amazonaws.com/openfold3-parameters/of3-p2-155k.pt",
        description="Pre-trained OpenFold3 p2 155k weights",
        expand=False,
    )

    # Stable Github snapshot for example Ubiquitin query JSON file
    input_file(
        "query_ubiquitin",
        url="https://raw.githubusercontent.com/aqlaboratory/openfold-3/119962b517a230cca9ee0550c13d58fe4bc303ed/examples/example_inference_inputs/query_ubiquitin.json",
        description="Example Ubiquitin query JSON file for OpenFold3 prediction",
        expand=False,
    )

    # DNA PTM benchmark query
    input_file(
        "query_dna_ptm",
        url="https://raw.githubusercontent.com/aqlaboratory/openfold-3/119962b517a230cca9ee0550c13d58fe4bc303ed/examples/example_inference_inputs/query_dna_ptm.json",
        description="Example DNA PTM query JSON file for OpenFold3 prediction",
        expand=False,
    )

    # Homomer benchmark query
    input_file(
        "query_homomer",
        url="https://raw.githubusercontent.com/aqlaboratory/openfold-3/119962b517a230cca9ee0550c13d58fe4bc303ed/examples/example_inference_inputs/query_homomer.json",
        description="Example Homomer protein query JSON file for OpenFold3 prediction",
        expand=False,
    )

    # Multimer benchmark query
    input_file(
        "query_multimer",
        url="https://raw.githubusercontent.com/aqlaboratory/openfold-3/119962b517a230cca9ee0550c13d58fe4bc303ed/examples/example_inference_inputs/query_multimer.json",
        description="Example Multimer protein query JSON file for OpenFold3 prediction",
        expand=False,
    )

    # Protein Ligand benchmark query
    input_file(
        "query_protein_ligand",
        url="https://raw.githubusercontent.com/aqlaboratory/openfold-3/119962b517a230cca9ee0550c13d58fe4bc303ed/examples/example_inference_inputs/query_protein_ligand.json",
        description="Example Protein-Ligand query JSON file for OpenFold3 prediction",
        expand=False,
    )

    # Define primary executable for running OpenFold3 inference
    executable(
        "predict",
        "run_openfold predict "
        "--query-json {query_json} "
        "--output-dir {experiment_run_dir} "
        "--inference-ckpt-path {openfold_checkpoint_path} "
        "{extra_args}",
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )

    # Define prediction workload and bind input files
    workload(
        "predict",
        executable="predict",
        inputs=[
            "openfold3_ptm_weights",
            "query_ubiquitin",
            "query_dna_ptm",
            "query_homomer",
            "query_multimer",
            "query_protein_ligand",
        ],
    )

    # Workload variables
    workload_variable(
        "query_json",
        default="{query_ubiquitin}",
        description="Path to the input query JSON file",
        workload="predict",
    )

    workload_variable(
        "openfold_checkpoint_path",
        default="{openfold3_ptm_weights}",
        description="Path to the OpenFold3 model weights checkpoint file",
        workload="predict",
    )

    workload_variable(
        "extra_args",
        default="",
        description="Additional command-line arguments for OpenFold3 inference",
        workload="predict",
    )

    # Figures of Merit
    figure_of_merit(
        "Alignment Generation Time",
        log_file="timing.out",
        fom_regex=r".*Alignment\s+Generation\s+Time\s+=\s+(?P<align_time>[0-9\.]+)\s+s",
        group_name="align_time",
        units="s",
    )

    figure_of_merit(
        "Inference Time",
        log_file="timing.out",
        fom_regex=r".*Inference\s+Time\s+=\s+(?P<time>[0-9\.]+)\s+s",
        group_name="time",
        units="s",
    )

    figure_of_merit(
        "Relaxation Time",
        log_file="timing.out",
        fom_regex=r".*Relaxation\s+Time\s+=\s+(?P<relax_time>[0-9\.]+)\s+s",
        group_name="relax_time",
        units="s",
    )

    figure_of_merit(
        "Average pLDDT",
        log_file="timing.out",
        fom_regex=r".*Average\s+pLDDT\s+=\s+(?P<plddt>[0-9\.]+)",
        group_name="plddt",
    )

    figure_of_merit(
        "predicted TM-score (pTM)",
        log_file="timing.out",
        fom_regex=r".*predicted\s+TM-score\s+\(pTM\)\s+=\s+(?P<ptm>[0-9\.]+)",
        group_name="ptm",
    )

    figure_of_merit(
        "interface predicted TM-score (ipTM)",
        log_file="timing.out",
        fom_regex=r".*interface\s+predicted\s+TM-score\s+\(ipTM\)\s+=\s+(?P<iptm>[0-9\.]+)",
        group_name="iptm",
    )

    figure_of_merit(
        "Predicted Distance Error (GPDE)",
        log_file="timing.out",
        fom_regex=r".*Predicted\s+Distance\s+Error\s+\(GPDE\)\s+=\s+(?P<gpde>[0-9\.]+)",
        group_name="gpde",
    )

    # Success criteria
    success_criteria(
        "predict_success",
        mode="string",
        match=r".*Successful\s+Queries:\s+[1-9]\d*.*",
    )

    def _prepare_analysis(self, workspace, app_inst):
        import glob
        import json
        import os

        run_dir = app_inst.expander.experiment_run_dir
        timing_files = glob.glob(
            os.path.join(run_dir, "*", "seed_*", "timing.json")
        )
        if not timing_files:
            logger.warn(
                "No timing.json files found for OpenFold3 predictions."
            )
            return

        for timing_file in timing_files:
            try:
                with open(timing_file, encoding="utf-8") as f:
                    data = json.load(f)

                timing_out_path = os.path.join(run_dir, "timing.out")
                with open(timing_out_path, "w", encoding="utf-8") as f_out:
                    if "runtime_s" in data:
                        f_out.write(
                            f"Inference Time = {data.get('runtime_s', 0.0)} s\n"
                        )
                    else:
                        f_out.write(
                            f"Alignment Generation Time = {data.get('alignment_generation_s', 0.0)} s\n"
                        )
                        f_out.write(
                            f"Inference Time = {data.get('inference_s', 0.0)} s\n"
                        )
                        f_out.write(
                            f"Relaxation Time = {data.get('relaxation_s', 0.0)} s\n"
                        )
                        f_out.write(
                            f"Total Time = {data.get('total_s', 0.0)} s\n"
                        )

                    # Parse confidences_aggregated.json files
                    conf_dir = os.path.dirname(timing_file)
                    conf_files = glob.glob(
                        os.path.join(conf_dir, "*_confidences_aggregated.json")
                    )
                    best_conf = None
                    best_score = -1.0
                    for conf_file in conf_files:
                        try:
                            with open(conf_file, encoding="utf-8") as f_conf:
                                conf_data = json.load(f_conf)
                            score = conf_data.get("sample_ranking_score", 0.0)
                            if score > best_score:
                                best_score = score
                                best_conf = conf_data
                        except Exception:
                            pass

                    if best_conf:
                        if "avg_plddt" in best_conf:
                            f_out.write(
                                f"Average pLDDT = {best_conf.get('avg_plddt', 0.0)}\n"
                            )
                        elif "plddt" in best_conf:
                            f_out.write(
                                f"Average pLDDT = {best_conf.get('plddt', 0.0) * 100.0}\n"
                            )

                        if "ptm" in best_conf:
                            f_out.write(
                                f"predicted TM-score (pTM) = {best_conf.get('ptm', 0.0)}\n"
                            )

                        if "iptm" in best_conf:
                            f_out.write(
                                f"interface predicted TM-score (ipTM) = {best_conf.get('iptm', 0.0)}\n"
                            )

                        if "gpde" in best_conf:
                            f_out.write(
                                f"Predicted Distance Error (GPDE) = {best_conf.get('gpde', 0.0)}\n"
                            )
                        elif "gp" in best_conf:
                            f_out.write(
                                f"Predicted Distance Error (GPDE) = {best_conf.get('gp', 0.0)}\n"
                            )

                logger.debug(
                    f"Successfully wrote formatted timings and quality metrics to {timing_out_path}"
                )
                break
            except Exception as e:
                logger.warn(f"Failed to parse timing/confidence files: {e}")

# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

# Placeholder for reports unit tests

# Test command line args

# Test file import for JSON and YAML
# - non-repeated experiments
# - repeated experiments

# Test normalization of data, and error when first value is zero

# Test that PDF is generated and contains data (size > some value?)

# Possible to test that a specific chart was correctly generated? Not sure...
import pytest

from ramble.reports import *

from matplotlib.backends.backend_pdf import PdfPages
import os

results = {
    "experiments": [
        {
            "RAMBLE_STATUS": "SUCCESS",
            "name": "exp_1",
            "n_nodes": 1,
            # "application_namespace": "test_app",
            # "workload_name": "test_workload",
            "simplified_workload_namespace": "test_app_test_workload",
            "RAMBLE_VARIABLES": {},
            "RAMBLE_RAW_VARIABLES": {},
            "CONTEXTS": [
                {
                    "name": "null",
                    "display_name": "null",
                    "foms": [
                        {
                            "name": "fom_1",
                            "value": 42.0,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                            "fom_type": {"name": "MEASURE", "better_direction": "INDETERMINATE"},
                        },
                        {
                            "name": "fom_2",
                            "value": 50,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                            "fom_type": {"name": "MEASURE", "better_direction": "INDETERMINATE"},
                        },
                    ],
                },
            ],
        },
        {
            "RAMBLE_STATUS": "SUCCESS",
            "name": "exp_2",
            "n_nodes": 2,
            # "application_namespace": "test_namespace",
            # "workload_name": "test_workload",
            "simplified_workload_namespace": "test_app_test_workload",
            "RAMBLE_VARIABLES": {},
            "RAMBLE_RAW_VARIABLES": {},
            "CONTEXTS": [
                {
                    "name": "null",
                    "display_name": "null",
                    "foms": [
                        {
                            "name": "fom_1",
                            "value": 28.0,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                            "fom_type": {"name": "MEASURE", "better_direction": "INDETERMINATE"},
                        },
                        {
                            "name": "fom_2",
                            "value": 55,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                            "fom_type": {"name": "MEASURE", "better_direction": "INDETERMINATE"},
                        },
                    ],
                },
            ],
        },
    ]
}


def create_test_exp(
    success,
    name,
    n_nodes,
    ns,
    ramble_vars,
    ramble_raw_vars,
    context,
    fom_name,
    fom_value,
    units,
    origin,
    origin_type,
    fom_type,
    better_direction,
    fv,
    ifv,
    normalized=False,
):
    test_exp_dict = {
        "RAMBLE_STATUS": success,
        "name": name,
        "n_nodes": n_nodes,
        "simplified_workload_namespace": ns,
        "RAMBLE_VARIABLES": ramble_vars,
        "RAMBLE_RAW_VARIABLES": ramble_raw_vars,
        "context": context,
        "fom_name": fom_name,
        "fom_value": fom_value,
        "fom_units": units,
        "fom_origin": origin,
        "fom_origin_type": origin_type,
        "fom_type": fom_type,
        "better_direction": better_direction,
        "series": ns,
        "normalized_fom_value" if normalized else "fom_value": fv,
    }
    # ideal_perf_value is not calculated for plots without better_direction
    if ifv:
        test_exp_dict["ideal_perf_value"] = ifv
    return test_exp_dict


@pytest.mark.parametrize(
    "values",
    [
        (StrongScalingPlot, "fom_1", 42.0, 42.0, 42.0, 28.0, 28.0, 21.0, False),
        (StrongScalingPlot, "fom_1", 42.0, 1.0, 1.0, 28.0, 1.5, 2.0, True),
        (WeakScalingPlot, "fom_2", 50, 50, None, 55, 55.0, None, False),
        (WeakScalingPlot, "fom_2", 50.0, 1.0, None, 55.0, 1.1, None, True),
    ],
)
def test_scaling_plots(mutable_mock_workspace_path, tmpdir_factory, values):

    report_name = "unit_test"
    report_dir_path = tmpdir_factory.mktemp(report_name)
    pdf_path = os.path.join(report_dir_path, f"{report_name}.pdf")

    plot_type, fom_name, fom1, nfv1, ideal1, fom2, nfv2, ideal2, normalize = values

    test_spec = [fom_name, "n_nodes"]

    ideal_data = []
    ideal_data.append(
        create_test_exp(
            "SUCCESS",
            "exp_1",
            1,
            "test_app_test_workload",
            {},
            {},
            "null",
            fom_name,
            fom1,
            "",
            "dummy_app",
            "application",
            FomType.MEASURE,
            BetterDirection.INDETERMINATE,
            nfv1,
            ideal1,
            normalized=normalize,
        )
    )
    ideal_data.append(
        create_test_exp(
            "SUCCESS",
            "exp_2",
            2,
            "test_app_test_workload",
            {},
            {},
            "null",
            fom_name,
            fom2,
            "",
            "dummy_app",
            "application",
            FomType.MEASURE,
            BetterDirection.INDETERMINATE,
            nfv2,
            ideal2,
            normalized=normalize,
        )
    )

    ideal_df = pd.DataFrame(ideal_data, columns=ideal_data[0].keys())

    # Update index to match
    ideal_df = ideal_df.set_index("n_nodes")

    ideal_df[["RAMBLE_VARIABLES", "RAMBLE_RAW_VARIABLES", "fom_units"]] = ideal_df[
        ["RAMBLE_VARIABLES", "RAMBLE_RAW_VARIABLES", "fom_units"]
    ].astype(object)

    # TODO: test things like log
    logx = False
    logy = False
    split_by = "simplified_workload_namespace"

    with PdfPages(pdf_path) as pdf_report:
        where_query = None
        results_df = prepare_data(results, where_query)
        plot = plot_type(
            test_spec, normalize, report_dir_path, pdf_report, results_df, logx, logy, split_by
        )
        plot.generate_plot_data()

        # Sort columns alphabetically, order is not important
        plot.output_df.sort_index(axis=1, inplace=True)
        ideal_df.sort_index(axis=1, inplace=True)

        assert plot.output_df.equals(ideal_df)
        assert os.path.isfile(pdf_path)


repeat_results = {
    "experiments": [
        {
            "RAMBLE_STATUS": "SUCCESS",
            "name": "repeat_exp_1",
            "n_nodes": 1,
            # "application_namespace": "test_app",
            # "workload_name": "test_workload",
            "simplified_workload_namespace": "test_app_test_workload",
            "N_REPEATS": 2,
            "RAMBLE_VARIABLES": {"repeat_index": 0},
            "RAMBLE_RAW_VARIABLES": {},
            "CONTEXTS": [
                {
                    "name": "null",
                    "display_name": "null",
                    "foms": [
                        {
                            "value": 2,
                            "units": "repeats",
                            "origin": "dummy_app",
                            "origin_type": "summary::n_total_repeats",
                            "name": "Experiment Summary",
                            "fom_type": {"name": "MEASURE", "better_direction": "INDETERMINATE"},
                        },
                        {
                            "value": 2,
                            "units": "repeats",
                            "origin": "dummy_app",
                            "origin_type": "summary::n_successful_repeats",
                            "name": "Experiment Summary",
                            "fom_type": {"name": "MEASURE", "better_direction": "INDETERMINATE"},
                        },
                        {
                            "value": 28.0,
                            "units": "s",
                            "origin": "dummy_app",
                            "origin_type": "summary::min",
                            "name": "fom_1",
                            "fom_type": {"name": "TIME", "better_direction": "LOWER"},
                        },
                        {
                            "value": 30.0,
                            "units": "s",
                            "origin": "dummy_app",
                            "origin_type": "summary::max",
                            "name": "fom_1",
                            "fom_type": {"name": "TIME", "better_direction": "LOWER"},
                        },
                        {
                            "value": 29.0,
                            "units": "s",
                            "origin": "dummy_app",
                            "origin_type": "summary::mean",
                            "name": "fom_1",
                            "fom_type": {"name": "TIME", "better_direction": "LOWER"},
                        },
                    ],
                },
            ],
        },
        {
            "RAMBLE_STATUS": "SUCCESS",
            "name": "repeat_exp_1.1",
            "n_nodes": 2,
            # "application_namespace": "test_namespace",
            # "workload_name": "test_workload",
            "simplified_workload_namespace": "test_app_test_workload",
            "N_REPEATS": 0,
            "RAMBLE_VARIABLES": {"repeat_index": 1},
            "RAMBLE_RAW_VARIABLES": {},
            "CONTEXTS": [
                {
                    "name": "null",
                    "display_name": "null",
                    "foms": [
                        {
                            "name": "fom_1",
                            "value": 28.0,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                            "fom_type": {"name": "TIME", "better_direction": "LOWER"},
                        },
                        {
                            "name": "fom_2",
                            "value": 55,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                            "fom_type": {"name": "MEASURE", "better_direction": "INDETERMINATE"},
                        },
                    ],
                },
            ],
        },
        {
            "RAMBLE_STATUS": "SUCCESS",
            "name": "repeat_exp_1.2",
            "n_nodes": 2,
            # "application_namespace": "test_namespace",
            # "workload_name": "test_workload",
            "simplified_workload_namespace": "test_app_test_workload",
            "N_REPEATS": 0,
            "RAMBLE_VARIABLES": {"repeat_index": 2},
            "RAMBLE_RAW_VARIABLES": {},
            "CONTEXTS": [
                {
                    "name": "null",
                    "display_name": "null",
                    "foms": [
                        {
                            "name": "fom_1",
                            "value": 30.0,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                            "fom_type": {"name": "TIME", "better_direction": "LOWER"},
                        },
                        {
                            "name": "fom_2",
                            "value": 55,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                            "fom_type": {"name": "MEASURE", "better_direction": "INDETERMINATE"},
                        },
                    ],
                },
            ],
        },
        {
            "RAMBLE_STATUS": "SUCCESS",
            "name": "single_exp_1",
            "n_nodes": 1,
            # "application_namespace": "test_app",
            # "workload_name": "test_workload",
            "simplified_workload_namespace": "test_app_test_workload",
            "RAMBLE_VARIABLES": {},
            "RAMBLE_RAW_VARIABLES": {},
            "CONTEXTS": [
                {
                    "name": "null",
                    "display_name": "null",
                    "foms": [
                        {
                            "name": "fom_1",
                            "value": 42.0,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                        },
                        {
                            "name": "fom_2",
                            "value": 50,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "application",
                        },
                    ],
                },
            ],
        },
    ]
}


def test_repeat_import(mutable_mock_workspace_path):
    where_query = None
    results_df = prepare_data(repeat_results, where_query)

    print(results_df)
    # DF contains only summary exp and not individual repeats
    assert "repeat_exp_1" in results_df.values
    assert "repeat_exp_1.1" not in results_df.values
    assert "single_exp_1" in results_df.values

    # Summary FOMs are present in DF, types converted to objects
    row_mean = results_df.query("fom_origin_type == 'summary::mean'")
    assert row_mean["fom_value"].values == [29.0]
    assert row_mean["fom_type"].values == [FomType.TIME]
    assert row_mean["better_direction"].values == [BetterDirection.LOWER]

    single_exp_rows = results_df.query("name == 'single_exp_1' and fom_name == 'fom_1'")
    assert single_exp_rows["fom_value"].values == [42.0]


# TODO: test fom plot
# TODO: test compare plot

# TODO: test where query
# TODO: test multiple groupby
# TODO: test multiple splitby

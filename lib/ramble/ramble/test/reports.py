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

# Test conversion from nested dict to dataframe

# Test conversion from dataframe to chart-ready pivot
# - data is not summarized (1 experiment / 1 chart)
# - data is summarized / not repeats (n experiments / 1 chart)
# - data is summarized from repeats (n_repeats / 1 chart)
# - mix of summarized and non-summarized data

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
                        },
                        {
                            "name": "fom_2",
                            "value": 55,
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


def prep_dict(
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
    better_direction,
    fv,
    ifv,
    normalized=False,
):
    return {
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
        "better_direction": better_direction,
        "series": ns,
        "normalized_fom_value" if normalized else "fom_value": fv,
        "ideal_perf_value": ifv,
    }


@pytest.mark.parametrize(
    "values",
    [
        (StrongScalingPlot, "fom_1", 42.0, 42.0, 42.0, 28.0, 28.0, 21.0, False),
        (StrongScalingPlot, "fom_1", 42.0, 1.0, 1.0, 28.0, 1.5, 2.0, True),
        (WeakScalingPlot, "fom_2", 50, 50, 50.0, 55, 55.0, 50.0, False),
        (WeakScalingPlot, "fom_2", 50.0, 1.0, 1.0, 55.0, 1.1, 1.0, True),
    ],
)
def test_scaling_plots(mutable_mock_workspace_path, tmpdir_factory, values):

    report_name = "unit_test"
    report_dir_path = tmpdir_factory.mktemp(report_name)
    pdf_path = os.path.join(report_dir_path, f"{report_name}.pdf")

    plot_type, fom_name, fom1, nfv1, ideal1, fom2, nfv2, ideal2, normalize = values

    test_spec = [[fom_name, "n_nodes"]]

    ideal_data = []
    ideal_data.append(
        prep_dict(
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
            BetterDirection.INDETERMINATE,
            nfv1,
            ideal1,
            normalized=normalize,
        )
    )
    ideal_data.append(
        prep_dict(
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
                        },
                        {
                            "value": 2,
                            "units": "repeats",
                            "origin": "dummy_app",
                            "origin_type": "summary::n_successful_repeats",
                            "name": "Experiment Summary",
                        },
                        {
                            "value": 28.0,
                            "units": "s",
                            "origin": "dummy_app",
                            "origin_type": "summary::min",
                            "name": "fom_1",
                        },
                        {
                            "value": 30.0,
                            "units": "s",
                            "origin": "dummy_app",
                            "origin_type": "summary::max",
                            "name": "fom_1",
                        },
                        {
                            "value": 29.0,
                            "units": "s",
                            "origin": "dummy_app",
                            "origin_type": "summary::mean",
                            "name": "fom_1",
                            "fom_type": {"name": "TIME", "better_direction": "LOWER"},
                        },
                        {
                            "value": 29.0,
                            "units": "s",
                            "origin": "dummy_app",
                            "origin_type": "summary::median",
                            "name": "fom_1",
                        },
                        {
                            "value": 2.0,
                            "units": "s^2",
                            "origin": "dummy_app",
                            "origin_type": "summary::variance",
                            "name": "fom_1",
                        },
                        {
                            "value": 1.4,
                            "units": "s",
                            "origin": "dummy_app",
                            "origin_type": "summary::stdev",
                            "name": "fom_1",
                        },
                        {
                            "value": 0.0,
                            "units": "",
                            "origin": "dummy_app",
                            "origin_type": "summary::cv",
                            "name": "fom_1",
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
    ]
}


def test_repeated_import(mutable_mock_workspace_path):
    where_query = None
    results_df = prepare_data(repeat_results, where_query)
    print(results_df.shape)


# TODO: test fom plot
# TODO: test compare plot

# TODO: test where query
# TODO: test multiple groupby
# TODO: test multiple splitby
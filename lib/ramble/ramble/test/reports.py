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

# Test that PDF is generated and contains data (size > some value?)

# Possible to test that a specific chart was correctly generated? Not sure...
import pytest

#import ramble.reports
from ramble.reports import *

from matplotlib.backends.backend_pdf import PdfPages
import os

results = {
    "experiments": [
        {
            "RAMBLE_STATUS": "SUCCESS",
            "name": "exp_1",
            "n_nodes": 1,
            #"application_namespace": "test_app",
            #"workload_name": "test_workload",
            "simplified_workload_namespace": "test_app_test_workload",
            "RAMBLE_VARIABLES": {},
            "RAMBLE_RAW_VARIABLES": {},
            "CONTEXTS": [
                {
                    "name": "null",
                    "display_name": "null",
                    "foms":
                    [
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
                    ]
                },
            ]
        },
        {
            "RAMBLE_STATUS": "SUCCESS",
            "name": "exp_2",
            "n_nodes": 2,
            #"application_namespace": "test_namespace",
            #"workload_name": "test_workload",
            "simplified_workload_namespace": "test_app_test_workload",
            "RAMBLE_VARIABLES": {},
            "RAMBLE_RAW_VARIABLES": {},
            "CONTEXTS": [
                {
                    "name": "null",
                    "display_name": 'null',
                    "foms":
                    [
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

                    ]
                },
            ]
        },
    ]
}
def prep_dict(success, name, n_nodes, ns, ramble_vars, ramble_raw_vars, context, fom_name, fom_value, units, origin, origin_type, better_direction, fv, ifv, normalized=False):
    return {
        'RAMBLE_STATUS': success,
        'name': name,
        'n_nodes': n_nodes,
        'simplified_workload_namespace': ns,
        'RAMBLE_VARIABLES': ramble_vars,
        'RAMBLE_RAW_VARIABLES': ramble_raw_vars,
        'context': context,
        'fom_name': fom_name,
        'fom_value': fom_value,
        'fom_units': units,
        'fom_origin': origin,
        'fom_origin_type': origin_type,
        'better_direction': better_direction,
        'series': ns,
        'normalized_fom_value' if normalized else 'fom_value': fv,
        'ideal_perf_value': ifv
    }


@pytest.mark.parametrize(
    "values", [
        (StrongScalingPlot, 'fom_1', 42.0, 42.0, 42.0, 28.0, 28.0, 21.0, False),
        (StrongScalingPlot, 'fom_1', 42.0, 1.0, 1.0, 28.0, 1.5, 2.0, True),
        (WeakScalingPlot, 'fom_2', 50, 50, 50.0, 55, 55.0, 50.0, False),
        (WeakScalingPlot, 'fom_2', 50.0, 1.0, 1.0, 55.0, 1.1, 1.0, True),
    ]
)
def test_scaling_plots(mutable_mock_workspace_path, tmpdir_factory, values):

    report_name = 'unit_test'
    report_dir_path = tmpdir_factory.mktemp(report_name)
    pdf_path = os.path.join(report_dir_path, f'{report_name}.pdf')

    plot_type, fom_name, fom1, nfv1, ideal1, fom2, nfv2, ideal2, normalize = values

    test_spec = [[fom_name, 'n_nodes']]

    ideal_data = []
    ideal_data.append(prep_dict('SUCCESS', 'exp_1', 1, 'test_app_test_workload', {}, {}, 'null', fom_name, fom1, '', 'dummy_app', 'application', 'INDETERMINATE', nfv1, ideal1, normalized=normalize))
    ideal_data.append(prep_dict('SUCCESS', 'exp_2', 2, 'test_app_test_workload', {}, {}, 'null', fom_name, fom2, '', 'dummy_app', 'application', 'INDETERMINATE', nfv2, ideal2, normalized=normalize))

    ideal_df = pd.DataFrame(ideal_data, columns=ideal_data[0].keys())

    # Update index to match
    ideal_df = ideal_df.set_index('n_nodes')

    # Update data types to match
    #for col in ideal_df:
         #ideal_df[col] = ramble.reports.to_numeric_if_possible(ideal_df[col])

    ideal_df[['RAMBLE_VARIABLES', 'RAMBLE_RAW_VARIABLES', 'fom_units']] = ideal_df[['RAMBLE_VARIABLES', 'RAMBLE_RAW_VARIABLES', 'fom_units']].astype(object)

    with PdfPages(pdf_path) as pdf_report:
        results_df = prepare_data(results)
        plot = plot_type(test_spec, normalize, report_dir_path, pdf_report, results_df)
        plot.generate_plot_data()

        assert(plot.output_df.equals(ideal_df))
        print(pdf_path)
        assert(os.path.isfile(pdf_path))

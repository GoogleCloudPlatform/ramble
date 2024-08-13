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

def test_strong_scaling(mutable_mock_workspace_path, tmpdir_factory):

    report_name = 'unit_test'
    report_dir_path = tmpdir_factory.mktemp(report_name)
    pdf_path = os.path.join(report_dir_path, f'{report_name}.pdf')

    test_spec = [['fom_1', 'n_nodes']]
    normalize = True

    with PdfPages(pdf_path) as pdf_report:
        plot = StrongScalingPlot(test_spec, normalize, report_dir_path, pdf_report)
        results_df = prepare_data(results)
        plot.generate_plot(results_df)

def test_weak_scaling(mutable_mock_workspace_path, tmpdir_factory):

    report_name = 'unit_test'
    report_dir_path = tmpdir_factory.mktemp(report_name)
    pdf_path = os.path.join(report_dir_path, f'{report_name}.pdf')

    test_spec = [['fom_2', 'n_nodes']]
    normalize = True

    with PdfPages(pdf_path) as pdf_report:
        plot = WeakScalingPlot(test_spec, normalize, report_dir_path, pdf_report)
        results_df = prepare_data(results)
        plot.generate_plot(results_df)

# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
import datetime
import itertools
import os
import re

import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

import llnl.util.filesystem as fs

import ramble.cmd.results
import ramble.cmd.workspace
import ramble.config
import ramble.filters
from ramble.language.shared_language import BetterDirection
import ramble.pipeline
import ramble.util.path
from ramble.util.logger import logger


def get_reports_path():
    """Returns current directory of ramble-created reports"""
    path_in_config = ramble.config.get("config:report_dirs")
    if not path_in_config:
        # command above should have worked, so if it doesn't, error out:
        logger.die("No config:report_dirs setting found in configuration. To add one,  "
                   "use command: ramble config add \"config:report_dirs:~/.ramble/reports\"")

    report_path = ramble.util.path.canonicalize_path(str(path_in_config))
    return report_path


def is_numeric(series):
    """Check if a pandas series contains only numeric values.
    """
    try:
        pd.to_numeric(series)
        return True
    except (ValueError, TypeError):
        return False


def validate_spec(results_df, chart_spec):
    """Validates that the FOMs and variables in the chart spec are in the results data."""
    for var in chart_spec:
        if var not in results_df.columns and var not in results_df.loc[:, 'fom_name'].values:
            logger.die(f'{var} was not found in the results data.')


def load_results(args):
    """Loads results from a file or workspace to use for reports.

    Check for results in this order:
        1. via ``ramble results report -f FILENAME``
        2. via ``ramble -w WRKSPC`` or ``ramble -D DIR`` or 
        ``ramble results report --workspace WRKSPC``(arguments)
        3. via a path in the ramble.workspace.ramble_workspace_var environment variable.
    """
    results_dict = {}

    if args.file:
        results_dict = ramble.cmd.results.import_results_file(args.file)
    else:
        ramble_ws = ramble.cmd.find_workspace_path(args)

        if not ramble_ws:
            logger.die("ramble results report requires either a results filename, "
                       "a command line workspace, or an active workspace")

        logger.debug("Looking for workspace results file...")
        json_results_path = os.path.join(ramble_ws, "results.latest.json")
        yaml_results_path = os.path.join(ramble_ws, "results.latest.yaml")
        if os.path.exists(json_results_path):
            logger.debug(f"Importing {json_results_path}")
            results_dict = ramble.cmd.results.import_results_file(json_results_path)
        elif os.path.exists(yaml_results_path):
            logger.debug(f"Importing {yaml_results_path}")
            results_dict = ramble.cmd.results.import_results_file(yaml_results_path)
        else:
            logger.die("No JSON or YAML results file was found. Please run "
                       "'ramble workspace analyze -f json'.")
    return results_dict


def prepare_data(results: dict) -> pd.DataFrame:
    """Creates a Pandas DataFrame from the results dictionary to use for reports.
    """

    unnest_context = []
    # first unnest dictionaries
    for exp in results['experiments']:
        if exp['RAMBLE_STATUS'] == 'SUCCESS':
            for context in exp['CONTEXTS']:
                for fom in context['foms']:
                    # Expand to one row per FOM per context w/ a copy of the experiment vars and metadata
                    exp_copy = copy.deepcopy(exp)

                    # Remove context dict and add the current FOM values
                    exp_copy.pop('CONTEXTS')
                    exp_copy['context'] = context['display_name']
                    exp_copy['fom_name'] = fom['name']
                    exp_copy['fom_value'] = fom['value']
                    exp_copy['fom_units'] = fom['units']
                    exp_copy['fom_origin'] = fom['origin']
                    exp_copy['fom_origin_type'] = fom['origin_type']
                    if 'fom_type' in fom.keys():
                        exp_copy['better_direction'] = fom['fom_type']['better_direction']
                    else:  # if using older data file without fom_type
                        exp_copy['better_direction'] = 'INDETERMINATE'

                    # Flatten final vars dict and drop raw vars dict
                    exp_copy.pop('RAMBLE_VARIABLES')
                    exp_copy.pop('RAMBLE_RAW_VARIABLES')

                    # Exclude vars that aren't needed for analysis, mainly paths and commands
                    dir_regex = r"_dir$"
                    path_regex = r"_path$"
                    vars_to_ignore = [
                        'batch_submit',
                        'log_file',
                        'command',
                        'execute_experiment',
                    ]
                    for key, value in exp['RAMBLE_VARIABLES'].items():
                        if key in vars_to_ignore:
                            continue
                        if re.search(dir_regex, key):
                            continue
                        if re.search(path_regex, key):
                            continue
                        exp_copy[key] = value

                    unnest_context.append(exp_copy)
        else:  # exclude failed experiments from dataset
            continue

    results_df = pd.DataFrame.from_dict(unnest_context)

    # Convert numeric columns to numeric
    # TODO(dpomeroy): need to fix this for fom_values column
    # to handle case when there are both numeric and non-numeric FOMs
    for col in results_df.columns:
        if is_numeric(results_df[col]):
            results_df.loc[:, col] = pd.to_numeric(results_df[col])

    pd.DataFrame.to_json(results_df, 'prepare_data_results.json')

    return results_df


def make_report(results_df, args):    
    dt = datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    report_dir_root = get_reports_path()
    # TODO(dpomeroy): update file import to extract workspace name and pass it through here
    ws_name = 'unknown_workspace'
    if args.workspace:
        ws_name = str(args.workspace)
    report_name = f"{ws_name}.{dt}"
    report_dir_path = os.path.join(report_dir_root, report_name)
    fs.mkdirp(report_dir_path)
    pdf_path = os.path.join(report_dir_path, f'{report_name}.pdf')

    with PdfPages(pdf_path) as pdf_report:

        if args.strong_scaling:
            print("strong_scaling")
            generate_strong_scaling_chart(results_df, pdf_report, report_dir_path, args)

        if args.weak_scaling:
            print("weak_scaling")
            generate_weak_scaling_chart(results_df, pdf_report, report_dir_path, args)

        if args.compare:
            print("compare")
            generate_compare_chart(results_df, pdf_report, report_dir_path, args)

        if args.foms:
            print("foms")
            generate_foms_chart(results_df, pdf_report, report_dir_path, args)

    # TODO(dpomeroy): this needs to error out if the PDF is empty, currently it succeeds
    # print(f'pdf size is {os.path.getsize(pdf_path)}')
    if os.path.isfile(pdf_path):
        logger.msg("Report generated successfully. A PDF summary is available at:\n"
                   f"    {pdf_path}")
        logger.msg("Individual chart images are available at:\n"
                   f"    {report_dir_path}")


def generate_strong_scaling_chart(results_df, pdf_report, report_dir_path, args):
    for chart_spec in args.strong_scaling:

        if len(chart_spec) < 2:
            logger.die('Scaling plot requires two arguments: '
                       'performance metric and scaling metric')

        validate_spec(results_df, chart_spec)

        perf_measure, scale_var, *additional_vars = chart_spec

        # FOMs are by row, so select only rows with the perf_measure FOM
        perf_results = results_df.query(f'fom_name == "{perf_measure}"').copy()

        # Determine which direction is 'better', or 'INDETERMINATE' if missing or ambiguous data
        better_direction = 'INDETERMINATE'
        if len(perf_results.loc[:, 'better_direction'].unique()) == 1:
            better_direction = perf_results.loc[:, 'better_direction'].unique()[0]

        perf_results.loc[:, 'series'] = perf_results.loc[:, 'workload_namespace']
        if additional_vars:
            for var in additional_vars:
                perf_results.loc[:, 'series'] = perf_results.loc[:, 'series'] + '_x_' + var

        for series in perf_results.loc[:, 'series'].unique():

            print(f'series = {series}')

            series_results = perf_results.query(f'series == "{series}"')
            selected = series_results.loc[:, [f'{scale_var}', 'fom_value']]

            fig, ax = plt.subplots()

            if args.normalize:
                first_perf_value = selected['fom_value'].iloc[0]
                selected.loc[:, 'normalized_fom_value'] = first_perf_value / selected.loc[:, 'fom_value']

                first_scale_value = selected[f'{scale_var}'].iloc[0]
                selected.loc[:, 'ideal_perf_value'] = selected.loc[:, f'{scale_var}'] / first_scale_value

                ax.plot(f'{scale_var}', 'normalized_fom_value', data=selected, marker='o')
                ax.plot(f'{scale_var}', 'ideal_perf_value', data=selected)

                ax.set_xlabel(f'{scale_var}')
                ax.set_ylabel('Speedup')
            else:
                first_perf_value = selected['fom_value'].iloc[0]

                if better_direction == 'LOWER' or better_direction == BetterDirection.LOWER:
                    first_perf_value = selected['fom_value'].iloc[0]
                    selected.loc[:, 'ideal_perf_value'] = first_perf_value / selected.loc[:, f'{scale_var}']
                if better_direction == 'HIGHER' or better_direction == BetterDirection.HIGHER:
                    first_perf_value = selected['fom_value'].iloc[0]
                    selected.loc[:, 'ideal_perf_value'] = first_perf_value * selected.loc[:, f'{scale_var}']                

                ax.plot(f'{scale_var}', 'fom_value', data=selected, marker='o')
                ax.plot(f'{scale_var}', 'ideal_perf_value', data=selected)

                ax.set_xlabel(f'{scale_var}')
                ax.set_ylabel(f'{perf_measure}')

            # ax.set_xscale('log')
            ax.set_xticks(perf_results.query(f'series == "{series}"')[f'{scale_var}'].unique().tolist())
            ax.set_title(f'Strong Scaling: {perf_measure} vs {scale_var} for {series}')

            # TODO(dpomeroy): add data table below chart
            # cols = (f'{scale_var}', f'{perf_measure}')
            # n_rows = len(selected)

            chart_filename = f'strong-scaling_{perf_measure}_vs_{scale_var}_{series}.png'
            chart_filename = chart_filename.replace(" ", "-")

            plt.savefig(os.path.join(report_dir_path, chart_filename))
            pdf_report.savefig(fig)
            plt.close(fig)


def generate_weak_scaling_chart(results_df, pdf_report, report_dir_path, args):
    for chart_spec in args.weak_scaling:

        if len(chart_spec) < 2:
            logger.die('Scaling plot requires two arguments: '
                       'performance metric and scaling metric')

        validate_spec(results_df, chart_spec)

        perf_measure, scale_var, *additional_vars = chart_spec

        # FOMs are by row, so select only rows with the perf_measure FOM
        perf_results = results_df.query(f'fom_name == "{perf_measure}"').copy()

        # Determine which direction is 'better', or 'INDETERMINATE' if missing or ambiguous data
        better_direction = 'INDETERMINATE'
        if len(perf_results.loc[:, 'better_direction'].unique()) == 1:
            better_direction = perf_results.loc[:, 'better_direction'].unique()[0]

        perf_results.loc[:, 'series'] = perf_results.loc[:, 'workload_namespace']
        if additional_vars:
            for var in additional_vars:
                perf_results.loc[:, 'series'] = perf_results.loc[:, 'series'] + '_x_' + var

        for series in perf_results.loc[:, 'series'].unique():

            print(f'series = {series}')

            series_results = perf_results.query(f'series == "{series}"')
            selected = series_results.loc[:, [f'{scale_var}', 'fom_value']]

            fig, ax = plt.subplots()

            if args.normalize:
                first_perf_value = selected['fom_value'].iloc[0]
                selected.loc[:, 'normalized_fom_value'] = first_perf_value / selected.loc[:, 'fom_value']

                selected.loc[:, 'ideal_perf_value'] = 1

                ax.plot(f'{scale_var}', 'normalized_fom_value', data=selected, marker='o')
                ax.plot(f'{scale_var}', 'ideal_perf_value', data=selected)

                ax.set_xlabel(f'{scale_var}')
                ax.set_ylabel('Efficiency')
            else:
                first_perf_value = selected['fom_value'].iloc[0]

                # TODO(dpomeroy): figure out if there's supposed to be a difference between non-normalized
                # weak scaling charts
                if better_direction == 'LOWER' or better_direction == BetterDirection.LOWER:
                    first_perf_value = selected['fom_value'].iloc[0]
                    selected.loc[:, 'ideal_perf_value'] = first_perf_value
                if better_direction == 'HIGHER' or better_direction == BetterDirection.HIGHER:
                    first_perf_value = selected['fom_value'].iloc[0]
                    selected.loc[:, 'ideal_perf_value'] = first_perf_value

                ax.plot(f'{scale_var}', 'fom_value', data=selected, marker='o')
                ax.plot(f'{scale_var}', 'ideal_perf_value', data=selected)

                ax.set_xlabel(f'{scale_var}')
                ax.set_ylabel(f'{perf_measure}')

            # ax.set_xscale('log')
            ax.set_xticks(perf_results.query(f'series == "{series}"')[f'{scale_var}'].unique().tolist())
            ax.set_title(f'Weak Scaling: {perf_measure} vs {scale_var} for {series}')

            # TODO(dpomeroy): add data table below chart
            # cols = (f'{scale_var}', f'{perf_measure}')
            # n_rows = len(selected)

            chart_filename = f'weak-scaling_{perf_measure}_vs_{scale_var}_{series}.png'
            chart_filename = chart_filename.replace(" ", "-")

            plt.savefig(os.path.join(report_dir_path, chart_filename))
            pdf_report.savefig(fig)
            plt.close(fig)

# --compare -n [FOM_1] [FOM_2] [optional: add'l FOMs] [optional: group by]
def generate_compare_chart(results_df, pdf_report, report_dir_path, args):
    for chart_spec in args.compare:
        validate_spec(results_df, chart_spec)

        # Organize input args into FOMs and groups
        foms = []
        groups = []

        for input in chart_spec:
            if input in results_df.loc[:, 'fom_name'].values:
                foms.append(input)
            else:
                groups.append(input)

        compare_results = results_df.pivot_table('fom_value', index=groups, columns='fom_name').copy()
        compare_results = compare_results[foms]
        # print(f'compare_results:\n{compare_results}')


def generate_foms_chart(results_df, pdf_report, report_dir_path, args):
    # this one doesn't have a chart spec, it's just a flag
    # first divide results into series based on workload namespace
    # then iterate through foms and create 1 chart per fom comparing fom_value (y) by experiment (x)

    pass

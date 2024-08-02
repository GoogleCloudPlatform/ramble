# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import copy
import datetime
import os
import re

import pandas as pd
# import numpy as np
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


def to_numeric_if_possible(series):
    """Try to convert a Pandas series to numeric, or return the series unchanged.
    """
    try:
        return pd.to_numeric(series)
    except (ValueError, TypeError):
        return series


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

    Transforms nested results dictionary into a flat dataframe. Each row equals
    one FOM from one context of one experiment, with columns including
    associated experiment variables (except paths and commands).

    Input (dict):
        {
            "experiments": [
                {"name": "exp_1",
                 "n_nodes": 1,
                 "CONTEXTS": [
                    {"name": "null",
                     "foms": [
                        {"name": "fom_1", "value": 42.0},
                        {"name": "fom_2", "value": 35},
                     ]
                    },
                 ]
                },
                {"name": "exp_2",
                 "n_nodes": 2,
                 "CONTEXTS": [
                    {"name": "null",
                     "foms": [
                        {"name": "fom_1", "value": 56.5},
                        {"name": "fom_2", "value": 73},
                     ]
                    },
                 ]
                },
            ]
        }

    Output (pd.DataFrame):
             name   fom_name    fom_value  n_nodes
        0   exp_1      fom_1         42.0        1
        1   exp_1      fom_2           35        1
        2   exp_2      fom_1         56.5        2
        3   exp_2      fom_2           73        2
    """

    unnest_context = []
    skip_exps = []
    # first unnest dictionaries
    for exp in results['experiments']:
        # TODO(dpomeroy): in charts, annotate chart if using aggregated/statistical data (e.g., 'avg' or 'mean')

        if exp['RAMBLE_STATUS'] == 'SUCCESS' and exp['name'] not in skip_exps:
            # For repeat experiments, use summary stats from base exp and skip repeats
            # Repeats are sequenced after base exp
            if exp['N_REPEATS'] > 0:
                # Generate repeat experiment names in order to skip them explicitly
                exp_name = exp['name']
                for n in range(1, exp['N_REPEATS'] + 1):
                    if ".chain" in exp_name:
                        insert_idx = exp_name.index(".chain")
                        repeat_exp_name = exp_name[:insert_idx] + f".{n}" + exp_name[insert_idx:]
                        skip_exps.append(repeat_exp_name)
                    else:
                        skip_exps.append(exp_name + f".{n}")

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
        else:  # exclude failed experiments from dataframe
            continue

    results_df = pd.DataFrame.from_dict(unnest_context)

    # TODO(dpomeroy): cleanup - delete exports
    pd.DataFrame.to_json(results_df, 'prepare_data_results.json')
    pd.DataFrame.to_csv(results_df, 'prepare_data_results.csv')

    return results_df


def make_report(results_df, ws_name, args):
    dt = datetime.datetime.now().strftime("%Y-%m-%d_%H.%M.%S")
    report_dir_root = get_reports_path()

    # TODO(dpomeroy): update file import to extract workspace name and pass it through here

    print(results_df)
    if args.workspace:
        ws_name = str(args.workspace)

    if not ws_name:
        ws_name = 'unknown_workspace'

    report_name = f"{ws_name}.{dt}"
    report_dir_path = os.path.join(report_dir_root, report_name)
    fs.mkdirp(report_dir_path)
    pdf_path = os.path.join(report_dir_path, f'{report_name}.pdf')

    with PdfPages(pdf_path) as pdf_report:

        if args.strong_scaling:
            generate_strong_scaling_chart(results_df, pdf_report, report_dir_path, args)

        if args.weak_scaling:
            generate_weak_scaling_chart(results_df, pdf_report, report_dir_path, args)

        if args.compare:
            generate_compare_chart(results_df, pdf_report, report_dir_path, args)

        if args.foms:
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
        perf_measure_results = results_df.query(f'fom_name == "{perf_measure}"').copy()

        # Determine which direction is 'better', or 'INDETERMINATE' if missing or ambiguous data
        better_direction = 'INDETERMINATE'
        if len(perf_measure_results.loc[:, 'better_direction'].unique()) == 1:
            better_direction = perf_measure_results.loc[:, 'better_direction'].unique()[0]

        perf_measure_results.loc[:, 'series'] = perf_measure_results.loc[:, 'application_namespace'] + '_' + perf_measure_results.loc[:, 'workload_name']

        # Break data down into series using app, workload, and vars input by user
        if additional_vars:
            perf_measure_results.loc[:, 'series'] = perf_measure_results.loc[:, 'series'] + '_x_' + perf_measure_results[additional_vars].agg('_x_'.join, axis=1)

        for col in perf_measure_results.columns:
            perf_measure_results.loc[:, col] = to_numeric_if_possible(perf_measure_results[col])

            # for var in additional_vars:
            #     vals = raw_results.loc[:, var].unique()
            #     for val in vals:

            #     raw_results.loc[:, 'series'] = raw_results.loc[:, 'series'] + '_x_' + var

        # for col in perf_measure_results.columns:
        #     print(col)
        #     try:
        #         print(str(results_df[col].unique()))
        #     except:
        #         pass


        for series in perf_measure_results.loc[:, 'series'].unique():

            #print(f'series = {series}')

            series_results = perf_measure_results.query(f'series == "{series}"')
            selected = series_results.loc[:, [f'{scale_var}', 'fom_value']]

            #print(series_results)

            #print(f"selected = {selected}")

            scale_pivot = series_results.pivot_table('fom_value', index=scale_var)

            #print(scale_pivot)

            fig, ax = plt.subplots()

            if args.normalize:
                first_perf_value = scale_pivot['fom_value'].iloc[0]
                scale_pivot.loc[:, 'normalized_fom_value'] = first_perf_value / scale_pivot.loc[:, 'fom_value']
                scale_pivot.loc[:, 'ideal_perf_value'] = scale_pivot.index / scale_pivot.index[0]

                ax.plot(scale_pivot.index, 'normalized_fom_value', data=scale_pivot, marker='o')
                ax.plot(scale_pivot.index, 'ideal_perf_value', data=scale_pivot)

                ax.set_xlabel(f'{scale_var}')
                ax.set_ylabel('Speedup')
            else:
                first_perf_value = scale_pivot['fom_value'].iloc[0]

                if better_direction == 'LOWER' or better_direction == BetterDirection.LOWER:
                    scale_pivot.loc[:, 'ideal_perf_value'] = first_perf_value / scale_pivot.index
                    ax.plot(scale_pivot.index, 'ideal_perf_value', data=scale_pivot)
                if better_direction == 'HIGHER' or better_direction == BetterDirection.HIGHER:
                    scale_pivot.loc[:, 'ideal_perf_value'] = first_perf_value * scale_pivot.index
                    ax.plot(scale_pivot.index, 'ideal_perf_value', data=scale_pivot)

                ax.plot(scale_pivot.index, 'fom_value', data=scale_pivot, marker='o')

                ax.set_xlabel(f'{scale_var}')
                ax.set_ylabel(f'{perf_measure}')

            # ax.set_xscale('log')
            ax.set_xticks(scale_pivot.index.unique().tolist())
            ax.set_title(f'Strong Scaling: {perf_measure} vs {scale_var} for {series}')
            plt.tight_layout()

            # TODO(dpomeroy): add data table below chart to show what's in the pivot table
            # cols = (f'{scale_var}', f'{perf_measure}')
            # n_rows = len(selected)

            chart_filename = f'strong-scaling_{perf_measure}_vs_{scale_var}_{series}.png'
            chart_filename = chart_filename.replace(" ", "-")

            plt.savefig(os.path.join(report_dir_path, chart_filename))
            pdf_report.savefig(fig)
            plt.close(fig)


# TODO(dpomeroy): once strong scaling chart is fixed up for repeats / summary,
# copy those changes here
def generate_weak_scaling_chart(results_df, pdf_report, report_dir_path, args):
    for chart_spec in args.weak_scaling:

        if len(chart_spec) < 2:
            logger.die('Scaling plot requires two arguments: '
                       'performance metric and scaling metric')

        validate_spec(results_df, chart_spec)

        perf_measure, scale_var, *additional_vars = chart_spec

        # FOMs are by row, so select only rows with the perf_measure FOM
        raw_results = results_df.query(f'fom_name == "{perf_measure}"').copy()

        # Determine which direction is 'better', or 'INDETERMINATE' if missing or ambiguous data
        better_direction = 'INDETERMINATE'
        if len(raw_results.loc[:, 'better_direction'].unique()) == 1:
            better_direction = raw_results.loc[:, 'better_direction'].unique()[0]

        raw_results.loc[:, 'series'] = raw_results.loc[:, 'simplified_workload_namespace']
        if additional_vars:
            for var in additional_vars:
                raw_results.loc[:, 'series'] = raw_results.loc[:, 'series'] + '_x_' + var

        for series in raw_results.loc[:, 'series'].unique():

            #print(f'series = {series}')

            series_results = raw_results.query(f'series == "{series}"')
            selected = series_results.loc[:, [f'{scale_var}', 'fom_value']]

            fig, ax = plt.subplots()

            if args.normalize:
                first_perf_value = selected['fom_value'].iloc[0]
                selected.loc[:, 'normalized_fom_value'] = first_perf_value / selected.loc[:, 'fom_value']

                selected.loc[:, 'ideal_perf_value'] = 1

                #print(selected)


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

                #print(selected)

                ax.plot(f'{scale_var}', 'fom_value', data=selected, marker='o')
                ax.plot(f'{scale_var}', 'ideal_perf_value', data=selected)

                ax.set_xlabel(f'{scale_var}')
                ax.set_ylabel(f'{perf_measure}')

            # ax.set_xscale('log')
            ax.set_xticks(raw_results.query(f'series == "{series}"')[f'{scale_var}'].unique().tolist())
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

        # Break out input args into FOMs and dimensions
        foms = []
        dimensions = []

        for input in chart_spec:
            if input in results_df.loc[:, 'fom_name'].values:
                foms.append(input)
            else:
                dimensions.append(input)

        # TODO(dpomeroy): pull in better_direction for the foms. If it's the same for all foms
        # (e.g., all are 'time' foms) then append (lower/higher is better) to chart title
        # else if there's a mix of foms or foms are not higher/lower, append nothing (indeterminate)

        # TODO(dpomeroy): convert to numeric (moved here from prepare_data function)

        raw_results = results_df[results_df.loc[:, 'fom_name'].isin(foms)].copy()

        raw_results.loc[:, 'Figure of Merit'] = (raw_results.loc[:, 'fom_name'] +
                                          ' (' + raw_results.loc[:, 'fom_units'] + ')')

        #print(raw_results.dtypes)
        #print(raw_results['fom_value'])

        raw_results['fom_value'] = pd.to_numeric(raw_results['fom_value'])
        raw_results.to_csv('raw_results.csv')

        #print(raw_results.loc[:, 'fom_value'])

        compare_pivot = raw_results.pivot_table('fom_value', index=dimensions, columns='Figure of Merit')

        # Pivot table aggregates values by mean. Check if results were aggregated and label them
        # Raw results have FOMs by row, pivot by columns, so multiply the pivot rows x cols
        print(f'raw values = {len(raw_results)}  vs pivot values = {len(compare_pivot)} x {len(compare_pivot.columns)} ={len(compare_pivot) * len(compare_pivot.columns)}')

        # If all FOMs are either higher or lower is better, add it to chart title
        title_suffix = ''
        if len(raw_results.loc[:, 'better_direction'].unique()) == 1:
            if raw_results.loc[:, 'better_direction'].unique()[0] == 'HIGHER':
                title_suffix = '(higher is better)'
            elif raw_results.loc[:, 'better_direction'].unique()[0] == 'LOWER':
                title_suffix = '(lower is better)'


        ax = compare_pivot.plot(kind="bar")
        fig = ax.get_figure()

        ax.set_title(f'{" vs ".join(foms)} by {" and ".join(dimensions)} {title_suffix}')

        plt.tight_layout()

        # Create filenames
        chart_filename = f'{"_vs_".join(foms)}_by_{"_and_".join(dimensions)}.png'
        chart_filename = chart_filename.replace(" ", "-")

        plt.savefig(os.path.join(report_dir_path, chart_filename))
        pdf_report.savefig(fig)
        plt.close(fig)

        # print(f'compare_results:\n{compare_results}')


def generate_foms_chart(results_df, pdf_report, report_dir_path, args):
    # this one doesn't have a chart spec, it's just a flag
    # first divide results into series based on workload namespace
    # then iterate over each fom in each series and create 1 bar chart per fom
    # comparing fom_value (y) by experiment (x)

    pass
